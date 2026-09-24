#!/usr/bin/env bash
# Attach LapSimPro-Setup.zip to a GitHub Release on the public website repo.
#
# This uploads a Release asset. It does not use actions/upload-artifact, and it
# does not commit the zip into the Pages site.
#
# Usage:
#   scripts/publish-installer.sh /path/to/LapSimPro-Setup.zip [tag]
#
# Environment:
#   LAPSIPRO_RELEASE_REPO   default: immortalesrevinu-art/lapsimpro-website
#   REPLACE_SAME_NAME=1     replace LapSimPro-Setup.zip on that tag only
#
# Requires: gh (authenticated with contents:write), python3.
set -euo pipefail

FILE="${1:-}"
TAG="${2:-v0.1.0}"
REPO="${LAPSIPRO_RELEASE_REPO:-immortalesrevinu-art/lapsimpro-website}"
ASSET_NAME="LapSimPro-Setup.zip"

if [[ -z "$FILE" || ! -f "$FILE" ]]; then
  echo "usage: scripts/publish-installer.sh <LapSimPro-Setup.zip> [tag]" >&2
  exit 1
fi

if ! printf '%s' "$TAG" | grep -Eq '^v[0-9][0-9A-Za-z._+-]*$'; then
  echo "tag must look like v0.1.0 (got: $TAG)" >&2
  exit 1
fi

python3 - "$FILE" <<'PY'
import sys
import zipfile

path = sys.argv[1]
size = __import__("os").path.getsize(path)
if not zipfile.is_zipfile(path):
    raise SystemExit(f"{path} is not a zip file")
if size < 1_000_000:
    raise SystemExit(f"{path} is {size} bytes; refusing a file under 1MB")
if size > 2_000_000_000:
    raise SystemExit(f"{path} is {size} bytes; GitHub Release assets must be under 2GB")
print(f"installer ok: {size} bytes")
PY

if ! gh release view "$TAG" --repo "$REPO" >/dev/null 2>&1; then
  echo "Release $TAG does not exist on $REPO." >&2
  echo "Create it first, then re-run this script:" >&2
  echo "  gh release create $TAG --repo $REPO --title \"LapSimPro ${TAG#v}\" --notes \"Windows installer.\"" >&2
  exit 1
fi

upload=(gh release upload "$TAG" "${FILE}#${ASSET_NAME}" --repo "$REPO")
if [[ "${REPLACE_SAME_NAME:-0}" == "1" ]]; then
  upload+=(--clobber)
  echo "Replacing ${ASSET_NAME} on ${TAG}. Other release assets are left in place."
else
  echo "Uploading ${ASSET_NAME} to ${TAG}. If that filename already exists, the upload fails and nothing is deleted."
fi

"${upload[@]}"
echo "https://github.com/${REPO}/releases/download/${TAG}/${ASSET_NAME}"
