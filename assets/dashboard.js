import { api, currentUser } from "./account-nav.js";

const $ = (sel) => document.querySelector(sel);

function fmtLap(s) {
  if (s == null) return "—";
  const n = Number(s);
  const m = Math.floor(n / 60);
  const rem = (n - m * 60).toFixed(3).padStart(6, "0");
  return `${m}:${rem}`;
}

function render(data) {
  $("#points-total").textContent = String(data.points_total ?? 0);
  const plan = data.entitlement?.plan || "none";
  const active = Boolean(data.entitlement?.active);
  $("#plan-pill").textContent = active ? `${plan} · active` : "no subscription";
  $("#plan-pill").classList.toggle("warn", !active);
  $("#who").textContent = data.user?.email || "";

  const sessions = data.sessions || [];
  const body = $("#session-body");
  const empty = $("#session-empty");
  if (!sessions.length) {
    body.innerHTML = "";
    empty.hidden = false;
  } else {
    empty.hidden = true;
    body.innerHTML = sessions
      .map(
        (row) => `
      <tr>
        <td>${row.track}</td>
        <td>${row.car}</td>
        <td class="mono">${fmtLap(row.best_lap_s)}</td>
        <td>${row.reference_source || "—"}</td>
      </tr>`
      )
      .join("");
  }

  const bests = data.best_laps || [];
  $("#best-body").innerHTML = bests.length
    ? bests
        .map(
          (row) => `
      <tr>
        <td>${row.track}</td>
        <td>${row.car}</td>
        <td class="mono">${fmtLap(row.lap_time_s)}</td>
      </tr>`
        )
        .join("")
    : `<tr><td colspan="3" class="empty">No personal bests yet.</td></tr>`;

  const cards = data.coaching || [];
  $("#coach-list").innerHTML = cards.length
    ? cards
        .map(
          (card) => `
      <article class="coach-card" data-tone="${card.tone || "cyan"}">
        <h3>${card.title}</h3>
        <p>${card.body}</p>
      </article>`
        )
        .join("")
    : `<p class="lede">No coaching cards yet. Sync a bound catalog lap from the overlay.</p>`;

  const events = data.point_events || [];
  $("#event-list").innerHTML = events.length
    ? events
        .map(
          (ev) => `
      <div class="event-row">
        <p>${ev.detail}</p>
        <strong>+${ev.points}</strong>
      </div>`
        )
        .join("")
    : `<p class="lede">Points land here when you hit a reference brake window or improve a lap.</p>`;
}

function paintHud(hud) {
  if (!hud) return;
  const val = $("#hud-points");
  const toast = $("#hud-toast");
  if (val) val.textContent = String(hud.points_total ?? 0);
  if (toast) {
    toast.hidden = !hud.toast;
    toast.textContent = hud.toast || "";
  }
}

async function load() {
  const user = await currentUser();
  if (!user) {
    location.href = "./login.html";
    return;
  }
  const data = await api("/api/dashboard");
  render(data);
}

async function replay() {
  const note = $("#dash-note");
  note.hidden = true;
  try {
    const result = await api("/api/demo/session", { method: "POST", body: "{}" });
    paintHud(result.hud);
    await load();
    note.hidden = false;
    note.className = "note ok";
    note.textContent = `Overlay replay synced. +${result.points_awarded} points from brake windows and a faster lap.`;
  } catch (err) {
    note.hidden = false;
    note.className = "note";
    note.textContent = err.message;
  }
}

document.addEventListener("DOMContentLoaded", () => {
  load().catch((err) => {
    const note = $("#dash-note");
    note.hidden = false;
    note.textContent = err.message;
  });
  $("#replay")?.addEventListener("click", replay);
});
