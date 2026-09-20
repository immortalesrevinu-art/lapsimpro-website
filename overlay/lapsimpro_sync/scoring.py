"""Live training points: brake-marker windows and personal-best laps."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from .honesty import bind_gates


@dataclass(frozen=True)
class ScoreConfig:
    brake_hit_window_m: float = 8.0
    brake_close_window_m: float = 16.0
    brake_threshold: float = 0.2
    brake_hit_points: int = 10
    brake_close_points: int = 5
    lap_pb_points: int = 50
    lap_improve_points: int = 25


@dataclass(frozen=True)
class Marker:
    name: str
    dist_m: float


@dataclass(frozen=True)
class Sample:
    d: float
    v: float = 0.0
    b: float = 0.0
    t: float = 0.0


@dataclass(frozen=True)
class PointEvent:
    kind: str
    points: int
    detail: str
    marker: str | None = None
    delta_m: float | None = None
    lap_time_s: float | None = None


@dataclass
class ScoreResult:
    events: list[PointEvent] = field(default_factory=list)
    rejected: str | None = None

    @property
    def points(self) -> int:
        return sum(e.points for e in self.events)


def as_samples(rows: Iterable[dict | Sample]) -> list[Sample]:
    out: list[Sample] = []
    for row in rows:
        if isinstance(row, Sample):
            out.append(row)
            continue
        out.append(
            Sample(
                d=float(row.get("d", row.get("dist_m", 0))),
                v=float(row.get("v", row.get("speed", 0)) or 0),
                b=float(row.get("b", row.get("brake", 0)) or 0),
                t=float(row.get("t", row.get("throttle", 0)) or 0),
            )
        )
    return out


def as_markers(rows: Iterable[dict | Marker]) -> list[Marker]:
    out: list[Marker] = []
    for row in rows:
        if isinstance(row, Marker):
            out.append(row)
            continue
        out.append(
            Marker(
                name=str(row.get("name") or row.get("marker") or "marker"),
                dist_m=float(row.get("dist_m", row.get("d", 0))),
            )
        )
    return out


def first_threshold(
    samples: list[Sample],
    start_d: float,
    end_d: float,
    attr: str,
    threshold: float,
) -> float | None:
    prev = None
    for sample in samples:
        if sample.d < start_d or sample.d > end_d:
            prev = sample
            continue
        value = getattr(sample, attr)
        prev_value = getattr(prev, attr) if prev is not None else 0.0
        if value >= threshold and prev_value < threshold:
            return sample.d
        prev = sample
    return None


def score_brake_hits(
    samples: list[Sample],
    markers: list[Marker],
    config: ScoreConfig | None = None,
) -> list[PointEvent]:
    cfg = config or ScoreConfig()
    events: list[PointEvent] = []
    seen: set[str] = set()
    for marker in markers:
        if marker.name in seen:
            continue
        hit_d = first_threshold(
            samples,
            marker.dist_m - cfg.brake_close_window_m,
            marker.dist_m + cfg.brake_close_window_m,
            "b",
            cfg.brake_threshold,
        )
        if hit_d is None:
            continue
        delta = hit_d - marker.dist_m
        abs_delta = abs(delta)
        if abs_delta <= cfg.brake_hit_window_m:
            events.append(
                PointEvent(
                    kind="brake_hit",
                    points=cfg.brake_hit_points,
                    detail=f"{marker.name} brake window ({delta:+.1f} m)",
                    marker=marker.name,
                    delta_m=round(delta, 2),
                )
            )
            seen.add(marker.name)
        elif abs_delta <= cfg.brake_close_window_m:
            events.append(
                PointEvent(
                    kind="brake_close",
                    points=cfg.brake_close_points,
                    detail=f"{marker.name} close brake ({delta:+.1f} m)",
                    marker=marker.name,
                    delta_m=round(delta, 2),
                )
            )
            seen.add(marker.name)
    return events


def score_lap_time(
    lap_time_s: float,
    previous_best_s: float | None,
    config: ScoreConfig | None = None,
) -> PointEvent | None:
    cfg = config or ScoreConfig()
    if lap_time_s <= 0:
        return None
    if previous_best_s is None:
        return PointEvent(
            kind="lap_pb",
            points=cfg.lap_pb_points,
            detail=f"First personal best {lap_time_s:.3f}s",
            lap_time_s=lap_time_s,
        )
    if lap_time_s + 0.001 < previous_best_s:
        gained = previous_best_s - lap_time_s
        return PointEvent(
            kind="lap_improve",
            points=cfg.lap_improve_points,
            detail=f"Faster by {gained:.3f}s ({lap_time_s:.3f}s)",
            lap_time_s=lap_time_s,
        )
    return None


def score_session(
    *,
    session_track: str,
    session_car: str,
    ref_track: str,
    ref_car: str,
    ref_source: str,
    samples: Iterable[dict | Sample],
    markers: Iterable[dict | Marker],
    lap_time_s: float | None,
    previous_best_s: float | None,
    valid_lap: bool = True,
    config: ScoreConfig | None = None,
) -> ScoreResult:
    ok, reason = bind_gates(session_track, session_car, ref_track, ref_car, ref_source)
    if not ok:
        return ScoreResult(rejected=reason)
    cfg = config or ScoreConfig()
    parsed_samples = as_samples(samples)
    parsed_markers = as_markers(markers)
    events = score_brake_hits(parsed_samples, parsed_markers, cfg)
    if valid_lap and lap_time_s:
        lap_event = score_lap_time(lap_time_s, previous_best_s, cfg)
        if lap_event:
            events.append(lap_event)
    return ScoreResult(events=events)
