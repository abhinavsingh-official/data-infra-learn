import NextAuth from "next-auth";
import Google from "next-auth/providers/google";
import PostgresAdapter from "@auth/pg-adapter";
import { Pool } from "pg";

/** A dedicated pool using auth_role (NOT app_role - see
 * docker/init/02_auth_role.sh), whose search_path is pinned to the `auth`
 * schema so the adapter's unqualified queries (SELECT * FROM users, etc.)
 * never collide with this project's own public.users/public.accounts
 * tables, which mean something completely different (fintech data).
 *
 * Database session strategy, not JWT - deliberate: Auth.js's default JWT
 * strategy encrypts (not just signs) the session token (JWE,
 * A256CBC-HS512), which the FastAPI backend would need real cryptographic
 * work to verify. With database sessions, the backend can instead just
 * read the same `auth.sessions` table directly via its own existing
 * Postgres admin connection - no cross-language token verification needed.
 *
 * AUTH_DB_SSL: unset locally (self-hosted Docker Postgres has no TLS
 * configured at all, so requesting SSL would just fail the handshake) -
 * set to "true" on the hosted deployment, where the database is Neon,
 * which refuses any non-TLS connection outright. */
const pool = new Pool({
  host: process.env.AUTH_DB_HOST,
  port: Number(process.env.AUTH_DB_PORT ?? 5433),
  database: process.env.AUTH_DB_NAME,
  user: process.env.AUTH_DB_USER,
  password: process.env.AUTH_DB_PASSWORD,
  ssl: process.env.AUTH_DB_SSL === "true" ? true : undefined,
});

export const { handlers, auth, signIn, signOut } = NextAuth({
  adapter: PostgresAdapter(pool),
  session: { strategy: "database" },
  providers: [Google],
  pages: {},
});
