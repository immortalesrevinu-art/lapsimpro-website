# LapSimPro (lapsimpro.com)

Marketing site plus a local **account / training API**. Drivers log in, the overlay scores brake-marker hits and faster laps, and the dashboard shows their data with “how to get faster” cards.

The public site remains static HTML (GitHub Pages). The API is Python so it matches the overlay stack. There was no existing auth library on this site — this repo adds a small email + password (or magic-link) service rather than Clerk/Auth.js.

The overlay application repo is private and was not checked out in this workspace. Live scoring + upload live in `overlay/lapsimpro_sync/` (copy that package into [iracing-coach-overlay](https://github.com/immortalesrevinu-art/iracing-coach-overlay)). See `overlay/INTEGRATE.md`.

## Overlay API contract (merged overlay #36)

The overlay turns off `LAPSIPRO_API_MOCK` when these routes exist. Base URL can be `http://127.0.0.1:8787` or `http://127.0.0.1:8787/api/v1`.

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/api/v1/auth/device` | Exchange a website device code (`python -m iracing_coach login --device-code`) |
| POST | `/api/v1/auth/magic` | Exchange a magic token (`--magic-token`) or request a link with `{email}` |
| GET | `/me` or `/api/v1/me` | Account + entitlement + points |
| POST | `/sessions` or `/api/v1/sessions` | `lapsimpro.session.v1` upsert by `client_session_id` |
| GET/PUT | `/pbs` or `/api/v1/pbs` | Personal bests per track+car |

Overlay scoring (also re-checked on the server when samples are present): **+10** brake-hit within **12 m or 0.35 s** of a bound REF marker; **+50** personal best. **POST /sessions and /pbs require a signed-in overlay token, not a Stripe subscription.** Download still requires an active Starter/Pro/Elite entitlement.

## Local how-to

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# leave LAPSIMPRO_DEV_ENTITLEMENT=1 for local scoring without a live Stripe customer
python -m server
```

Open http://127.0.0.1:8787/login.html

1. Create an account (email + password, 8+ characters).
2. Open **Dashboard** → **Replay overlay session**. That drives the same `TrainingAid` engine the overlay uses: catalog_sample Laguna / Huracán, two laps, brake windows + a personal-best then a faster lap.
3. Coaching cards and point events appear on the dashboard. The HUD preview shows the points chip / toast.

Overlay device login (same account):

```bash
cd overlay
PYTHONPATH=. python -m lapsimpro_sync login --api http://127.0.0.1:8787 --email you@example.com
PYTHONPATH=. python -m lapsimpro_sync replay
```

The device token is stored at `~/.lapsimpro/session.json` with `0600` permissions. You can also mint a token on **Account**.

```bash
pytest -q
```

## Stripe entitlement check

Download (`GET /api/download`) and cloud sync (`POST /api/overlay/sync`) require an **active subscription**.

When `STRIPE_SECRET_KEY` is set and `LAPSIMPRO_DEV_ENTITLEMENT` is unset/0, the API:

1. Links the logged-in user to a Stripe Customer (`customer_email` / Payment Link claim / webhook).
2. Lists that customer’s subscriptions (`status` in `active`, `trialing`, `past_due`).
3. Maps the product to Starter / Pro / Elite via product `metadata.tier` (already `starter` / `pro` / `elite` on the live catalog).
4. Returns the installer URL only when that check passes.

Logged-in checkout uses Stripe Checkout Sessions (`mode=subscription`) with `client_reference_id=user_id` and `integration_identifier=lapsimpro_dash_********`. Existing Payment Links stay as the guest path; after return, `/download.html?session_id=…` calls `POST /api/billing/claim`.

Live prices (do not commit secret keys):

| Plan    | Product              | Price id                     | Amount   |
| ------- | -------------------- | ---------------------------- | -------- |
| Starter | LapSimPro Starter    | `price_1UGOsMPVazkD4GpuxvLFjoCJ` | $5.99/mo |
| Pro     | LapSimPro Pro        | `price_1UGOsNPVazkD4GpuP7jWZuax` | $9.99/mo |
| Elite   | LapSimPro Elite      | `price_1UGOsMPVazkD4GpuqAtr8Muv` | $18.99/mo |

Webhook: `POST /api/webhooks/stripe` with `STRIPE_WEBHOOK_SECRET`. Events: `checkout.session.completed`, `customer.subscription.*`.

If you charge US or EU customers, consider enabling [Stripe Tax for recurring payments](https://docs.stripe.com/billing/taxes/collect-taxes.md). This API does **not** set `automatic_tax` — Stripe collects no tax until you have an active registration.

Use a [restricted API key](https://docs.stripe.com/keys/restricted-api-keys.md) (`rk_`) in production.

## Honesty rules (overlay + server)

- Points and coaching stay off unless track + car bind to a real catalog / Garage 61 / fastest reference.
- No invented G61 pedal traces. Local replay is labeled `catalog_sample`.
- Overlay HUD points chip is display-only and must not steal focus or change borderless click-through.

## Env vars

See `.env.example`. Nothing secret belongs in git.

| Variable | Purpose |
| --- | --- |
| `LAPSIMPRO_SECRET` | Signs session + device tokens |
| `LAPSIMPRO_DB` | SQLite path |
| `LAPSIMPRO_PUBLIC_URL` | Redirects and magic-link host |
| `LAPSIMPRO_DEV_ENTITLEMENT` | Local bypass of Stripe (Starter) |
| `LAPSIMPRO_DOWNLOAD_URL` | Installer returned after entitlement |
| `STRIPE_SECRET_KEY` | Restricted key for customer / subscription reads |
| `STRIPE_WEBHOOK_SECRET` | Webhook signature |
| `STRIPE_PRICE_*` | Checkout line items |
| `BRAKE_HIT_WINDOW_M` / `BRAKE_CLOSE_WINDOW_M` | Marker timing/distance tolerance |
| `BRAKE_HIT_POINTS` / `LAP_PB_POINTS` / `LAP_IMPROVE_POINTS` | Training aid scoring |

GitHub Pages can keep serving the static marketing pages. Point `window.LAPSIMPRO_API` at a hosted API (Fly/Render/etc.) when you deploy beyond localhost.
