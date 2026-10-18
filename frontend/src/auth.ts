import NextAuth from "next-auth";
import Google from "next-auth/providers/google";
import PostgresAdapter from "@auth/pg-adapter";
import { Pool } from "pg";

/** auth_role (not app_role), search_path pinned to `auth` so the
 * adapter's unqualified queries don't collide with public.users/
 * public.accounts (fintech data, unrelated). Database sessions, not
 * JWT, so the FastAPI backend can just read auth.sessions directly
 * instead of decrypting Auth.js's JWE tokens. AUTH_DB_SSL: unset
 * locally (no TLS on Docker Postgres), "true" on the hosted deployment
 * (Neon requires TLS). */
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
