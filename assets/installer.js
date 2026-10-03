// Starts the LapSimPro-Setup.zip download for buttons marked data-installer-download.
//
// The installer is about 280 MB, over the 100 MB per-file limit of the static host that
// serves lapsimpro.com, so the zip is a release asset on the same account. Pages link to
// https://lapsimpro.com/releases/ and this script hands the browser the file. Change the
// release here only; no HTML page carries the file host URL.
export const INSTALLER_URL =
  "https://github.com/immortalesrevinu-art/lapsimpro-website/releases/download/v0.1.0/LapSimPro-Setup.zip";

export function startInstallerDownload() {
  window.location.assign(INSTALLER_URL);
}

function wire() {
  document.querySelectorAll("[data-installer-download]").forEach((el) => {
    el.addEventListener("click", (event) => {
      event.preventDefault();
      startInstallerDownload();
    });
  });
  if (document.querySelector("[data-installer-autostart]")) {
    window.setTimeout(startInstallerDownload, 600);
  }
}

if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", wire);
else wire();
