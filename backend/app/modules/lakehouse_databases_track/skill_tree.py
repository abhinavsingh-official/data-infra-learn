"""The "Lakehouse Databases" track - table-format fundamentals (atomic
commits, schema enforcement/evolution, MERGE/upsert, time travel, the
transaction log, optimistic concurrency, compaction, data skipping,
retention/VACUUM) taught via small Postgres tables, paired with the
real lakehouse_phase capstone (Delta/Iceberg at scale) the same way
sql_databases_track pairs with postgres_phase. Every example row/
expected output was captured by actually running these queries against
Postgres."""

LAKEHOUSE_DATABASES_SKILL_TREE = {
    "paradigm": "lakehouse-databases",
    "nodes": [
        {
            "id": "intro",
            "type": "intro",
            "title": "A lakehouse: ACID transactions on top of lake storage",
            "body": (
                "A lakehouse keeps a lake's cheap, schema-on-read object storage but adds a table "
                "format (Delta Lake, Apache Iceberg) on top - a transaction log that turns a folder "
                "of files into something with real database guarantees: atomic commits, enforced "
                "schema, MERGE/upsert, time travel, and safe concurrent writers. Every one of those "
                "guarantees is really just a consequence of one idea: a table's true state isn't "
                "'whatever files happen to be in this folder right now', it's 'whatever the "
                "transaction log says the current version is'. This track walks through the SQL "
                "consequence of that idea on small, hand-sized data - the Lakehouse capstone right "
                "after does the same thing for real, against a real table format at full scale."
            ),
        },
        {
            "id": "node_1_atomic_commits",
            "type": "skill",
            "title": "Atomic commits: a batch is visible all at once, or not at all",
            "teach": {
                "sql": "SELECT order_id, amount\nFROM commit_batches\nWHERE status = 'committed';",
                "note": (
                    "A plain lake has no concept of a 'commit' - a writer crashing halfway through "
                    "writing a batch of files leaves whatever partial files it managed to write "
                    "sitting there, readable, half-done. A table format's transaction log fixes "
                    "this: a batch of writes only becomes visible to readers once a single atomic "
                    "commit record says so, so a reader only ever sees a fully-committed batch, "
                    "never a half-written one. Filtering to status = 'committed' here is the "
                    "Postgres stand-in for that guarantee - an aborted batch's rows exist in the "
                    "underlying storage, but no correct reader ever sees them."
                ),
                "steps": [
                    {
                        "body": "A plain lake has no concept of a 'commit' at all - a writer that "
                        "crashes halfway through writing a batch of files leaves whatever partial "
                        "files it managed to finish sitting there, readable, half-done."
                    },
                    {
                        "body": "Only ever read rows from a batch whose commit actually succeeded:",
                        "sql": "SELECT id FROM batches\nWHERE status = 'committed';",
                    },
                    {
                        "body": "Return every order from a successfully committed batch only:",
                        "sql": "SELECT order_id, amount\nFROM commit_batches\nWHERE status = 'committed';",
                    },
                    {
                        "body": "status = 'aborted' rows exist in the underlying storage here - "
                        "they were actually written - but no correct reader should ever see them, "
                        "exactly the way a table format's transaction log never advances the "
                        "table's current version to include a batch that didn't fully commit."
                    },
                    {
                        "body": "This is the real meaning of 'atomic' here: all-or-nothing, not "
                        "'fast' or 'safe' in some vaguer sense. A batch of 10,000 rows either "
                        "becomes entirely visible in one commit, or none of it does - there's no "
                        "state where a reader sees 6,000 of the 10,000 rows because the writer got "
                        "partway through before failing."
                    },
                    {
                        "body": "A plain lake can approximate atomicity with conventions (write to "
                        "a staging path, then rename the whole directory only once everything "
                        "finished) but it's a convention, not a guarantee the storage layer "
                        "enforces - a table format makes it a property of the format itself, "
                        "enforced by every reader and writer that respects the transaction log."
                    },
                    {
                        "body": "A commit makes an entire batch of writes visible at once, or none "
                        "of it, never a partial batch. Try it yourself in the Practice tab."
                    },
                ],
            },
            "practice": {
                "prompt": "Return every order from a successfully committed batch only.",
                "table_name": "commit_batches",
                "schema": [
                    {"column": "commit_id", "type": "bigint"},
                    {"column": "status", "type": "text"},
                    {"column": "order_id", "type": "bigint"},
                    {"column": "amount", "type": "numeric"},
                ],
                "example_rows": [
                    {"commit_id": 1, "status": "committed", "order_id": 1, "amount": 100.00},
                    {"commit_id": 1, "status": "committed", "order_id": 2, "amount": 200.00},
                    {"commit_id": 2, "status": "aborted", "order_id": 3, "amount": 300.00},
                ],
                "expected_output_rows": [
                    {"order_id": 1, "amount": 100.00},
                    {"order_id": 2, "amount": 200.00},
                ],
            },
        },
        {
            "id": "node_2_schema_enforcement",
            "type": "skill",
            "title": "Schema enforcement at write time: rejecting rows that violate it",
            "teach": {
                "sql": (
                    "SELECT id, account_id, amount\n"
                    "FROM incoming_writes\n"
                    "WHERE account_id IS NOT NULL AND amount > 0;"
                ),
                "note": (
                    "A plain lake's schema-on-read (node 1 of the Lake track) accepts anything a "
                    "producer sends and defers interpretation to query time. A lakehouse table "
                    "format inverts that back toward a warehouse's behavior at the table level: it "
                    "declares a schema and REJECTS a write that violates it - a NULL in a "
                    "declared-NOT-NULL column, or a value that fails a declared CHECK constraint, "
                    "never gets committed in the first place. This query models what enforcement "
                    "would have already filtered out: rows with a NULL account_id or a non-positive "
                    "amount are exactly what a real schema-enforced write would have refused to "
                    "accept."
                ),
                "steps": [
                    {
                        "body": "A plain lake accepts any row a producer sends, however malformed, "
                        "and defers the problem to query time. A lakehouse table format can refuse "
                        "a bad row before it's ever committed - schema enforcement AT write time."
                    },
                    {
                        "body": "Model what a schema-enforced write would have already refused:",
                        "sql": "SELECT id FROM incoming\nWHERE required_col IS NOT NULL AND value > 0;",
                    },
                    {
                        "body": "Return only rows that would have passed a NOT NULL + positive-amount constraint:",
                        "sql": (
                            "SELECT id, account_id, amount\n"
                            "FROM incoming_writes\n"
                            "WHERE account_id IS NOT NULL AND amount > 0;"
                        ),
                    },
                    {
                        "body": "A real lakehouse table format would never have let the NULL-"
                        "account_id row or the negative-amount row land in the table at all - the "
                        "write itself fails, loudly, at commit time, instead of silently succeeding "
                        "and leaving a bad row for every future reader to stumble over."
                    },
                    {
                        "body": "This is a genuinely different failure mode from node 7 of the "
                        "Warehouse Databases track (the Unknown Member pattern) - there, a bad "
                        "foreign key is allowed to land and gets handled gracefully at READ time "
                        "(COALESCE to 'Unknown'). Here, a schema violation is refused at WRITE time "
                        "and never lands at all. Both are legitimate strategies; they just push the "
                        "problem to different points in the pipeline."
                    },
                    {
                        "body": "Schema enforcement is also why adding a column safely (node 3, "
                        "schema evolution) has to be an explicit, deliberate operation on a "
                        "lakehouse table - the same enforcement that rejects a NULL in a required "
                        "column would reject every OLD row the instant a new required column is "
                        "added, unless the table format handles that transition specially."
                    },
                    {
                        "body": "Schema enforcement refuses a bad write at commit time, instead of "
                        "letting every future reader discover the problem. Try it yourself in the "
                        "Practice tab."
                    },
                ],
            },
            "practice": {
                "prompt": "Return only the rows that satisfy a NOT NULL account_id and a positive amount - the ones a schema-enforced write would have accepted.",
                "table_name": "incoming_writes",
                "schema": [
                    {"column": "id", "type": "bigint"},
                    {"column": "account_id", "type": "bigint"},
                    {"column": "amount", "type": "numeric"},
                ],
                "example_rows": [
                    {"id": 1, "account_id": 101, "amount": 50.00},
                    {"id": 2, "account_id": None, "amount": 20.00},
                    {"id": 3, "account_id": 102, "amount": -5.00},
                    {"id": 4, "account_id": 103, "amount": 75.00},
                ],
                "expected_output_rows": [
                    {"id": 1, "account_id": 101, "amount": 50.00},
                    {"id": 4, "account_id": 103, "amount": 75.00},
                ],
            },
        },
        {
            "id": "node_3_schema_evolution",
            "type": "skill",
            "title": "Schema evolution: adding a column without breaking old readers",
            "teach": {
                "sql": "SELECT id, user_id, COALESCE(source_app, 'unknown') AS source_app\nFROM events;",
                "note": (
                    "Schema enforcement (node 2) sounds like it should make adding a column "
                    "painful - wouldn't every old row now violate the new, stricter schema? Table "
                    "formats solve this with schema evolution: a new column is added as nullable, "
                    "every existing row is treated as having NULL for it (no rewrite of old data "
                    "required), and new rows can populate it going forward. Old readers that don't "
                    "know about the new column keep working unmodified; new readers that do know "
                    "about it, as here, just need to handle the NULL case for pre-evolution rows."
                ),
                "steps": [
                    {
                        "body": "Enforcement (node 2) sounds like it should make adding a column "
                        "painful - wouldn't every existing row now violate the stricter schema?"
                    },
                    {
                        "body": "A newly added column is nullable for every pre-existing row:",
                        "sql": "SELECT id, COALESCE(new_col, 'default') AS new_col\nFROM table;",
                    },
                    {
                        "body": "Return source_app for every event, with a safe default for rows older than the column:",
                        "sql": "SELECT id, user_id, COALESCE(source_app, 'unknown') AS source_app\nFROM events;",
                    },
                    {
                        "body": "Schema evolution adds source_app as nullable - every row that "
                        "existed before the column was added is automatically treated as NULL for "
                        "it, with no rewrite of old data required. New rows populate it going "
                        "forward; old rows just read back as NULL until a query decides what "
                        "default makes sense, same as here."
                    },
                    {
                        "body": "This is deliberately one-directional in the safe case: ADDING a "
                        "nullable column never breaks an old reader, since it simply doesn't know "
                        "the new column exists and keeps selecting what it always selected. "
                        "RENAMING or DROPPING a column, or adding one as NOT NULL with no default, "
                        "are the genuinely breaking schema changes - they change the meaning of "
                        "something an old reader is already relying on."
                    },
                    {
                        "body": "This is also why schema drift (Lake track, node 5) and schema "
                        "evolution look similar but solve different problems: drift is what "
                        "happens when there's NO table format tracking the schema at all (the "
                        "producer just started sending a differently-shaped row, with no record of "
                        "when). Evolution is a table format's explicit, versioned, intentional "
                        "change to a schema it already governs."
                    },
                    {
                        "body": "Adding a column safely means making it nullable and letting old "
                        "rows read back as NULL for it, with no rewrite required. Try it yourself "
                        "in the Practice tab."
                    },
                ],
            },
            "practice": {
                "prompt": "Return source_app for every event, defaulting to 'unknown' for rows from before the column existed.",
                "table_name": "events",
                "schema": [
                    {"column": "id", "type": "bigint"},
                    {"column": "user_id", "type": "text"},
                    {"column": "source_app", "type": "text"},
                ],
                "example_rows": [
                    {"id": 1, "user_id": "u1", "source_app": None},
                    {"id": 2, "user_id": "u2", "source_app": "mobile"},
                ],
                "expected_output_rows": [
                    {"id": 1, "user_id": "u1", "source_app": "unknown"},
                    {"id": 2, "user_id": "u2", "source_app": "mobile"},
                ],
            },
        },
        {
            "id": "node_4_merge_upsert",
            "type": "skill",
            "title": "MERGE/upsert: insert if new, update if it already exists",
            "teach": {
                "sql": (
                    "INSERT INTO accounts_current (id, balance) VALUES (1, 250.00)\n"
                    "ON CONFLICT (id) DO UPDATE SET balance = EXCLUDED.balance\n"
                    "RETURNING id, balance;"
                ),
                "note": (
                    "A Delta/Iceberg MERGE INTO statement does one conditional thing per matched "
                    "key: update the row if it already exists in the target table, insert it if it "
                    "doesn't - in one atomic operation, not a separate SELECT-then-decide dance that "
                    "could race against another writer. Postgres's own upsert, INSERT ... ON "
                    "CONFLICT ... DO UPDATE, is the exact same idea in miniature: account 1 already "
                    "exists here, so the ON CONFLICT branch fires and its balance is updated in "
                    "place, atomically, rather than erroring on the duplicate key or silently "
                    "inserting a second row for the same id."
                ),
                "steps": [
                    {
                        "body": "A lakehouse's MERGE INTO does one conditional thing per key: "
                        "update the row if it already exists, insert it if it doesn't - atomically, "
                        "in one operation, never as a separate 'check then decide' that could race "
                        "against another writer."
                    },
                    {
                        "body": "Postgres's upsert is the same idea, scoped to one table:",
                        "sql": "INSERT INTO t (id, val) VALUES (1, 'x')\nON CONFLICT (id) DO UPDATE SET val = EXCLUDED.val;",
                    },
                    {
                        "body": "Upsert account 1's balance to 250.00:",
                        "sql": (
                            "INSERT INTO accounts_current (id, balance) VALUES (1, 250.00)\n"
                            "ON CONFLICT (id) DO UPDATE SET balance = EXCLUDED.balance\n"
                            "RETURNING id, balance;"
                        ),
                    },
                    {
                        "body": "Account 1 already exists, so the ON CONFLICT branch fires: its "
                        "balance is updated in place, atomically. If account 1 hadn't existed yet, "
                        "the same statement would have inserted it fresh instead - one statement, "
                        "two possible outcomes, chosen automatically by whether the key already "
                        "exists."
                    },
                    {
                        "body": "Without ON CONFLICT, a plain INSERT against an existing id would "
                        "either error (duplicate key violation, if id has a uniqueness constraint) "
                        "or silently create a second row for the same logical account (if it "
                        "doesn't) - both worse outcomes than the single, correct, atomic upsert."
                    },
                    {
                        "body": "A real MERGE INTO can express more than this - different actions "
                        "for matched vs. unmatched rows, conditional deletes, multiple source rows "
                        "merging against one target row - but the core idea is identical: decide "
                        "insert-vs-update per key, in one atomic pass, instead of two separate "
                        "racy statements."
                    },
                    {
                        "body": "Upsert conditionally inserts or updates by key, in one atomic "
                        "statement, never as two separate racy steps. Try it yourself in the "
                        "Practice tab."
                    },
                ],
            },
            "practice": {
                "prompt": "Upsert account 1's balance to 250.00 - update it if the account already exists.",
                "table_name": "accounts_current",
                "schema": [
                    {"column": "id", "type": "bigint primary key"},
                    {"column": "balance", "type": "numeric"},
                ],
                "example_rows": [
                    {"id": 1, "balance": 100.00},
                ],
                "expected_output_rows": [
                    {"id": 1, "balance": 250.00},
                ],
                "starter_sql": "INSERT INTO accounts_current (id, balance) VALUES (1, 250.00)\nON CONFLICT (id) DO UPDATE SET balance = EXCLUDED.balance\nRETURNING id, balance;",
            },
        },
        {
            "id": "node_5_time_travel",
            "type": "skill",
            "title": "Time travel: querying an older version of the table",
            "teach": {
                "sql": "SELECT account_id, balance\nFROM accounts_versions\nWHERE version = 2;",
                "note": (
                    "Every commit to a Delta/Iceberg table creates a new, numbered (or timestamped) "
                    "version, and old versions aren't deleted outright - they stay queryable until "
                    "something explicitly vacuums them (node 10). 'Time travel' means querying one "
                    "of those older versions directly, as if the table had never been written to "
                    "since - VERSION AS OF 2 in Delta's own syntax, or, here, a plain WHERE version "
                    "= 2 against a table that explicitly keeps every version as its own rows, the "
                    "same idea in Postgres form."
                ),
                "steps": [
                    {
                        "body": "Every commit creates a new, numbered version of the table - and "
                        "old versions aren't deleted outright. They stay queryable until something "
                        "explicitly cleans them up."
                    },
                    {
                        "body": "Querying an old version just means filtering to it directly:",
                        "sql": "SELECT key, val FROM table_versions\nWHERE version = 5;",
                    },
                    {
                        "body": "Return this account's balance as of version 2, not the current version:",
                        "sql": "SELECT account_id, balance\nFROM accounts_versions\nWHERE version = 2;",
                    },
                    {
                        "body": "VERSION AS OF 2 is Delta's own syntax for exactly this - query "
                        "the table as it looked right after commit 2, ignoring every commit that "
                        "came after. This table models that by keeping every version as its own "
                        "explicit row instead of overwriting in place."
                    },
                    {
                        "body": "Time travel's classic uses: debugging ('what did this table look "
                        "like right before the bad job ran'), audit/compliance ('what value did "
                        "this row actually have on this date'), and reproducing an old report "
                        "exactly, even after the underlying data has since changed."
                    },
                    {
                        "body": "Time travel isn't free forever - it only works back as far as the "
                        "retention window the table's VACUUM policy keeps (node 10). Query far "
                        "enough back and the files that version depended on may already be gone, "
                        "even though the transaction log still remembers the version existed."
                    },
                    {
                        "body": "Time travel queries an older, still-retained version of the table "
                        "directly, as if nothing had been written since. Try it yourself in the "
                        "Practice tab."
                    },
                ],
            },
            "practice": {
                "prompt": "Return this account's balance as of version 2 - not its current version.",
                "table_name": "accounts_versions",
                "schema": [
                    {"column": "version", "type": "bigint"},
                    {"column": "account_id", "type": "bigint"},
                    {"column": "balance", "type": "numeric"},
                ],
                "example_rows": [
                    {"version": 1, "account_id": 101, "balance": 100.00},
                    {"version": 2, "account_id": 101, "balance": 150.00},
                    {"version": 3, "account_id": 101, "balance": 175.00},
                ],
                "expected_output_rows": [
                    {"account_id": 101, "balance": 150.00},
                ],
            },
        },
        {
            "id": "node_6_transaction_log",
            "type": "skill",
            "title": "The transaction log: replaying commits to get current state",
            "teach": {
                "sql": (
                    "SELECT account_id, SUM(CASE WHEN op = 'withdraw' THEN -amount ELSE amount END) AS balance\n"
                    "FROM txn_log\n"
                    "GROUP BY account_id;"
                ),
                "note": (
                    "A table format never stores 'the current state' as a single mutable thing - it "
                    "stores a log of every commit (add these files, remove those files, in this "
                    "order), and 'current state' is simply the result of replaying that entire log "
                    "from the start. This query models exactly that: txn_log is the commit history "
                    "(open, deposit, withdraw), and summing each operation's effect in order - "
                    "positive for an open/deposit, negative for a withdraw - reconstructs the "
                    "current balance the same way a table format reconstructs a table's current "
                    "rows by replaying its own log."
                ),
                "steps": [
                    {
                        "body": "A table format never stores 'the current state' as one mutable "
                        "thing - it stores a LOG of every commit, and current state is just the "
                        "result of replaying that log from the start."
                    },
                    {
                        "body": "Replaying a log means folding each entry's effect in order:",
                        "sql": "SELECT key, SUM(CASE WHEN op = 'sub' THEN -val ELSE val END)\nFROM log GROUP BY key;",
                    },
                    {
                        "body": "Reconstruct each account's current balance by replaying its log:",
                        "sql": (
                            "SELECT account_id, SUM(CASE WHEN op = 'withdraw' THEN -amount ELSE amount END) AS balance\n"
                            "FROM txn_log\n"
                            "GROUP BY account_id;"
                        ),
                    },
                    {
                        "body": "txn_log IS the source of truth here, not a side record of it - "
                        "'open' and 'deposit' add to the balance, 'withdraw' subtracts, and summing "
                        "every entry for an account in order reconstructs its current balance "
                        "exactly, the same way a table format reconstructs current rows by "
                        "replaying every add-file/remove-file commit in its log."
                    },
                    {
                        "body": "This is also exactly why time travel (node 5) is possible at "
                        "all: querying an old version just means replaying the log only up through "
                        "that commit, instead of all the way to the end - the log doesn't need a "
                        "separate mechanism for 'current' vs. 'historical', just a different "
                        "stopping point."
                    },
                    {
                        "body": "Real table formats checkpoint periodically (materializing the "
                        "replayed state every N commits) purely for performance, so a reader "
                        "doesn't have to replay a million-commit log from entry 1 every single "
                        "time - but the checkpoint is a cached answer, not a different source of "
                        "truth than the log itself."
                    },
                    {
                        "body": "Current state is the log replayed from the start - never a "
                        "separately maintained mutable value. Try it yourself in the Practice tab."
                    },
                ],
            },
            "practice": {
                "prompt": "Reconstruct each account's current balance by replaying its transaction log (withdraw subtracts, everything else adds).",
                "table_name": "txn_log",
                "schema": [
                    {"column": "log_id", "type": "bigint"},
                    {"column": "account_id", "type": "bigint"},
                    {"column": "op", "type": "text"},
                    {"column": "amount", "type": "numeric"},
                ],
                "example_rows": [
                    {"log_id": 1, "account_id": 101, "op": "open", "amount": 100.00},
                    {"log_id": 2, "account_id": 101, "op": "deposit", "amount": 50.00},
                    {"log_id": 3, "account_id": 101, "op": "withdraw", "amount": 30.00},
                    {"log_id": 4, "account_id": 102, "op": "open", "amount": 200.00},
                ],
                "expected_output_rows": [
                    {"account_id": 101, "balance": 120.00},
                    {"account_id": 102, "balance": 200.00},
                ],
            },
        },
        {
            "id": "node_7_optimistic_concurrency",
            "type": "skill",
            "title": "Optimistic concurrency: catching a conflicting concurrent writer",
            "teach": {
                "sql": (
                    "UPDATE accounts_optimistic\n"
                    "SET balance = 500, version = version + 1\n"
                    "WHERE id = 1 AND version = 1\n"
                    "RETURNING id, balance, version;"
                ),
                "note": (
                    "A table format lets two writers both start a transaction against the same "
                    "table version, but only one of their commits can actually win - the second "
                    "writer's commit is rejected and must retry, because the table has moved on "
                    "since it read. The version column here is the Postgres stand-in for that "
                    "check: this UPDATE only succeeds WHERE version = 1, the version this writer "
                    "last read, but another writer already bumped it to 2 - so this statement "
                    "matches zero rows, correctly detecting the conflict instead of silently "
                    "overwriting the other writer's change."
                ),
                "steps": [
                    {
                        "body": "Two writers can both start a transaction against the same table "
                        "version - but only one of their commits can actually win. The loser must "
                        "detect the conflict and retry, not silently overwrite the winner."
                    },
                    {
                        "body": "An UPDATE guarded by the version you last read is the check:",
                        "sql": "UPDATE t SET val = 'new', version = version + 1\nWHERE id = 1 AND version = 1;",
                    },
                    {
                        "body": "Try to update account 1, but only if its version is still 1 (what you last read):",
                        "sql": (
                            "UPDATE accounts_optimistic\n"
                            "SET balance = 500, version = version + 1\n"
                            "WHERE id = 1 AND version = 1\n"
                            "RETURNING id, balance, version;"
                        ),
                    },
                    {
                        "body": "Account 1's version is already 2 - someone else committed first. "
                        "This UPDATE's WHERE clause matches zero rows, so RETURNING produces no "
                        "rows at all: the conflict is detected correctly, not papered over by "
                        "silently applying the write anyway on top of a value this writer never "
                        "actually saw."
                    },
                    {
                        "body": "This is 'optimistic' concurrency specifically because no lock is "
                        "held while the writer was deciding what to write - it just assumed nobody "
                        "else would commit in the meantime, and checks that assumption only at "
                        "commit time via the version match. A pessimistic approach would instead "
                        "lock the row up front, blocking the second writer entirely until the "
                        "first finishes."
                    },
                    {
                        "body": "The correct response to zero rows updated is to retry: re-read "
                        "the current version (2), recompute the new balance against it, and issue "
                        "a fresh UPDATE ... WHERE version = 2 - never to just resubmit the same "
                        "stale write and hope it eventually succeeds."
                    },
                    {
                        "body": "A version-guarded UPDATE matching zero rows is how optimistic "
                        "concurrency catches a conflicting concurrent writer. Try it yourself in "
                        "the Practice tab."
                    },
                ],
            },
            "practice": {
                "prompt": "Try to update account 1's balance to 500, but only if its version is still 1 - detect the conflict if someone already wrote first.",
                "table_name": "accounts_optimistic",
                "schema": [
                    {"column": "id", "type": "bigint primary key"},
                    {"column": "balance", "type": "numeric"},
                    {"column": "version", "type": "bigint"},
                ],
                "example_rows": [
                    {"id": 1, "balance": 200.00, "version": 2},
                ],
                "expected_output_rows": [],
            },
        },
        {
            "id": "node_8_compaction_optimize",
            "type": "skill",
            "title": "OPTIMIZE: compacting many small commits into fewer larger ones",
            "teach": {
                "sql": (
                    "SELECT table_partition, SUM(rows_written) AS total_rows, COUNT(*) AS commit_count\n"
                    "FROM commit_log_fragments\n"
                    "GROUP BY table_partition;"
                ),
                "note": (
                    "A lakehouse table that accepts frequent small commits (streaming upserts, "
                    "say) accumulates exactly the small-file problem the plain Lake track covers "
                    "(node 8 there) - except here it's framed at the COMMIT level, not just the "
                    "file level: many small commits, each adding a few files, instead of fewer "
                    "commits each adding a well-sized batch. OPTIMIZE (Delta's own command) "
                    "rewrites a partition's many small files into fewer large ones as a single new "
                    "commit, without changing the logical data at all - this query is the same "
                    "accounting as the plain Lake track's compaction node, run one layer up, at the "
                    "granularity of commits instead of raw files."
                ),
                "steps": [
                    {
                        "body": "A table accepting frequent small commits (streaming upserts) "
                        "accumulates the same small-file problem the plain lake has - just framed "
                        "at the COMMIT level: many small commits instead of fewer well-sized ones."
                    },
                    {
                        "body": "Total up how fragmented each partition's commit history is:",
                        "sql": "SELECT partition, SUM(rows), COUNT(*)\nFROM commit_log\nGROUP BY partition;",
                    },
                    {
                        "body": "Total rows written and commit count per table_partition:",
                        "sql": (
                            "SELECT table_partition, SUM(rows_written) AS total_rows, COUNT(*) AS commit_count\n"
                            "FROM commit_log_fragments\n"
                            "GROUP BY table_partition;"
                        ),
                    },
                    {
                        "body": "A partition with a high commit_count relative to its total_rows "
                        "has a lot of small commits behind it - exactly what OPTIMIZE targets: it "
                        "rewrites those many small files into fewer large ones as a single new "
                        "commit, leaving the logical data (every row, every value) completely "
                        "unchanged."
                    },
                    {
                        "body": "This is the same concept as the plain Lake track's compaction "
                        "(node 8 there), just one layer up: that one compacts raw FILES sitting in "
                        "a lake with no transaction log at all; this one compacts COMMITS in a "
                        "table format that tracks every one of them explicitly - a lakehouse table "
                        "actually knows exactly how fragmented it is, because the log itself is the "
                        "record of every commit."
                    },
                    {
                        "body": "OPTIMIZE, like compaction, is a maintenance operation run "
                        "periodically, not a side effect of every write - it's a deliberate "
                        "tradeoff of compute time now for faster reads later."
                    },
                    {
                        "body": "OPTIMIZE rewrites many small commits' files into fewer large "
                        "ones, as one new commit, with zero change to the logical data. Try it "
                        "yourself in the Practice tab."
                    },
                ],
            },
            "practice": {
                "prompt": "Total rows_written and count the commits for each table_partition.",
                "table_name": "commit_log_fragments",
                "schema": [
                    {"column": "commit_id", "type": "bigint"},
                    {"column": "table_partition", "type": "text"},
                    {"column": "rows_written", "type": "bigint"},
                ],
                "example_rows": [
                    {"commit_id": 1, "table_partition": "p1", "rows_written": 10},
                    {"commit_id": 2, "table_partition": "p1", "rows_written": 15},
                    {"commit_id": 3, "table_partition": "p2", "rows_written": 40},
                ],
                "expected_output_rows": [
                    {"table_partition": "p1", "total_rows": 25, "commit_count": 2},
                    {"table_partition": "p2", "total_rows": 40, "commit_count": 1},
                ],
            },
        },
        {
            "id": "node_9_zorder_data_skipping",
            "type": "skill",
            "title": "Z-ordering: data skipping across more than one column at once",
            "teach": {
                "sql": "SELECT id, region, amount\nFROM order_records\nWHERE region = 'US' AND amount > 500;",
                "note": (
                    "Plain data skipping (Lake track, node 10) works great for a filter on a single "
                    "column, but min/max stats help far less when a query filters on TWO columns "
                    "together (region = 'US' AND amount > 500) unless rows with similar region AND "
                    "amount values are physically clustered into the same files - otherwise nearly "
                    "every file has some US rows and some high-amount rows, so almost nothing can "
                    "be skipped. Z-ordering is a layout operation that physically clusters rows by "
                    "MULTIPLE columns' combined values, so a file's min/max stats on both columns "
                    "together actually become useful for a two-column filter like this one."
                ),
                "steps": [
                    {
                        "body": "Plain min/max data skipping works great for a filter on ONE "
                        "column. What about a filter on TWO columns together, like region AND "
                        "amount here?"
                    },
                    {
                        "body": "A multi-column filter is the shape Z-ordering is built to exploit:",
                        "sql": "SELECT id FROM t\nWHERE region = 'US' AND amount > 500;",
                    },
                    {
                        "body": "Return every US order over 500:",
                        "sql": "SELECT id, region, amount\nFROM order_records\nWHERE region = 'US' AND amount > 500;",
                    },
                    {
                        "body": "If rows are scattered randomly across files, nearly every file "
                        "has SOME US rows and SOME high-amount rows, so a file's min/max stats on "
                        "either column alone rule almost nothing out. Z-ordering physically "
                        "clusters rows by both columns' combined values when files are written, so "
                        "a file's stats on region AND amount together actually become useful for "
                        "exactly this two-column filter."
                    },
                    {
                        "body": "Z-ordering is a write-time (or OPTIMIZE-time) layout decision, "
                        "not a query-time one - a query can't ask for Z-ordering on demand the way "
                        "it can add a WHERE clause; the table has to already be laid out that way "
                        "before this filter can benefit from it."
                    },
                    {
                        "body": "Picking which columns to Z-order by is a real design tradeoff: "
                        "clustering by region and amount helps THIS query, but might hurt a "
                        "different query that filters on country and device instead - Z-ordering "
                        "optimizes for whichever multi-column filters actually show up often in "
                        "practice, not every possible filter combination at once."
                    },
                    {
                        "body": "Z-ordering clusters rows by more than one column at once, so "
                        "multi-column filters can skip files the same way single-column filters "
                        "already could. Try it yourself in the Practice tab."
                    },
                ],
            },
            "practice": {
                "prompt": "Return every order from the US region with an amount over 500.",
                "table_name": "order_records",
                "schema": [
                    {"column": "id", "type": "bigint"},
                    {"column": "region", "type": "text"},
                    {"column": "amount", "type": "numeric"},
                ],
                "example_rows": [
                    {"id": 1, "region": "US", "amount": 600.00},
                    {"id": 2, "region": "US", "amount": 400.00},
                    {"id": 3, "region": "EU", "amount": 900.00},
                ],
                "expected_output_rows": [
                    {"id": 1, "region": "US", "amount": 600.00},
                ],
            },
        },
        {
            "id": "node_10_retention_vacuum",
            "type": "skill",
            "title": "Retention and VACUUM: finding old versions eligible for cleanup",
            "teach": {
                "sql": "SELECT version\nFROM table_versions\nWHERE committed_at < '2026-01-10';",
                "note": (
                    "Time travel (node 5) only works because old versions aren't deleted the "
                    "instant a new commit supersedes them - but keeping every version forever would "
                    "mean storage grows without bound. VACUUM deletes files belonging to versions "
                    "older than a configured retention window (commonly 7 days), once they're no "
                    "longer needed for time travel within that window. This query is exactly that "
                    "eligibility check: find every version committed before the retention cutoff, "
                    "which is precisely what a VACUUM run would consider safe to delete."
                ),
                "steps": [
                    {
                        "body": "Time travel only works because old versions AREN'T deleted the "
                        "instant a new commit supersedes them - but keeping every version forever "
                        "means storage grows without bound."
                    },
                    {
                        "body": "Find every version older than the retention cutoff:",
                        "sql": "SELECT version FROM table_versions\nWHERE committed_at < 'cutoff_date';",
                    },
                    {
                        "body": "Find every version committed before 2026-01-10 - eligible for VACUUM:",
                        "sql": "SELECT version\nFROM table_versions\nWHERE committed_at < '2026-01-10';",
                    },
                    {
                        "body": "This is exactly the eligibility check a real VACUUM run performs "
                        "before deleting anything: any version older than the retention window "
                        "(commonly 7 days) is a candidate for cleanup, since time travel back to it "
                        "is no longer guaranteed to be needed."
                    },
                    {
                        "body": "The retention window is a genuine tradeoff, not a free safety "
                        "margin - a longer window means more storage spent holding onto old "
                        "versions nobody may ever query again; a shorter window means time travel "
                        "and debugging queries against recent-but-already-vacuumed history simply "
                        "fail, with no way to recover the deleted files."
                    },
                    {
                        "body": "VACUUM has to be careful not to delete a file that's still part "
                        "of the CURRENT version just because it's old - a file written long ago "
                        "that's never been superseded is still live data, not an old version "
                        "eligible for cleanup. Eligibility is about whether a version has been "
                        "SUPERSEDED and aged out, not about a file's raw age."
                    },
                    {
                        "body": "VACUUM finds versions older than the retention window and reclaims "
                        "their storage, trading time-travel depth for lower storage cost. Try it "
                        "yourself in the Practice tab."
                    },
                ],
            },
            "practice": {
                "prompt": "Find every version committed before 2026-01-10 - the ones eligible for VACUUM.",
                "table_name": "table_versions",
                "schema": [
                    {"column": "version", "type": "bigint"},
                    {"column": "committed_at", "type": "timestamptz"},
                ],
                "example_rows": [
                    {"version": 1, "committed_at": "2026-01-01T00:00:00+00"},
                    {"version": 2, "committed_at": "2026-01-05T00:00:00+00"},
                    {"version": 3, "committed_at": "2026-01-12T00:00:00+00"},
                ],
                "expected_output_rows": [
                    {"version": 1},
                    {"version": 2},
                ],
            },
        },
        {
            "id": "review",
            "type": "review",
            "title": "Review: atomic commits, schema enforcement/evolution, upsert, time travel, transaction log, concurrency, compaction, Z-ordering, retention",
            "prompt": (
                "A quick recap of a lakehouse table format's own ACID mechanics in SQL form before "
                "moving into the Lakehouse capstone, which builds this same table format for real - "
                "against the actual fintech feed, on real Delta/Iceberg tables, at full scale."
            ),
        },
    ],
}
