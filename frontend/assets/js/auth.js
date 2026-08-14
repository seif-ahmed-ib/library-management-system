import { apiRequest, jsonOptions, setToken } from "./api.js";

export async function login(email, password) {
  const body = new URLSearchParams({ username: email, password });
  const { data } = await apiRequest("/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });
  setToken(data.access_token);
  return data;
}

export async function registerAccount(account) {
  const { data } = await apiRequest(
    "/auth/register",
    jsonOptions("POST", account),
  );
  return data;
}

export async function getCurrentUser() {
  const { data } = await apiRequest("/auth/me");
  return data;
}
