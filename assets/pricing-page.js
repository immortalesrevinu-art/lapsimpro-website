import { api, currentUser } from "./account-nav.js";

async function boot() {
  const user = await currentUser();
  if (!user) return;
  let cfg;
  try {
    cfg = await api("/api/config");
  } catch {
    return;
  }
  if (!cfg.stripe_configured) return;
  document.querySelectorAll("[data-plan]").forEach((btn) => {
    btn.addEventListener("click", async (event) => {
      event.preventDefault();
      try {
        const data = await api("/api/billing/checkout", {
          method: "POST",
          body: JSON.stringify({ plan: btn.getAttribute("data-plan") }),
        });
        if (data.url) location.href = data.url;
      } catch (err) {
        const note = document.querySelector("[data-pricing-note]");
        if (note) {
          note.hidden = false;
          note.textContent = err.message;
        }
      }
    });
  });
}

document.addEventListener("DOMContentLoaded", () => {
  boot();
});
