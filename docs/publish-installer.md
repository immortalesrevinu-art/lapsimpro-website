# Publish the Windows installer

Paying subscribers download `LapSimPro-Setup.zip` (~282MB) after `GET /api/download` confirms an active Stripe subscription. The durable copy is a **GitHub Release asset on this repo**, not an Actions artifact and not a file in the GitHub Pages site.

Current known-good asset (do not delete it):

```text
https://github.com/immortalesrevinu-art/lapsimpro-website/releases/download/v0.1.0/LapSimPro-Setup.zip
```

Unauthenticated `GET` returns 302 to the release CDN, then 200. The Pages download page (`download.html`) only links there after the API entitlement check.

## Why the old publish path failed

This website repo has no Windows build. The overlay build lives in the private repo `immortalesrevinu-art/iracing-coach-overlay` (leave that repo private). A prior Windows release workflow uploaded `LapSimPro-Setup.zip` with `actions/upload-artifact`.

That fails for two separate limits:

| Path | What happens to a ~282MB zip |
| --- | --- |
| `actions/upload-artifact` | Counts against the account's Actions storage quota (500MB on Free, 1–2GB on Pro/Team), shared by every repo under the account. Default retention keeps each upload for days, so one or two installer builds exhaust the quota and later uploads — including other workflows — fail. |
| GitHub Pages | Will not publish a site file over 100MB. Committing the zip, or letting the Pages deploy include it, fails the Pages build. Pages artifacts are also Actions storage. |

Release assets are a different store. A single asset may be up to 2GB, and uploading one does not consume Actions artifact retention. Replacing `LapSimPro-Setup.zip` on a tag updates that one filename. It does not delete other assets on the release.

This repo's current Actions artifacts are only the small `github-pages` bundles (~1.2MB). They are not the installer. The quota failure is from installer artifacts retained elsewhere on the same GitHub account (typically the private overlay repo).

## Publish the next zip from your machine

Build the installer in the private overlay repo, then from a checkout of **this** repo:

```bash
# Requires gh auth with contents:write on immortalesrevinu-art/lapsimpro-website.
# REPLACE_SAME_NAME=1 replaces LapSimPro-Setup.zip on that tag only.
REPLACE_SAME_NAME=1 scripts/publish-installer.sh /path/to/LapSimPro-Setup.zip v0.1.0
```

Leave `REPLACE_SAME_NAME` unset when the asset name is not already on the tag. The script refuses to upload unless the file is a zip between 1MB and 2GB. It never calls `actions/upload-artifact` and never commits the zip.

To ship a new version instead of replacing 0.1.0:

```bash
gh release create v0.1.1 \
  --repo immortalesrevinu-art/lapsimpro-website \
  --title "LapSimPro 0.1.1" \
  --notes "Windows installer."
scripts/publish-installer.sh /path/to/LapSimPro-Setup.zip v0.1.1
```

Then point subscribers at the new asset:

1. Set `LAPSIMPRO_DOWNLOAD_URL` to `https://github.com/immortalesrevinu-art/lapsimpro-website/releases/download/v0.1.1/LapSimPro-Setup.zip` (Render and `.env`).
2. Or change `DEFAULT_DOWNLOAD_URL` in `server/config.py` and deploy the API.

`releases/index.html` and the `/releases/LapSimPro-Setup.zip` 404 recovery in `404.html` must keep pointing at the same public asset. Do not commit the zip to make that Pages path succeed.

Until that URL changes, the API keeps serving the `v0.1.0` asset.

## Publish from Actions without artifact storage

After this workflow is on `main`, run **Publish Windows installer** (`workflow_dispatch`) in the Actions tab.

| Input | Meaning |
| --- | --- |
| `tag` | Release tag. Default `v0.1.0`. |
| `source_url` | `https://` URL of the zip. The runner downloads it to disk and uploads it with `gh release upload`. |
| `replace_same_name` | `false` by default. Set `true` only to replace `LapSimPro-Setup.zip` on that tag. Other assets stay. |
| `create_release` | `false` by default. Set `true` to create a missing tag. It will not recreate `v0.1.0`. |

The workflow rejects Actions artifact URLs (`/actions/artifacts/`) so a quota-limited artifact is not the source. It does not upload a new Actions artifact.

`workflow_dispatch` cannot attach a file from your laptop. Use the script for a local zip. Use the workflow when the zip is already fetchable over HTTPS.

### Overlay repo snippet

If the private Windows workflow still ends in `actions/upload-artifact`, replace that step with a release upload. Do not make the overlay repo public. Create a fine-grained PAT that can write contents on **this** repo only, and store it as `LAPSIPRO_RELEASE_TOKEN` in the overlay repo.

```yaml
- name: Publish installer to the public website release
  env:
    GH_TOKEN: ${{ secrets.LAPSIPRO_RELEASE_TOKEN }}
  run: |
    gh release upload v0.1.0 path/to/LapSimPro-Setup.zip \
      --repo immortalesrevinu-art/lapsimpro-website \
      --clobber
```

`--clobber` replaces the same filename. It does not delete the release or any other asset. Drop `--clobber` when you want the upload to fail instead of replacing a file that is already there.

## Clear the quota (manual)

This change stops new installer uploads from filling Actions storage. It does not delete artifacts already retained by GitHub.

1. Open the GitHub account or org that owns both repos → **Settings → Billing and licensing → Actions** (or **Settings → Actions → General**) and check **Storage**.
2. On each repo that built the installer, open **Settings → Actions → Artifacts** (or the Actions run page) and delete old `LapSimPro-Setup` / Windows artifacts.
3. Do **not** delete the `v0.1.0` Release asset `LapSimPro-Setup.zip`. Release assets are not the quota that failed.
4. The small `github-pages` artifacts on this website repo can stay. Deleting them does not remove the published site, but it also does not free enough space if the installer artifacts are still retained on the overlay repo.

If Render was given `LAPSIMPRO_DOWNLOAD_URL` pointing at `iracing-coach-overlay`, change it to the public website release URL above or remove the variable so the API default applies. The Render blueprint in `render.yaml` now sets the public URL.
