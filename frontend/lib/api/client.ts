const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public payload: unknown,
  ) {
    super(message);
  }
}

function token(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem("interviewos_token");
}

export function setToken(value: string | null) {
  if (typeof window === "undefined") return;
  if (value) window.localStorage.setItem("interviewos_token", value);
  else window.localStorage.removeItem("interviewos_token");
}

function readErrorMessage(data: unknown, fallback: string): string {
  if (!data || typeof data !== "object") return fallback;
  const payload = data as Record<string, unknown>;
  if (typeof payload.message === "string" && payload.message.trim()) return payload.message;
  const detail = payload.detail;
  if (typeof detail === "string" && detail.trim()) return detail;
  if (detail && typeof detail === "object" && !Array.isArray(detail)) {
    const nested = detail as Record<string, unknown>;
    if (typeof nested.message === "string" && nested.message.trim()) return nested.message;
  }
  if (Array.isArray(detail)) {
    const parts = detail
      .map((item) => {
        if (typeof item === "string") return item;
        if (item && typeof item === "object" && "msg" in item) {
          return String((item as { msg: unknown }).msg);
        }
        return "";
      })
      .filter(Boolean);
    if (parts.length) return parts.join("; ");
  }
  return fallback;
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  const auth = token();
  if (auth) headers.set("Authorization", `Bearer ${auth}`);
  if (init.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, { ...init, headers });
  } catch {
    throw new ApiError(
      `Cannot reach the InterviewOS API at ${API_URL}. Start the backend and confirm NEXT_PUBLIC_API_URL.`,
      0,
      null,
    );
  }
  const text = await response.text();
  let data: unknown = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = { message: text.slice(0, 240) };
    }
  }
  if (!response.ok) {
    throw new ApiError(readErrorMessage(data, response.statusText || "Request failed"), response.status, data);
  }
  return data as T;
}

async function requestBlob(path: string, body: unknown, signal?: AbortSignal): Promise<Blob> {
  const headers = new Headers({ "Content-Type": "application/json" });
  const auth = token();
  if (auth) headers.set("Authorization", `Bearer ${auth}`);
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      method: "POST",
      headers,
      body: JSON.stringify(body),
      signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw new ApiError(
      `Cannot reach the InterviewOS API at ${API_URL}. Start the backend and confirm NEXT_PUBLIC_API_URL.`,
      0,
      null,
    );
  }
  if (!response.ok) {
    const text = await response.text();
    let data: unknown = null;
    try {
      data = text ? JSON.parse(text) : null;
    } catch {
      data = { message: text.slice(0, 240) };
    }
    throw new ApiError(readErrorMessage(data, response.statusText || "Request failed"), response.status, data);
  }
  return response.blob();
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  postBlob: (path: string, body: unknown, signal?: AbortSignal) => requestBlob(path, body, signal),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, {
      method: "POST",
      body: body instanceof FormData ? body : body ? JSON.stringify(body) : undefined,
    }),
  patch: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "PATCH", body: JSON.stringify(body) }),
  delete: <T>(path: string) => request<T>(path, { method: "DELETE" }),
};
