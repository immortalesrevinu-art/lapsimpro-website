import { api, currentUser, setToken } from "./account-nav.js";

const $ = (sel) => document.querySelector(sel);

async function boot() {
  const user = await currentUser();
  if (!user) {
    location.href = "./login.html";
    return;
  }
  $("#email").textContent = user.email;
  const ent = user.entitlement || {};
  $("#plan").textContent = ent.active ? `${ent.plan || "starter"} · ${ent.reason}` : "No active subscription";
  $("#gate").hidden = Boolean(ent.active);
  $("#download-wrap").hidden = !ent.active;
}

async function mintDevice() {
  const data = await api("/api/devices", { method: "POST", body: JSON.stringify({ name: "overlay" }) });
  $("#device-token").textContent = data.token;
  $("#device-box").hidden = false;
}

async function logout() {
  try {
    await api("/api/auth/logout", { method: "POST" });
  } finally {
    setToken("");
    location.href = "./login.html";
  }
}

async function claim() {
  const params = new URLSearchParams(location.search);
  const sessionId = params.get("session_id");
  if (!sessionId) return;
  try {
    await api("/api/billing/claim", { method: "POST", body: JSON.stringify({ session_id: sessionId }) });
    await boot();
  } catch {
    /* claim is best-effort on account page */
  }
}

document.addEventListener("DOMContentLoaded", () => {
  boot().then(claim);
  $("#mint-device")?.addEventListener("click", (event) => {
    event.preventDefault();
    mintDevice().catch((err) => {
      $("#device-note").hidden = false;
      $("#device-note").textContent = err.message;
    });
  });
  $("#logout")?.addEventListener("click", logout);
});
