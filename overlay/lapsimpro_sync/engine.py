"""Live training aid: bind catalog refs, score ticks, queue sync."""

from __future__ import annotations

from dataclasses import dataclass, field

from .coaching import analyze
from .honesty import bind_gates
from .hud import PointsHud
from .scoring import Marker, Sample, ScoreConfig, as_markers, score_brake_hits, score_lap_time


@dataclass
class LiveState:
    track: str = ""
    car: str = ""
    ref_track: str = ""
    ref_car: str = ""
    ref_source: str = ""
    ref_samples: list[dict] = field(default_factory=list)
    markers: list[Marker] = field(default_factory=list)
    bind_ok: bool = False
    bind_reason: str = "NO SESSION IDENTITY"


class TrainingAid:
    def __init__(self, config: ScoreConfig | None = None):
        self.config = config or ScoreConfig()
        self.state = LiveState()
        self.hud = PointsHud()
        self._lap_samples: list[Sample] = []
        self._scored_markers: set[str] = set()
        self._events: list[dict] = []
        self._best_s: float | None = None
        self._laps: list[dict] = []
        self.session_started: str | None = None

    def bind_session(self, track: str, car: str) -> str:
        self.state.track = track
        self.state.car = car
        return self._rebind()

    def set_reference(
        self,
        track: str,
        car: str,
        source: str,
        markers: list[dict],
        samples: list[dict] | None = None,
    ) -> str:
        self.state.ref_track = track
        self.state.ref_car = car
        self.state.ref_source = source
        self.state.markers = as_markers(markers)
        self.state.ref_samples = list(samples or [])
        return self._rebind()

    def _rebind(self) -> str:
        ok, reason = bind_gates(
            self.state.track,
            self.state.car,
            self.state.ref_track,
            self.state.ref_car,
            self.state.ref_source,
        )
        self.state.bind_ok = ok
        self.state.bind_reason = reason
        return reason

    def tick(self, dist_m: float, speed: float, brake: float, throttle: float, on_track: bool = True) -> None:
        if not on_track or not self.state.bind_ok:
            return
        sample = Sample(d=float(dist_m), v=float(speed), b=float(brake), t=float(throttle))
        self._lap_samples.append(sample)
        fresh = score_brake_hits(self._lap_samples, self.state.markers, self.config)
        for event in fresh:
            key = event.marker or event.detail
            if key in self._scored_markers:
                continue
            self._scored_markers.add(key)
            self._events.append(event.__dict__)
            self.hud.add(event.points, event.detail)

    def end_lap(self, lap_time_s: float, valid: bool = True) -> None:
        if not self.state.bind_ok:
            self._reset_lap()
            return
        event = score_lap_time(lap_time_s, self._best_s, self.config) if valid else None
        if event:
            self._events.append(event.__dict__)
            self.hud.add(event.points, event.detail)
            self._best_s = lap_time_s
        elif valid and (self._best_s is None or lap_time_s < self._best_s):
            self._best_s = lap_time_s
        self._laps.append(
            {
                "lap_time_s": lap_time_s,
                "valid": valid,
                "samples": [s.__dict__ for s in self._lap_samples],
                "personal_best": bool(event and event.kind in {"lap_pb", "lap_improve"}),
            }
        )
        self._reset_lap()

    def _reset_lap(self) -> None:
        self._lap_samples = []
        self._scored_markers = set()

    def coaching(self) -> list[dict]:
        cards: list[dict] = []
        seen: set[str] = set()
        markers = [{"name": m.name, "dist_m": m.dist_m} for m in self.state.markers]
        for lap in self._laps:
            if not lap.get("samples"):
                continue
            for card in analyze(
                session_track=self.state.track,
                session_car=self.state.car,
                ref_track=self.state.ref_track,
                ref_car=self.state.ref_car,
                ref_source=self.state.ref_source,
                driver_samples=lap["samples"],
                ref_samples=self.state.ref_samples,
                markers=markers,
            ):
                if card.title in seen:
                    continue
                seen.add(card.title)
                cards.append(card.__dict__)
        return cards

    def flush_payload(self) -> dict:
        best = None
        valid_times = [lap["lap_time_s"] for lap in self._laps if lap.get("valid") and lap.get("lap_time_s")]
        if valid_times:
            best = min(valid_times)
        return {
            "session": {
                "track": self.state.track,
                "car": self.state.car,
                "reference_source": self.state.ref_source,
                "bind_ok": self.state.bind_ok,
                "bind_reason": self.state.bind_reason,
                "best_lap_s": best,
            },
            "reference": {
                "track": self.state.ref_track,
                "car": self.state.ref_car,
                "source": self.state.ref_source,
                "markers": [{"name": m.name, "dist_m": m.dist_m} for m in self.state.markers],
                "samples": self.state.ref_samples,
            },
            "laps": self._laps,
            "point_events": self._events,
            "coaching": self.coaching(),
            "points_total": self.hud.total,
        }
