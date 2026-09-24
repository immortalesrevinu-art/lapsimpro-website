# Production API

GitHub Pages serves the static site at [lapsimpro.com](https://lapsimpro.com). Pages cannot serve `/api/...`, so the FastAPI process (`python -m server`) needs a public HTTPS host.

**Chosen host:** Render free web service `lapsimpro-api`. A Render account for `theuniversecontractor@gmail.com` is already verified. New Render workspaces require a card on file even for the **Free** ($0) instance — that is the only remaining click. Fly, Railway, Alwaysdata, and Hugging Face either require a card or blocked automated signup.

| Role | URL |
| --- | --- |
| Marketing / login / dashboard | `https://lapsimpro.com` (GitHub Pages, `main`) |
| Account / training API | `https://lapsimpro-api.onrender.com` (after the Free service is deployed) |
| Preferred custom API host | `https://api.lapsimpro.com` (CNAME below; optional) |

The Pages frontend reads the API host from one file: [`assets/api-config.js`](../assets/api-config.js) (`LAPSIMPRO_API_BASE`). After a custom domain is live, change that value and set `LAPSIMPRO_API_URL` on the host to match.

Overlay (repo `iracing-coach-overlay`):

```bash
export LAPSIPRO_API_URL=https://lapsimpro-api.onrender.com
export LAPSIPRO_API_MOCK=0
```

`LAPSIPRO_API_URL` and `LAPSIMPRO_API_URL` are both accepted by `python -m lapsimpro_sync`.

## Finish deploy (one card-on-file click)

1. Open [dashboard.render.com](https://dashboard.render.com) and sign in as `theuniversecontractor@gmail.com` (use **Forgot password** if needed).
2. Add a payment method when Render asks. The Free instance is $0/month; the card is only for abuse checks.
3. Deploy this repo as a Free Python web service:
   - [Deploy to Render](https://render.com/deploy?repo=https://github.com/immortalesrevinu-art/lapsimpro-website), or Dashboard → **New** → **Blueprint** / **Web Service** → public git `https://github.com/immortalesrevinu-art/lapsimpro-website`
   - Branch: `main` (after this PR merges) or `cursor/deploy-training-api-d58d` before merge
   - Runtime: Python
   - Build: `pip install -r requirements.txt`
   - Start: `python -m server`
   - Health check: `/api/health`
   - Instance: **Free**

`Dockerfile` (uid 1000, `PORT`/`0.0.0.0`) and `Procfile` also work on Fly, Railway, or a Hugging Face Docker Space if you later move hosts. Stripe Projects can provision the same Render `web-service` (free instance) after `stripe login` + `stripe projects init` on your machine.

## Environment

Set these on the Render service (Blueprint already seeds them). **Never commit secret values.**

| Variable | Production value | Notes |
| --- | --- | --- |
| `LAPSIMPRO_SECRET` | generate a long random string | Render Blueprint uses `generateValue: true` |
| `LAPSIMPRO_PUBLIC_URL` | `https://lapsimpro.com` | Stripe redirects + magic-link landing |
| `LAPSIMPRO_API_URL` | `https://lapsimpro-api.onrender.com` | Magic-link consume URL (API host) |
| `LAPSIMPRO_CORS_ORIGINS` | `https://lapsimpro.com,https://www.lapsimpro.com,http://lapsimpro.com,http://www.lapsimpro.com` | Include `http://` until GitHub finishes the Pages TLS cert |
| `LAPSIMPRO_DEV_ENTITLEMENT` | `1` for bring-up | Set `0` when live Stripe keys are installed |
| `LAPSIMPRO_DOWNLOAD_URL` | `https://github.com/immortalesrevinu-art/lapsimpro-website/releases/download/v0.1.0/LapSimPro-Setup.zip` | Public Release asset on `lapsimpro-website` tag `v0.1.0`. Replace any previously saved private overlay release URL on the host. `GET /api/download` returns this only after an active Starter/Pro/Elite entitlement. Next zip: [`publish-installer.md`](publish-installer.md). |
| `LAPSIMPRO_HOST` | `0.0.0.0` | Required in the container |
| `STRIPE_SECRET_KEY` | `rk_live_...` restricted key | Placeholder empty on first deploy |
| `STRIPE_WEBHOOK_SECRET` | `whsec_...` | Endpoint: `https://lapsimpro-api.onrender.com/api/webhooks/stripe` |
| `STRIPE_PRICE_STARTER` / `PRO` / `ELITE` | existing live price ids | Already defaulted in code |

Stripe live account `acct_1UGOgnPVazkD4Gpu` is connected in Cursor, but secret keys cannot be read from the Dashboard/MCP. Paste a [restricted key](https://docs.stripe.com/keys/restricted-api-keys.md) into Render when entitlements should be real, then set `LAPSIMPRO_DEV_ENTITLEMENT=0`.

Free Render disks are ephemeral. Account rows live in SQLite under `data/lapsimpro.db` and reset if the instance is recycled. For durable accounts, attach a disk and set `LAPSIMPRO_DB=/var/data/lapsimpro.db`, or move to Postgres later.

## GoDaddy DNS (lapsimpro.com)

Nameservers today: `ns43.domaincontrol.com` / `ns44.domaincontrol.com` (GoDaddy). GitHub does **not** host extra records for this domain.

### Already in place (GitHub Pages)

| Type | Name | Value | TTL |
| --- | --- | --- | --- |
| A | `@` | `185.199.108.153` | 600 |
| A | `@` | `185.199.109.153` | 600 |
| A | `@` | `185.199.110.153` | 600 |
| A | `@` | `185.199.111.153` | 600 |
| CNAME | `www` | `immortalesrevinu-art.github.io` | 600 |

Repo Pages setting: custom domain `lapsimpro.com`. In GitHub → Settings → Pages, wait until the TLS certificate is issued, then tick **Enforce HTTPS**. The apex currently presents `*.github.io` on 443; browsers that open `https://lapsimpro.com` may warn until that cert exists. `http://lapsimpro.com` already serves login/dashboard.

### Add for the API (after Render is live)

| Type | Name | Value | TTL |
| --- | --- | --- | --- |
| CNAME | `api` | `lapsimpro-api.onrender.com` | 600 |

Then in Render → lapsimpro-api → **Custom Domains** → add `api.lapsimpro.com`. Render will ask you to add a verify CNAME if they issue one (copy it exactly). After the cert is ready:

1. Set `LAPSIMPRO_API_URL=https://api.lapsimpro.com` on the service.
2. Change `LAPSIMPRO_API_BASE` in `assets/api-config.js` to `https://api.lapsimpro.com`.
3. Point the Stripe webhook at `https://api.lapsimpro.com/api/webhooks/stripe`.

Do **not** add an `api` record in GitHub Pages; Pages only maps the apex/`www` site.

## Installer file

`LapSimPro-Setup.zip` (~270–282 MB) is a **public GitHub Release asset**, not a file in this git repo and not a GitHub Pages object. Pages rejects files over 100 MB.

| URL | Behavior |
| --- | --- |
| `https://github.com/immortalesrevinu-art/lapsimpro-website/releases/download/v0.1.0/LapSimPro-Setup.zip` | The file. This is `LAPSIMPRO_DOWNLOAD_URL`. |
| `https://lapsimpro.com/releases/` | Static page (`releases/index.html`) with a meta refresh to that asset. |
| `https://lapsimpro.com/releases/LapSimPro-Setup.zip` | Pages 404. `404.html` explains that and links to the Release asset. Do not commit the zip to satisfy this path. |

Stripe gating is unchanged: anonymous and unpaid `GET /api/download` stays 401/402. The URL itself is public so a subscriber's browser can fetch it without a GitHub login.

To attach a newer zip, use `scripts/publish-installer.sh` or the **Publish Windows installer** workflow. Those upload a Release asset and do not commit the file or store it as an Actions artifact. Steps: [`publish-installer.md`](publish-installer.md). Do not remove `releases/index.html` or the 404 recovery for `/releases/LapSimPro-Setup.zip`.

## Smoke test

```bash
curl -sS https://lapsimpro-api.onrender.com/api/health
curl -sS https://lapsimpro-api.onrender.com/api/v1
```

Expect `{"ok": true, ...}` and the `lapsimpro.session.v1` contract listing. Free instances sleep after ~15 minutes; the first request can take about a minute.

Then open `http://lapsimpro.com/login.html` (or `https://` once Pages TLS is valid), create an account, and confirm the dashboard loads.

## Fly.io / Railway

`Dockerfile`, `Procfile`, and `fly.toml` are ready if you later add a paid/card host. Fly no longer has a free allowance for new accounts. Railway requires a token + typically a card after credits. Prefer Render until then.
