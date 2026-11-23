import type { ApiErrorBody } from "../types/api";

export class ApiError extends Error {
  constructor(public code: string, message: string, public details?: Record<string, unknown>) {
    super(message);
  }
}

async function handle<T>(res: Response): Promise<T> {
  if (res.ok) return (await res.json()) as T;
  let body: ApiErrorBody | null = null;
  try { body = (await res.json()) as ApiErrorBody; } catch { /* abaikan */ }
  throw new ApiError(body?.error.code ?? "INTERNAL_ERROR", body?.error.message ?? res.statusText, body?.error.details);
}

export async function get<T>(path: string, params?: Record<string, string | number | boolean | undefined>, signal?: AbortSignal): Promise<T> {
  const q = params
    ? "?" + new URLSearchParams(Object.entries(params).filter(([, v]) => v !== undefined).map(([k, v]) => [k, String(v)])).toString()
    : "";
  return handle<T>(await fetch(`/api${path}${q}`, { signal }));
}

export async function post<T, B>(path: string, body: B, signal?: AbortSignal): Promise<T> {
  return handle<T>(await fetch(`/api${path}`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body), signal,
  }));
}

export async function postForm<T>(path: string, form: FormData, signal?: AbortSignal): Promise<T> {
  return handle<T>(await fetch(`/api${path}`, { method: "POST", body: form, signal }));
}
