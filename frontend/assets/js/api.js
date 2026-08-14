const API_BASE = "/api/v1";
const TOKEN_KEY = "library-token";

let accessToken = localStorage.getItem(TOKEN_KEY) || "";

export function hasToken() {
  return Boolean(accessToken);
}

export function setToken(token) {
  accessToken = token;
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  accessToken = "";
  localStorage.removeItem(TOKEN_KEY);
}

export async function apiRequest(path, options = {}) {
  const headers = new Headers(options.headers || {});

  if (accessToken) {
    headers.set("Authorization", `Bearer ${accessToken}`);
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  let data = null;
  if (response.status !== 204) {
    const contentType = response.headers.get("content-type") || "";
    data = contentType.includes("application/json")
      ? await response.json()
      : await response.text();
  }

  if (!response.ok) {
    const detail = data && typeof data === "object" ? data.detail : null;
    const error = new Error(detail || "The request could not be completed.");
    error.status = response.status;
    throw error;
  }

  return { data, headers: response.headers, status: response.status };
}

export function jsonOptions(method, body) {
  return {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  };
}
