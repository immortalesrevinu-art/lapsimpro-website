// LapSimPro-Setup.zip is about 280 MB, over the per-file limit of the static host.
// The URL stays in this module. Call startInstallerDownload only after an access-code unlock.
export const INSTALLER_URL =
  "https://github.com/immortalesrevinu-art/lapsimpro-website/releases/download/v0.1.0/LapSimPro-Setup.zip";

export function startInstallerDownload() {
  window.location.assign(INSTALLER_URL);
}
