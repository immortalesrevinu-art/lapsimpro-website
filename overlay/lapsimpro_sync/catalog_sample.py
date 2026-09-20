"""Honest catalog_sample for local replay — not a Garage 61 pedal invent."""

from __future__ import annotations

TRACK = "WeatherTech Raceway at Laguna Seca"
CAR = "Lamborghini Huracán GT3 EVO"
REF_SOURCE = "catalog_sample"
REF_LAP_S = 82.436

MARKERS = [
    {"name": "T1 Andretti", "dist_m": 180.0},
    {"name": "T3-4 Corkscrew", "dist_m": 520.0},
]


def _trace(brake_at: float, release_at: float, throttle_at: float, extra_slow: float = 0.0) -> list[dict]:
    samples: list[dict] = []
    for d in range(0, 801, 4):
        b = 0.0
        t = 1.0
        v = 52.0
        if brake_at <= d < release_at:
            b = 0.75
            t = 0.0
            v = 38.0 - extra_slow
        elif release_at <= d < throttle_at:
            b = 0.08
            t = 0.05
            v = 36.0 - extra_slow
        elif throttle_at <= d < throttle_at + 40:
            b = 0.0
            t = 0.7
            v = 42.0 - extra_slow * 0.4
        samples.append({"d": float(d), "v": v, "b": b, "t": t})
    return samples


def reference_samples() -> list[dict]:
    # Two corners: brake 176/516, release 210/560, throttle 220/572
    first = _trace(176, 210, 220)
    # Overlay second corner onto the same distance series.
    out = []
    for sample in first:
        d = sample["d"]
        if 500 <= d <= 640:
            if 516 <= d < 560:
                sample = {"d": d, "v": 34.0, "b": 0.8, "t": 0.0}
            elif 560 <= d < 572:
                sample = {"d": d, "v": 33.0, "b": 0.08, "t": 0.04}
            elif 572 <= d < 620:
                sample = {"d": d, "v": 40.0, "b": 0.0, "t": 0.75}
        out.append(sample)
    return out


def driver_slow_samples() -> list[dict]:
    """Late T1 brake, delayed throttle — used for coaching + first PB."""
    first = _trace(192, 230, 250, extra_slow=4)
    out = []
    for sample in first:
        d = sample["d"]
        if 500 <= d <= 660:
            if 534 <= d < 580:
                sample = {"d": d, "v": 29.0, "b": 0.85, "t": 0.0}
            elif 580 <= d < 610:
                sample = {"d": d, "v": 28.0, "b": 0.1, "t": 0.02}
            elif 610 <= d < 650:
                sample = {"d": d, "v": 35.0, "b": 0.0, "t": 0.6}
        out.append(sample)
    return out


def driver_fast_samples() -> list[dict]:
    """Hits both brake windows and improves the lap."""
    first = _trace(178, 211, 221)
    out = []
    for sample in first:
        d = sample["d"]
        if 500 <= d <= 640:
            if 518 <= d < 561:
                sample = {"d": d, "v": 34.5, "b": 0.78, "t": 0.0}
            elif 561 <= d < 573:
                sample = {"d": d, "v": 33.5, "b": 0.07, "t": 0.05}
            elif 573 <= d < 620:
                sample = {"d": d, "v": 40.5, "b": 0.0, "t": 0.78}
        out.append(sample)
    return out
