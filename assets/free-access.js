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
  downloadWrap.hidden = false;
}

async function unlock(raw, { input, status, downloadWrap, submitBtn }) {
  submitBtn.disabled = true;
  try {
    const ok = await accessCodeMatches(raw);
    if (!ok) {
      setStatus(status, REJECTED, "bad");
      return;
    }
    rememberUnlock();
    setStatus(status, ACCEPTED, "ok");
    showDownload(downloadWrap);
    input.value = "";
    startInstallerDownload();
  } catch {
    setStatus(status, REJECTED, "bad");
  } finally {
    submitBtn.disabled = false;
  }
}

function boot() {
  const root = document.querySelector("[data-free-access]");
  if (!root) return;
  const form = root.querySelector("[data-free-access-form]");
  const input = root.querySelector("[data-free-access-input]");
  const status = root.querySelector("[data-free-access-status]");
  const downloadWrap = root.querySelector("[data-free-access-download]");
  const submitBtn = form.querySelector("button[type=submit]");
  const ui = { input, status, downloadWrap, submitBtn };

  if (readUnlocked()) showDownload(downloadWrap);

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    unlock(input.value, ui);
  });

  const params = new URLSearchParams(location.search);
  if (!params.has("code")) return;
  const fromUrl = params.get("code") ?? "";
  input.value = fromUrl;
  params.delete("code");
  const query = params.toString();
  history.replaceState(null, "", `${location.pathname}${query ? `?${query}` : ""}${location.hash}`);
  unlock(fromUrl, ui);
}

if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
else boot();
