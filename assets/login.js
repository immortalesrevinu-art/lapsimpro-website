import { api, setToken } from "./account-nav.js";

const $ = (sel) => document.querySelector(sel);

function showNote(el, text, kind = "info") {
  el.hidden = false;
  el.className = `note ${kind}`;
  el.textContent = text;
}

async function register(event) {
  event.preventDefault();
  const note = $("#auth-note");
  try {
    const data = await api("/api/auth/register", {
      method: "POST",
      body: JSON.stringify({
        email: $("#reg-email").value,
        password: $("#reg-password").value,
      }),
    });
    setToken(data.token);
    location.href = "./dashboard.html";
  } catch (err) {
    showNote(note, err.message, " ");
  }
}

async function login(event) {
  event.preventDefault();
  const note = $("#auth-note");
  try {
    const data = await api("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({
        email: $("#login-email").value,
        password: $("#login-password").value,
      }),
    });
    setToken(data.token);
    location.href = "./dashboard.html";
  } catch (err) {
    showNote(note, err.message, " ");
  }
}

async function magic(event) {
  event.preventDefault();
  const note = $("#magic-note");
  try {
    const data = await api("/api/auth/magic-link", {
      method: "POST",
      body: JSON.stringify({ email: $("#magic-email").value }),
    });
    if (data.dev_url) {
      showNote(note, "Local magic link ready — opening it now.", "ok");
      location.href = data.dev_url;
      return;
    }
    showNote(note, "If that inbox is registered, a sign-in link is on its way.", "ok");
  } catch (err) {
    showNote(note, err.message, " ");
  }
}

document.addEventListener("DOMContentLoaded", () => {
  $("#register-form")?.addEventListener("submit", register);
  $("#login-form")?.addEventListener("submit", login);
  $("#magic-form")?.addEventListener("submit", magic);
});
