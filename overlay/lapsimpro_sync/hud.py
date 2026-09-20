"""Non-intrusive points toast for the overlay HUD."""

from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class HudToast:
    text: str
    until: float


class PointsHud:
    """Small counter + fading toast. Does not take focus or create windows."""

    def __init__(self, fade_s: float = 2.2):
        self.total = 0
        self.toast: HudToast | None = None
        self.fade_s = fade_s

    def add(self, points: int, detail: str) -> None:
        if points <= 0:
            return
        self.total += points
        self.toast = HudToast(text=f"+{points}  {detail}", until=time.monotonic() + self.fade_s)

    def snapshot(self) -> dict:
        toast = None
        if self.toast and time.monotonic() < self.toast.until:
            toast = self.toast.text
        elif self.toast:
            self.toast = None
        return {
            "points_total": self.total,
            "toast": toast,
            "visible": True,
        }
