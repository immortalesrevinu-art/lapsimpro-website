import { LAPSIMPRO_API_BASE } from "./api-config.js";

const TOKEN_KEY = "lsp_token";

export function apiBase() {
  if (window.LAPSIMPRO_API) return String(window.LAPSIMPRO_API).replace(/\/$/, "");
  if (location.port === "8787" || location.pathname.startsWith("/api")) return "";
  const host = location.hostname;
  if (host === "127.0.0.1" || host === "localhost") return "http://127.0.0.1:8787";
  return String(LAPSIMPRO_API_BASE || "").replace(/\/$/, "");
}

export function storedToken() {
  try {
    return localStorage.getItem(TOKEN_KEY) || "";
  } catch {
    return "";
  }
}

export function setToken(token) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* ignore */
  }
}

export async function api(path, options = {}) {
  const headers = { Accept: "application/json", ...(options.headers || {}) };
  if (options.body && !headers["Content-Type"]) headers["Content-Type"] = "application/json";
  const token = storedToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(`${apiBase()}${path}`, { credentials: "include", ...options, headers });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.detail || res.statusText || "Request failed");
    err.status = res.status;
    err.data = data;
    throw err;
  }
  return data;
}

export async function currentUser() {
  try {
    return await api("/api/me");
  } catch {
    return null;
  }
}

function wireNav() {
  const nav = document.getElementById("site-nav");
  const toggle = document.querySelector(".nav-toggle");
  toggle?.addEventListener("click", () => {
    const open = !nav?.classList.contains("open");
    nav?.classList.toggle("open", open);
    toggle.setAttribute("aria-expanded", String(open));
  });
}

function markNav() {
  const file = (location.pathname.split("/").pop() || "index.html").toLowerCase();
  const key = file.includes("dashboard")
    ? "dash"
    : file.includes("login") || file.includes("account")
      ? "account"
      : file.includes("leaderboard")
        ? "boards"
        : file.includes("coaching")
          ? "coaching"
          : file.includes("news")
            ? "news"
            : file.includes("livery") || file.includes("paint")
              ? "liveries"
              : file.includes("aid")
                ? "aid"
                : file.includes("pricing")
                  ? "pricing"
                  : file.includes("support") || file.includes("faq")
                    ? "support"
                    : file.includes("download") || file.includes("get-started")
                      ? "start"
                      : file.includes("404")
                        ? ""
                        : "home";
  document.querySelectorAll("[data-nav]").forEach((el) => {
    if (el.getAttribute("data-nav") === key) el.classList.add("active");
  });
}

function captureQueryToken() {
  try {
    const params = new URLSearchParams(location.search);
    const token = params.get("token");
    if (!token) return;
    setToken(token);
    params.delete("token");
    const next = `${location.pathname}${params.toString() ? `?${params}` : ""}${location.hash}`;
    history.replaceState({}, "", next);
  } catch {
    /* ignore */
  }
}

async function boot() {
  captureQueryToken();
  wireNav();
  markNav();
  const year = document.getElementById("year");
  if (year) year.textContent = String(new Date().getFullYear());
  const user = await currentUser();
  document.querySelectorAll("[data-auth-link]").forEach((el) => {
    if (user) {
      el.textContent = "Account";
      el.setAttribute("href", "./account.html");
    } else {
      el.textContent = "Log in";
      el.setAttribute("href", "./login.html");
    }
  });
  document.querySelectorAll("[data-auth-only]").forEach((el) => {
    el.hidden = !user;
  });
  document.querySelectorAll("[data-guest-only]").forEach((el) => {
    el.hidden = Boolean(user);
  });
  window.__lspUser = user;
  document.dispatchEvent(new CustomEvent("lsp:user", { detail: user }));
}

if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
else boot();
