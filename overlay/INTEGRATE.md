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

Before the race HUD (a separate window is fine):

```text
python -m lapsimpro_sync login --api https://api.lapsimpro.com
```

Or paste a device token from the website Account page. The token is stored at `~/.lapsimpro/session.json` with `0600` permissions.

## HUD rules

- Points chip is display-only.
- Do not create a focus-stealing dialog during a session.
- Keep the overlay borderless / click-through behavior unchanged.
