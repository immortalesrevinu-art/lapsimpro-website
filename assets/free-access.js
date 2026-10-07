import { accessCodeMatches } from "./access-codes.js";
import { startInstallerDownload } from "./installer.js";

const STORAGE_KEY = "lapsimpro.freeAccess";
const ACCEPTED = "Code accepted - your download is starting";
const REJECTED = "That code isn't valid";

function readUnlocked() {
  try {
    return localStorage.getItem(STORAGE_KEY) === "1";
  } catch {
    return false;
  }
}

function rememberUnlock() {
  try {
    localStorage.setItem(STORAGE_KEY, "1");
  } catch {
    /* private browsing can block storage; the download still starts */
  }
}

function setStatus(status, text, state) {
  status.textContent = text;
  if (state) status.dataset.state = state;
  else delete status.dataset.state;
}

function showDownload(downloadWrap) {
  if (!downloadWrap) return;
  downloadWrap.hidden = false;
  downloadWrap.querySelectorAll("a, button").forEach((el) => {
    if (el.dataset.wired === "1") return;
    el.dataset.wired = "1";
    el.addEventListener("click", (event) => {
      event.preventDefault();
      startInstallerDownload();
    });
  });
}

async function unlock(raw, { input, status, downloadWrap, submitBtn }) {
  submitBtn.disabled = true;
  try {
    const ok = await accessCodeMatches(raw);
    if (!ok) {
      setStatus(status, REJECTED, "bad");
      return false;
    }
    rememberUnlock();
    setStatus(status, ACCEPTED, "ok");
    showDownload(downloadWrap);
    input.value = "";
    startInstallerDownload();
    return true;
  } catch {
    setStatus(status, REJECTED, "bad");
    return false;
  } finally {
    submitBtn.disabled = false;
  }
}

export function bootFreeAccess() {
  const root = document.querySelector("[data-free-access]");
  if (!root) return;
  const form = root.querySelector("[data-free-access-form]");
  const input = root.querySelector("[data-free-access-input]");
  const status = root.querySelector("[data-free-access-status]");
  const downloadWrap = root.querySelector("[data-free-access-download]");
  const submitBtn = form.querySelector("button[type=submit]");
  const ui = { input, status, downloadWrap, submitBtn };
  const resumeDownload = root.hasAttribute("data-free-access-resume");

  if (readUnlocked()) showDownload(downloadWrap);

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    return unlock(input.value, ui);
  });

  const params = new URLSearchParams(location.search);
  if (params.has("code")) {
    const fromUrl = params.get("code") ?? "";
    input.value = fromUrl;
    params.delete("code");
    const query = params.toString();
    history.replaceState(null, "", `${location.pathname}${query ? `?${query}` : ""}${location.hash}`);
    return unlock(fromUrl, ui).then((ok) => {
      if (!ok && readUnlocked() && resumeDownload) startInstallerDownload();
    });
  }

  if (readUnlocked() && resumeDownload) {
    setStatus(status, ACCEPTED, "ok");
    startInstallerDownload();
  }
}

if (!globalThis.__LSP_SKIP_FREE_ACCESS_BOOT) {
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", bootFreeAccess);
  else bootFreeAccess();
}
