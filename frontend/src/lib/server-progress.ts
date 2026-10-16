// Module 17: server-side-only progress helpers - reads the Auth.js
// session-token cookie directly (only possible in a Server Component /
// Route Handler, since it's httpOnly) and calls the backend. Shared by
// the XP header badge (a Server Component, no client round trip needed)
// and the /api/progress/* proxy route (used by client components, which
// can't read this cookie themselves).

import { cookies } from "next/headers";
import type { DailyChallengeDto, ProgressDto } from "./types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export async function sessionToken(): Promise<string | undefined> {
  const store = await cookies();
  // Auth.js prefixes the cookie name with "__Secure-" only when served
  // over https (see @auth/core/lib/utils/cookie.js) - check both since
  // local dev is plain http.
  return store.get("__Secure-authjs.session-token")?.value ?? store.get("authjs.session-token")?.value;
}

export async function fetchProgressServerSide(): Promise<ProgressDto | null> {
  const token = await sessionToken();
  if (!token) return null;
  try {
    const response = await fetch(`${API_BASE_URL}/progress/me`, {
      headers: { "X-Session-Token": token },
      cache: "no-store",
    });
    if (!response.ok) return null;
    return (await response.json()) as ProgressDto;
  } catch {
    return null;
  }
}

export async function fetchDailyChallengeServerSide(): Promise<DailyChallengeDto | null> {
  const token = await sessionToken();
  if (!token) return null;
  try {
    const response = await fetch(`${API_BASE_URL}/progress/daily/today`, {
      headers: { "X-Session-Token": token },
      cache: "no-store",
    });
    if (!response.ok) return null;
    return (await response.json()) as DailyChallengeDto;
  } catch {
    return null;
  }
}
