export const $ = (selector, root = document) => root.querySelector(selector);
export const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

export function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

export function initials(name) {
  return String(name || "User")
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0].toUpperCase())
    .join("");
}

export function formatDate(value) {
  if (!value) return "—";
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function showToast(message, type = "success") {
  const region = $("#toast-region");
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.innerHTML = `<span class="toast-dot"></span><span>${escapeHtml(message)}</span><button type="button" aria-label="Dismiss">×</button>`;
  toast.querySelector("button").addEventListener("click", () => toast.remove());
  region.append(toast);
  window.setTimeout(() => toast.remove(), 4200);
}

export function setLoading(isLoading) {
  $("#loading-overlay").classList.toggle("hidden", !isLoading);
}

export function showModal(selector) {
  const modal = $(selector);
  modal.classList.remove("hidden");
  document.body.style.overflow = "hidden";
  window.setTimeout(() => modal.querySelector("input, button")?.focus(), 0);
}

export function hideModal(selector) {
  $(selector).classList.add("hidden");
  document.body.style.overflow = "";
}

export function getBookColor(bookId) {
  const palette = ["#174d42", "#8b5b43", "#3d567c", "#73577d", "#976a2f"];
  return palette[Math.abs(Number(bookId) || 0) % palette.length];
}
