import { boot } from "./boot";

export class ApiError extends Error {
  status: number;
  fields: Record<string, string[]>;

  constructor(message: string, status: number, fields: Record<string, string[]> = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.fields = fields;
  }
}

let csrfToken = boot.session.csrf_token;

export function setCsrfToken(token: string | undefined) {
  if (token) csrfToken = token;
}

type Params = Record<string, string | number | boolean | null | undefined | (string | number)[]>;

export function toQuery(params?: Params | URLSearchParams | string) {
  if (!params) return "";
  if (typeof params === "string") return params.replace(/^\?/, "");
  if (params instanceof URLSearchParams) return params.toString();
  const qs = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === "" || value === false) continue;
    if (Array.isArray(value)) value.forEach((v) => qs.append(key, String(v)));
    else qs.append(key, value === true ? "1" : String(value));
  }
  return qs.toString();
}

async function request<T>(method: string, path: string, body?: unknown, retry = true): Promise<T> {
  const url = path.startsWith("/api/") ? path : `/api/app${path}`;
  const headers: Record<string, string> = { Accept: "application/json" };
  if (method !== "GET") {
    headers["Content-Type"] = "application/json";
    headers["X-CSRFToken"] = csrfToken;
  }
  let response: Response;
  try {
    response = await fetch(url, {
      method,
      headers,
      credentials: "same-origin",
      body: body === undefined || method === "GET" ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new ApiError("You appear to be offline. Check your connection and try again.", 0);
  }
  const data = response.status === 204 ? {} : await response.json().catch(() => ({}));
  if (!response.ok) {
    // An expired CSRF token (e.g. after logging in elsewhere): refresh the session once and retry.
    if (response.status === 403 && retry && method !== "GET" && String(data.error ?? "").startsWith("CSRF")) {
      const session = await request<{ csrf_token: string }>("GET", "/session/", undefined, false);
      setCsrfToken(session.csrf_token);
      return request<T>(method, path, body, false);
    }
    const message = data.error ?? (response.status === 429 ? "Too many requests — please wait a moment." : `Something went wrong (HTTP ${response.status}).`);
    throw new ApiError(message, response.status, data.fields ?? {});
  }
  if (data && typeof data === "object" && "csrf_token" in data) setCsrfToken((data as { csrf_token: string }).csrf_token);
  return data as T;
}

export const api = {
  get: <T>(path: string, params?: Params | URLSearchParams | string) => {
    const qs = toQuery(params);
    return request<T>("GET", qs ? `${path}${path.includes("?") ? "&" : "?"}${qs}` : path);
  },
  post: <T>(path: string, body: unknown = {}) => request<T>("POST", path, body),
  put: <T>(path: string, body: unknown = {}) => request<T>("PUT", path, body),
  patch: <T>(path: string, body: unknown = {}) => request<T>("PATCH", path, body),
  delete: <T>(path: string, body?: unknown) => request<T>("DELETE", path, body),
};

export function errorMessage(error: unknown) {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message;
  return "Something went wrong.";
}
