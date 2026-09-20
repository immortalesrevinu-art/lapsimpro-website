import { api, currentUser } from "./account-nav.js";

async function boot() {
  const params = new URLSearchParams(location.search);
  const sessionId = params.get("session_id");
  const user = await currentUser();
  const banner = document.querySelector("[data-checkout-complete]");
  const gate = document.querySelector("[data-download-gate]");
  const links = document.querySelectorAll("[data-download-link]");

  if (sessionId && user) {
    try {
      await api("/api/billing/claim", { method: "POST", body: JSON.stringify({ session_id: sessionId }) });
      if (banner) banner.hidden = false;
    } catch {
      /* Payment Links still land here even if claim needs a later refresh */
    }
  } else if (sessionId && banner) {
    banner.hidden = false;
  }

  if (!user) {
    links.forEach((a) => {
      a.setAttribute("href", "./login.html");
      a.textContent = "Log in to download";
    });
    if (gate) {
      gate.hidden = false;
      gate.textContent = "Log in, then we check your Stripe subscription before handing over the installer.";
    }
    return;
  }

  try {
    const download = await api("/api/download");
    links.forEach((a) => {
      a.setAttribute("href", download.url);
    });
    if (gate) gate.hidden = true;
  } catch (err) {
    links.forEach((a) => {
      a.setAttribute("href", "./pricing.html");
      a.textContent = "Subscribe to download";
    });
    if (gate) {
      gate.hidden = false;
      gate.textContent = err.message || "Active subscription required.";
    }
  }
}

document.addEventListener("DOMContentLoaded", () => {
  boot().catch(() => {});
});
