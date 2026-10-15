// Module 17: a thin server-side proxy for the backend's /progress/* API.
// Auth.js's database-session cookie is httpOnly by design (Module 15) -
// client components can't read it via document.cookie, so a client-side
// fetch straight to the FastAPI backend has no way to prove who's signed
// in. This route runs server-side (where `cookies()` can read it),
// forwards it to the backend as the X-Session-Token header the backend
// already expects (see backend/app/core/session_auth.py), and relays the
// response back untouched.

import { NextRequest, NextResponse } from "next/server";
import { sessionToken } from "@/lib/server-progress";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function proxy(request: NextRequest, path: string[]): Promise<NextResponse> {
  const token = await sessionToken();
  const url = `${API_BASE_URL}/progress/${path.join("/")}`;

  const init: RequestInit = {
    method: request.method,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { "X-Session-Token": token } : {}),
    },
  };
  if (request.method !== "GET" && request.method !== "HEAD") {
    init.body = await request.text();
  }

  let backendResponse: Response;
  try {
    backendResponse = await fetch(url, init);
  } catch {
    return NextResponse.json(
      { detail: `Could not reach the backend at ${API_BASE_URL}.` },
      { status: 502 },
    );
  }
  const body = await backendResponse.text();
  return new NextResponse(body, {
    status: backendResponse.status,
    headers: { "Content-Type": "application/json" },
  });
}

export async function GET(request: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  const { path } = await params;
  return proxy(request, path);
}

export async function POST(request: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  const { path } = await params;
  return proxy(request, path);
}
