"""How-to-get-faster cards from driver telemetry vs a bound reference."""

from __future__ import annotations

from dataclasses import dataclass

from .honesty import bind_gates
from .scoring import Marker, Sample, as_markers, as_samples, first_threshold


@dataclass(frozen=True)
class CoachingCard:
    title: str
    body: str
    tone: str
    corner: str | None = None
    metric: str | None = None
    delta: float | None = None


def _brake_release(samples: list[Sample], after_d: float, until_d: float, threshold: float) -> float | None:
    prev = None
    for sample in samples:
        if sample.d < after_d or sample.d > until_d:
            prev = sample
            continue
        prev_b = prev.b if prev is not None else 1.0
        if sample.b < threshold and prev_b >= threshold:
            return sample.d
        prev = sample
    return None


def _mean_speed(samples: list[Sample], start_d: float, end_d: float) -> float | None:
    vals = [s.v for s in samples if start_d <= s.d <= end_d]
    if not vals:
        return None
    return sum(vals) / len(vals)


def analyze(
    *,
    session_track: str,
    session_car: str,
    ref_track: str,
    ref_car: str,
    ref_source: str,
    driver_samples: list[dict | Sample],
    ref_samples: list[dict | Sample],
    markers: list[dict | Marker],
    brake_threshold: float = 0.2,
    throttle_threshold: float = 0.3,
) -> list[CoachingCard]:
    ok, reason = bind_gates(session_track, session_car, ref_track, ref_car, ref_source)
    if not ok:
        return [
            CoachingCard(
                title="No bound reference",
                body=reason
                + ". Coaching stays off until the overlay binds a catalog lap for this track and car.",
                tone="amber",
            )
        ]

    driver = as_samples(driver_samples)
    reference = as_samples(ref_samples)
    if not driver or not reference:
        return [
            CoachingCard(
                title="Need a reference trace",
                body="A catalog reference with brake/throttle/speed samples is required. Nothing is invented.",
                tone="amber",
            )
        ]

    cards: list[CoachingCard] = []
    for marker in as_markers(markers):
        window = 40.0
        start, end = marker.dist_m - window, marker.dist_m + window
        d_brake = first_threshold(driver, start, end, "b", brake_threshold)
        r_brake = first_threshold(reference, start, end, "b", brake_threshold)
        if d_brake is not None and r_brake is not None:
            delta = d_brake - r_brake
            if delta > 4:
                cards.append(
                    CoachingCard(
                        title=f"{marker.name} — late brake",
                        body=f"You braked {delta:.1f} m later than the reference. Start the pedal earlier so the car is set before the apex.",
                        tone="red",
                        corner=marker.name,
                        metric="brake_delta_m",
                        delta=round(delta, 2),
                    )
                )
            elif delta < -4:
                cards.append(
                    CoachingCard(
                        title=f"{marker.name} — early brake",
                        body=f"You braked {abs(delta):.1f} m earlier than the reference. Carry a little more speed to the mark.",
                        tone="amber",
                        corner=marker.name,
                        metric="brake_delta_m",
                        delta=round(delta, 2),
                    )
                )

        d_rel = _brake_release(driver, marker.dist_m, marker.dist_m + 80, brake_threshold)
        r_rel = _brake_release(reference, marker.dist_m, marker.dist_m + 80, brake_threshold)
        if d_rel is not None and r_rel is not None:
            d_thr = first_threshold(driver, d_rel, d_rel + 80, "t", throttle_threshold)
            r_thr = first_threshold(reference, r_rel, r_rel + 80, "t", throttle_threshold)
            if d_thr is not None and r_thr is not None:
                delay = (d_thr - d_rel) - (r_thr - r_rel)
                if delay > 6:
                    cards.append(
                        CoachingCard(
                            title=f"{marker.name} — throttle delay",
                            body=f"Throttle came back ~{delay:.0f} m later than the reference after release. Pick up sooner once the car is straight.",
                            tone="amber",
                            corner=marker.name,
                            metric="throttle_delay_m",
                            delta=round(delay, 2),
                        )
                    )

        d_spd = _mean_speed(driver, marker.dist_m, marker.dist_m + 25)
        r_spd = _mean_speed(reference, marker.dist_m, marker.dist_m + 25)
        if d_spd and r_spd and (r_spd - d_spd) > 3:
            cards.append(
                CoachingCard(
                    title=f"{marker.name} — speed delta",
                    body=f"Minimum-speed window is {r_spd - d_spd:.1f} slower than the reference. Work the brake release so you don't over-slow.",
                    tone="cyan",
                    corner=marker.name,
                    metric="speed_delta",
                    delta=round(r_spd - d_spd, 2),
                )
            )

    cards.sort(key=lambda c: abs(c.delta or 0), reverse=True)
    return cards[:4]
