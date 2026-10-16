"""Module 16: persistence for per-user progress - node completions, XP
total, streak, badges. All writes go through record_node_completion,
the one place XP/streak/badge logic actually runs; reads are a thin
SELECT. Idempotent by design - completing an already-completed node
again is a no-op (returns current state, no double XP/streak credit),
since the node-check endpoint has no other way to know a submission is a
repeat attempt rather than the first pass.

Concurrency note: the read-then-write of progress.user_stats isn't
wrapped in row-level locking beyond a plain UPDATE/INSERT - acceptable
here for the same reason PySpark's single-session design was (see
ARCHITECTURE_DECISIONS.md §3.2): primary usage is the user alone, not
concurrent multi-user traffic."""

from datetime import datetime, timezone

from psycopg import Connection
from psycopg.rows import dict_row

from app.modules.progress.xp_rules import capstone_badge_for, newly_earned_badges, update_streak, xp_for_node


def get_progress(conn: Connection, user_id: int) -> dict:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT xp_total, current_streak, longest_streak, last_activity_date "
            "FROM progress.user_stats WHERE user_id = %s",
            (user_id,),
        )
        stats = cur.fetchone() or {
            "xp_total": 0,
            "current_streak": 0,
            "longest_streak": 0,
            "last_activity_date": None,
        }

        cur.execute(
            "SELECT paradigm, node_id FROM progress.node_completions WHERE user_id = %s",
            (user_id,),
        )
        completions = cur.fetchall()

        cur.execute("SELECT badge_id FROM progress.badges WHERE user_id = %s", (user_id,))
        badges = [row["badge_id"] for row in cur.fetchall()]

    completed_by_paradigm: dict[str, list[str]] = {}
    for row in completions:
        completed_by_paradigm.setdefault(row["paradigm"], []).append(row["node_id"])

    return {
        "xp_total": stats["xp_total"],
        "current_streak": stats["current_streak"],
        "longest_streak": stats["longest_streak"],
        "badges": badges,
        "completed_nodes": completed_by_paradigm,
    }


def record_node_completion(conn: Connection, user_id: int, paradigm: str, node_id: str, node_type: str) -> dict:
    today = datetime.now(timezone.utc).date()

    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT 1 FROM progress.node_completions WHERE user_id = %s AND paradigm = %s AND node_id = %s",
            (user_id, paradigm, node_id),
        )
        if cur.fetchone() is not None:
            result = get_progress(conn, user_id)
            result["newly_awarded_xp"] = 0
            result["new_badges"] = []
            return result

        cur.execute(
            "SELECT xp_total, current_streak, longest_streak, last_activity_date "
            "FROM progress.user_stats WHERE user_id = %s",
            (user_id,),
        )
        row = cur.fetchone()
        xp_total = row["xp_total"] if row else 0
        current_streak = row["current_streak"] if row else 0
        longest_streak = row["longest_streak"] if row else 0
        last_activity_date = row["last_activity_date"] if row else None

        awarded_xp = xp_for_node(node_type)
        new_streak, new_longest = update_streak(last_activity_date, today, current_streak, longest_streak)
        new_xp_total = xp_total + awarded_xp

        cur.execute(
            "INSERT INTO progress.user_stats "
            "(user_id, xp_total, current_streak, longest_streak, last_activity_date) "
            "VALUES (%s, %s, %s, %s, %s) "
            "ON CONFLICT (user_id) DO UPDATE SET "
            "xp_total = EXCLUDED.xp_total, current_streak = EXCLUDED.current_streak, "
            "longest_streak = EXCLUDED.longest_streak, last_activity_date = EXCLUDED.last_activity_date, "
            "updated_at = now()",
            (user_id, new_xp_total, new_streak, new_longest, today),
        )
        cur.execute(
            "INSERT INTO progress.node_completions (user_id, paradigm, node_id, xp_awarded) "
            "VALUES (%s, %s, %s, %s)",
            (user_id, paradigm, node_id, awarded_xp),
        )

        cur.execute("SELECT COUNT(*) AS n FROM progress.node_completions WHERE user_id = %s", (user_id,))
        total_nodes = cur.fetchone()["n"]
        cur.execute("SELECT badge_id FROM progress.badges WHERE user_id = %s", (user_id,))
        already_earned = {r["badge_id"] for r in cur.fetchall()}

        new_badges = newly_earned_badges(
            total_nodes_completed=total_nodes,
            current_streak=new_streak,
            xp_total=new_xp_total,
            already_earned=already_earned,
        )
        if node_type == "capstone":
            capstone_badge = capstone_badge_for(paradigm)
            if capstone_badge and capstone_badge.badge_id not in already_earned:
                new_badges.append(capstone_badge)
        for badge in new_badges:
            cur.execute(
                "INSERT INTO progress.badges (user_id, badge_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                (user_id, badge.badge_id),
            )

    conn.commit()

    result = get_progress(conn, user_id)
    result["newly_awarded_xp"] = awarded_xp
    result["new_badges"] = [badge.badge_id for badge in new_badges]
    return result
