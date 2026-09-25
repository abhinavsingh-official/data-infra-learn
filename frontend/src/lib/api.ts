import type { ExecuteResult, GradingReport, PostgresTask } from "./types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

class ApiError extends Error {}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      headers: { "Content-Type": "application/json" },
      ...init,
    });
  } catch {
    throw new ApiError(
      `Could not reach the backend at ${API_BASE_URL}. Is it running (uvicorn app.main:app)?`,
    );
  }
  if (!response.ok) {
    // FastAPI's HTTPException bodies are {"detail": "..."} - surface that
    // directly (e.g. "Session not found or expired") instead of a generic
    // status-code message, since the detail is the actionable part.
    const detail = await response
      .json()
      .then((body: { detail?: string }) => body.detail)
      .catch(() => undefined);
    throw new ApiError(detail ?? `Request to ${path} failed with status ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export function getPostgresTask() {
  return request<PostgresTask>("/postgres-phase/task");
}

export function createSession() {
  return request<{ session_id: string }>("/postgres-phase/sessions", { method: "POST" });
}

export function executeSql(sessionId: string, sql: string) {
  return request<ExecuteResult>(`/postgres-phase/sessions/${sessionId}/execute`, {
    method: "POST",
    body: JSON.stringify({ sql }),
  });
}

export function gradeSession(sessionId: string) {
  return request<GradingReport>(`/postgres-phase/sessions/${sessionId}/grade`, {
    method: "POST",
  });
}

export function endSession(sessionId: string) {
  return request<{ status: string }>(`/postgres-phase/sessions/${sessionId}`, {
    method: "DELETE",
  });
}

export { ApiError };
