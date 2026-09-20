# Drop-in for iracing-coach-overlay

This package is the overlay half of the logged-in training aid. Copy `overlay/lapsimpro_sync/` into the overlay repo (for example `src/lapsimpro_sync/` or next to `iracing_coach`).

The overlay repo is private and was not in this Cloud Agent workspace, so the integration lives here until it is vendored.

## Honesty (do not skip)

- Call `set_reference` only with a **real catalog / Garage 61 / fastest-bound** lap.
- Never invent G61 pedal traces. If bind fails, show the existing `NO REFERENCE FOR THIS TRACK` copy and skip points.
- `bind_gates(track, car, ref_track, ref_car, source)` must pass before scoring.

## Live hook

```python
from lapsimpro_sync import TrainingAid, AccountClient

aid = TrainingAid()
# after iRacing session identity + catalog bind:
aid.bind_session(track_name, car_name)
aid.set_reference(ref_track, ref_car, source="catalog", markers=markers, samples=ref_samples)

# each telemetry tick (do not steal focus):
aid.tick(dist_m, speed, brake, throttle, on_track=not in_pits)
hud_bits = aid.hud.snapshot()
# draw a small "PTS 120" label + optional toast; ignore if toast is None

# on lap complete:
aid.end_lap(lap_time_s, valid=valid_lap)

# when online, after the run:
AccountClient.from_saved().sync(aid.flush_payload())
```

## Device login

Website Account page mints a device code. Overlay (merged #36):

```text
python -m iracing_coach login --device-code LSP-XXXXXX
python -m iracing_coach login --magic-token <token>
```

This package also still supports `python -m lapsimpro_sync login`. The token is stored at `~/.lapsimpro/session.json` with `0600` permissions.

Production API (after deploy):

```bash
export LAPSIPRO_API_URL=https://lapsimpro-api.onrender.com
export LAPSIPRO_API_MOCK=0
```

`python -m lapsimpro_sync` also reads `LAPSIMPRO_API_URL`. See `docs/production.md`.

Contract the overlay expects (so `LAPSIPRO_API_MOCK` can stay off):

- `POST /api/v1/auth/device` `{ "device_code": "LSP-XXXXXX" }`
- `POST /api/v1/auth/magic` `{ "magic_token": "..." }`
- `GET /me`
- `POST /sessions` body `schema: lapsimpro.session.v1`, upsert on `client_session_id`
- `GET` / `PUT /pbs`

## House liveries (paint installer)

The marketing site publishes a Pages-ready pack at `https://lapsimpro.com/data/liveries.json` (`lapsimpro.liveries.v1`). Gallery: `/liveries.html`. Customer Download buttons use:

```text
lapsimpro://paint/install?id=<livery_id>&car_path=<car_path>&pack=lapsimpro-house-gt3
```

When the overlay paint-installer PR lands:

1. Register the `lapsimpro://` protocol (Windows) and handle `paint/install`.
2. Fetch the manifest (or a bundled copy) and resolve `car_path` — these folder names match iRacing (`ferrari296gt3`, `fordmustanggt3`, `bmwm4gt3`, …). BMW M4 GT3 EVO stays in `bmwm4gt3` with alias `bmwm4gt3evo`.
3. Copy TGA files from the pack into `{Documents}/iRacing/paint/{car_path}/car_{customerId}.tga`.
4. If `assets_ready` is false, show the preview and skip the copy — do not invent paint pixels.
5. Never send drivers to a public GitHub URL. Fallback CTA is `https://lapsimpro.com/download.html?paint=<id>`.

Asset drop path on the website repo: `assets/liveries/{car_path}/car.tga`. Helper: `from lapsimpro_sync.paints import protocol_url, install_files, validate_manifest`.

## HUD rules

- Points chip is display-only.
- Do not create a focus-stealing dialog during a session.
- Keep the overlay borderless / click-through behavior unchanged.
