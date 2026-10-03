#!/usr/bin/env python3
"""Render original placeholder art into assets/img/sim/.

PLACEHOLDER: these frames are generated graphics, not photographs.
They are not iRacing, RaceLab, or other third-party images.
Replace the WebP files with screenshots you own, then set
"placeholder": false in assets/img/sim/manifest.json.
"""

from __future__ import annotations

import json
import math
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "img" / "sim"

SKY_TOP = (5, 7, 11)
SKY_MID = (16, 22, 30)
HORIZON = (42, 36, 28)
GROUND = (8, 10, 12)
LIME = (214, 255, 74)
RED = (255, 51, 68)
GREEN = (46, 232, 106)
MIST = (170, 190, 200)


def mix(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def gradient(w: int, h: int) -> Image.Image:
    column = Image.new("RGB", (1, h))
    px = column.load()
    for y in range(h):
        t = y / max(1, h - 1)
        if t < 0.58:
            px[0, y] = mix(SKY_TOP, SKY_MID, t / 0.58)
        elif t < 0.72:
            px[0, y] = mix(SKY_MID, HORIZON, (t - 0.58) / 0.14)
        else:
            px[0, y] = mix(HORIZON, GROUND, (t - 0.72) / 0.28)
    return column.resize((w, h), Image.Resampling.BILINEAR).convert("RGBA")


def line_points(w: int, h: int, seed: int) -> list[tuple[float, float]]:
    rng = random.Random(seed)
    count = 8
    pts = []
    for i in range(count):
        x = w * (i / (count - 1))
        wave = math.sin(i * 1.15 + seed) * 0.08
        y = h * (0.62 + wave + rng.uniform(-0.035, 0.035))
        pts.append((x, y))
    return pts


def smooth(pts: list[tuple[float, float]]) -> str:
    if len(pts) < 2:
        return ""
    d = [f"M {pts[0][0]:.1f} {pts[0][1]:.1f}"]
    for i in range(1, len(pts) - 1):
        x = (pts[i][0] + pts[i + 1][0]) / 2
        y = (pts[i][1] + pts[i + 1][1]) / 2
        d.append(f"Q {pts[i][0]:.1f} {pts[i][1]:.1f} {x:.1f} {y:.1f}")
    d.append(f"T {pts[-1][0]:.1f} {pts[-1][1]:.1f}")
    return " ".join(d)


def draw_pillow(img: Image.Image, kind: str, seed: int) -> None:
    w, h = img.size
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    rng = random.Random(seed + 19)
    for i in range(14):
        y = int(h * (0.18 + i * 0.028))
        alpha = 18 if i % 2 == 0 else 10
        d.line([(0, y), (w, y + rng.randint(-8, 8))], fill=(255, 255, 255, alpha), width=2)
    glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse([w * 0.05, h * 0.42, w * 0.92, h * 0.78], fill=(214, 255, 74, 26))
    glow = glow.filter(ImageFilter.GaussianBlur(radius=max(12, w // 48)))
    img.alpha_composite(glow)
    img.alpha_composite(overlay)
    d = ImageDraw.Draw(img)
    pts = line_points(w, h, seed)
    d.line(pts, fill=(*LIME, 230), width=max(3, w // 280), joint="curve")
    d.line(pts, fill=(255, 255, 255, 180), width=max(1, w // 900))
    if kind == "markers":
        for p in pts[1:-1]:
            r = max(6, w // 180)
            d.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], outline=(*RED, 230), width=3)
    elif kind == "bars":
        bar_w = w * 0.045
        base = h * 0.78
        d.rounded_rectangle([w * 0.72, h * 0.34, w * 0.72 + bar_w, base], radius=8, fill=(*RED, 210))
        d.rounded_rectangle([w * 0.80, h * 0.22, w * 0.80 + bar_w, base], radius=8, fill=(*GREEN, 210))
    elif kind == "speed":
        d.line([(w * 0.2, h * 0.4), (w * 0.78, h * 0.4)], fill=(255, 255, 255, 160), width=max(2, w // 500))
        d.polygon([(w * 0.78, h * 0.4), (w * 0.74, h * 0.385), (w * 0.74, h * 0.415)], fill=(255, 255, 255, 200))
    elif kind == "bias":
        cx, cy, r = w * 0.78, h * 0.38, h * 0.12
        d.arc([cx - r, cy - r, cx + r, cy + r], start=200, end=340, fill=(*LIME, 220), width=max(3, w // 400))
    elif kind == "pull":
        d.rounded_rectangle([w * 0.62, h * 0.22, w * 0.9, h * 0.48], radius=16, outline=(*LIME, 200), width=3)
    elif kind == "list":
        for i in range(4):
            y = h * (0.28 + i * 0.08)
            d.rounded_rectangle([w * 0.62, y, w * (0.9 - i * 0.03), y + h * 0.045], radius=6, fill=(255, 255, 255, 40))
    elif kind == "dots":
        for i, color in enumerate((RED, (255, 255, 255), GREEN)):
            cx = w * (0.62 + i * 0.1)
            cy = h * (0.36 + (i - 1) * 0.04)
            r = h * 0.035
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(*color, 220))
    elif kind == "delta":
        d.line([(w * 0.62, h * 0.46), (w * 0.9, h * 0.3)], fill=(*GREEN, 220), width=4)
        d.line([(w * 0.62, h * 0.46), (w * 0.9, h * 0.58)], fill=(*RED, 180), width=3)
    elif kind == "map":
        d.rounded_rectangle([w * 0.58, h * 0.22, w * 0.92, h * 0.55], radius=80, outline=(*LIME, 200), width=4)
        d.arc([w * 0.68, h * 0.3, w * 0.84, h * 0.48], 20, 300, fill=(255, 255, 255, 140), width=3)
    elif kind == "fuel":
        d.rounded_rectangle([w * 0.7, h * 0.24, w * 0.78, h * 0.55], radius=10, outline=(*LIME, 220), width=3)
        d.rectangle([w * 0.715, h * 0.36, w * 0.765, h * 0.53], fill=(*LIME, 180))
    car_x = pts[5][0]
    car_y = pts[5][1]
    scale = w / 900
    body = [
        (car_x - 46 * scale, car_y - 8 * scale),
        (car_x - 10 * scale, car_y - 18 * scale),
        (car_x + 42 * scale, car_y - 14 * scale),
        (car_x + 58 * scale, car_y - 4 * scale),
        (car_x + 36 * scale, car_y + 8 * scale),
        (car_x - 40 * scale, car_y + 8 * scale),
    ]
    d.polygon(body, fill=(236, 240, 236, 230))
    for wx in (-28, 32):
        r = 7 * scale
        cx, cy = car_x + wx * scale, car_y + 8 * scale
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(12, 14, 16, 240))
    vignette = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    vd = ImageDraw.Draw(vignette)
    vd.rectangle([0, 0, w, h], fill=(0, 0, 0, 0))
    vd.rectangle([0, 0, w, int(h * 0.16)], fill=(0, 0, 0, 90))
    vd.rectangle([0, int(h * 0.86), w, h], fill=(0, 0, 0, 110))
    img.alpha_composite(vignette)


def svg_doc(w: int, h: int, kind: str, seed: int) -> str:
    pts = line_points(w, h, seed)
    path = smooth(pts)
    extra = ""
    if kind == "markers":
        extra = "".join(
            f'<circle cx="{p[0]:.1f}" cy="{p[1]:.1f}" r="{max(8, w // 160)}" fill="none" stroke="#ff3344" stroke-width="3"/>'
            for p in pts[1:-1]
        )
    elif kind == "bars":
        extra = (
            f'<rect x="{w * 0.72:.1f}" y="{h * 0.34:.1f}" width="{w * 0.045:.1f}" height="{h * 0.44:.1f}" rx="8" fill="#ff3344"/>'
            f'<rect x="{w * 0.80:.1f}" y="{h * 0.22:.1f}" width="{w * 0.045:.1f}" height="{h * 0.56:.1f}" rx="8" fill="#2ee86a"/>'
        )
    elif kind == "speed":
        extra = (
            f'<line x1="{w * 0.2:.1f}" y1="{h * 0.4:.1f}" x2="{w * 0.78:.1f}" y2="{h * 0.4:.1f}" stroke="#ffffff" stroke-width="3" opacity="0.7"/>'
        )
    elif kind == "bias":
        extra = (
            f'<path d="M {w * 0.70:.1f} {h * 0.46:.1f} A {h * 0.12:.1f} {h * 0.12:.1f} 0 0 1 {w * 0.86:.1f} {h * 0.46:.1f}" fill="none" stroke="#d6ff4a" stroke-width="4"/>'
        )
    elif kind == "pull":
        extra = (
            f'<rect x="{w * 0.62:.1f}" y="{h * 0.22:.1f}" width="{w * 0.28:.1f}" height="{h * 0.26:.1f}" rx="16" fill="none" stroke="#d6ff4a" stroke-width="3"/>'
        )
    elif kind == "list":
        extra = "".join(
            f'<rect x="{w * 0.62:.1f}" y="{h * (0.28 + i * 0.08):.1f}" width="{w * (0.28 - i * 0.03):.1f}" height="{h * 0.045:.1f}" rx="6" fill="#ffffff" opacity="0.16"/>'
            for i in range(4)
        )
    elif kind == "dots":
        extra = "".join(
            f'<circle cx="{w * (0.62 + i * 0.1):.1f}" cy="{h * (0.36 + (i - 1) * 0.04):.1f}" r="{h * 0.035:.1f}" fill="{color}"/>'
            for i, color in enumerate(("#ff3344", "#ffffff", "#2ee86a"))
        )
    elif kind == "delta":
        extra = (
            f'<line x1="{w * 0.62:.1f}" y1="{h * 0.46:.1f}" x2="{w * 0.9:.1f}" y2="{h * 0.3:.1f}" stroke="#2ee86a" stroke-width="4"/>'
            f'<line x1="{w * 0.62:.1f}" y1="{h * 0.46:.1f}" x2="{w * 0.9:.1f}" y2="{h * 0.58:.1f}" stroke="#ff3344" stroke-width="3"/>'
        )
    elif kind == "map":
        extra = (
            f'<rect x="{w * 0.58:.1f}" y="{h * 0.22:.1f}" width="{w * 0.34:.1f}" height="{h * 0.33:.1f}" rx="80" fill="none" stroke="#d6ff4a" stroke-width="4"/>'
        )
    elif kind == "fuel":
        extra = (
            f'<rect x="{w * 0.7:.1f}" y="{h * 0.24:.1f}" width="{w * 0.08:.1f}" height="{h * 0.31:.1f}" rx="10" fill="none" stroke="#d6ff4a" stroke-width="3"/>'
            f'<rect x="{w * 0.715:.1f}" y="{h * 0.36:.1f}" width="{w * 0.05:.1f}" height="{h * 0.17:.1f}" fill="#d6ff4a"/>'
        )
    streaks = "".join(
        f'<line x1="0" y1="{h * (0.18 + i * 0.028):.1f}" x2="{w}" y2="{h * (0.18 + i * 0.03):.1f}" stroke="#ffffff" stroke-width="2" opacity="0.08"/>'
        for i in range(12)
    )
    return f"""<!-- PLACEHOLDER: original LapSimPro art, not an iRacing or third-party screenshot. -->
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-hidden="true">
  <defs>
    <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#05070b"/>
      <stop offset="58%" stop-color="#10161e"/>
      <stop offset="72%" stop-color="#2a241c"/>
      <stop offset="100%" stop-color="#080a0c"/>
    </linearGradient>
  </defs>
  <rect width="{w}" height="{h}" fill="url(#sky)"/>
  <ellipse cx="{w * 0.5:.1f}" cy="{h * 0.62:.1f}" rx="{w * 0.46:.1f}" ry="{h * 0.16:.1f}" fill="#d6ff4a" opacity="0.08"/>
  {streaks}
  <path d="{path}" fill="none" stroke="#d6ff4a" stroke-width="{max(4, w // 240)}" stroke-linecap="round"/>
  <path d="{path}" fill="none" stroke="#ffffff" stroke-width="{max(1, w // 800)}" stroke-linecap="round" opacity="0.85"/>
  {extra}
</svg>
"""


SLOTS = [
    {
        "id": "hero",
        "file": "hero",
        "group": "hero",
        "w": 2560,
        "h": 1440,
        "kind": "sweep",
        "seed": 3,
        "alt": "Placeholder art of a dark circuit and a single racing line.",
    },
    {
        "id": "coach",
        "file": "overlays/coach",
        "group": "overlays",
        "w": 1600,
        "h": 900,
        "kind": "markers",
        "seed": 7,
        "alt": "Placeholder art suggesting brake markers along a racing line.",
    },
    {
        "id": "pedals",
        "file": "overlays/pedals",
        "group": "overlays",
        "w": 1600,
        "h": 900,
        "kind": "bars",
        "seed": 11,
        "alt": "Placeholder art with a reference pedal-bar motif over a dark circuit.",
    },
    {
        "id": "speed",
        "file": "overlays/speed",
        "group": "overlays",
        "w": 1600,
        "h": 900,
        "kind": "speed",
        "seed": 13,
        "alt": "Placeholder art suggesting a live speed comparison on a dark circuit.",
    },
    {
        "id": "bias",
        "file": "overlays/bias",
        "group": "overlays",
        "w": 1600,
        "h": 900,
        "kind": "bias",
        "seed": 17,
        "alt": "Placeholder art with a corner and a brake-bias cue.",
    },
    {
        "id": "reference",
        "file": "overlays/reference",
        "group": "overlays",
        "w": 1600,
        "h": 900,
        "kind": "pull",
        "seed": 19,
        "alt": "Placeholder art suggesting reference data loading for a new track.",
    },
    {
        "id": "standings",
        "file": "overlays/standings",
        "group": "overlays",
        "w": 1600,
        "h": 900,
        "kind": "list",
        "seed": 23,
        "alt": "Placeholder art for the coming-soon standings overlay.",
    },
    {
        "id": "relative",
        "file": "overlays/relative",
        "group": "overlays",
        "w": 1600,
        "h": 900,
        "kind": "dots",
        "seed": 29,
        "alt": "Placeholder art for the coming-soon relative overlay.",
    },
    {
        "id": "delta",
        "file": "overlays/delta",
        "group": "overlays",
        "w": 1600,
        "h": 900,
        "kind": "delta",
        "seed": 31,
        "alt": "Placeholder art for the coming-soon delta overlay.",
    },
    {
        "id": "track-map",
        "file": "overlays/track-map",
        "group": "overlays",
        "w": 1600,
        "h": 900,
        "kind": "map",
        "seed": 37,
        "alt": "Placeholder art of a generic circuit diagram for the coming-soon track map.",
    },
    {
        "id": "fuel",
        "file": "overlays/fuel",
        "group": "overlays",
        "w": 1600,
        "h": 900,
        "kind": "fuel",
        "seed": 41,
        "alt": "Placeholder art for the coming-soon fuel calculator overlay.",
    },
    {
        "id": "gallery-1",
        "file": "gallery/01",
        "group": "gallery",
        "w": 1280,
        "h": 720,
        "kind": "sweep",
        "seed": 43,
        "alt": "Placeholder art, gallery frame of a night circuit.",
    },
    {
        "id": "gallery-2",
        "file": "gallery/02",
        "group": "gallery",
        "w": 1280,
        "h": 720,
        "kind": "markers",
        "seed": 47,
        "alt": "Placeholder art, gallery frame with corner markers.",
    },
    {
        "id": "gallery-3",
        "file": "gallery/03",
        "group": "gallery",
        "w": 1280,
        "h": 720,
        "kind": "speed",
        "seed": 53,
        "alt": "Placeholder art, gallery frame with a speed streak.",
    },
    {
        "id": "gallery-4",
        "file": "gallery/04",
        "group": "gallery",
        "w": 1280,
        "h": 720,
        "kind": "sweep",
        "seed": 59,
        "alt": "Placeholder art, gallery frame of a sweeping racing line.",
    },
    {
        "id": "gallery-5",
        "file": "gallery/05",
        "group": "gallery",
        "w": 1280,
        "h": 720,
        "kind": "map",
        "seed": 61,
        "alt": "Placeholder art, gallery frame with a generic circuit outline.",
    },
    {
        "id": "gallery-6",
        "file": "gallery/06",
        "group": "gallery",
        "w": 1280,
        "h": 720,
        "kind": "bars",
        "seed": 67,
        "alt": "Placeholder art, gallery frame with pedal-colored bars.",
    },
]


def write_slot(slot: dict) -> dict:
    rel = slot["file"]
    svg_path = OUT / f"{rel}.svg"
    webp_path = OUT / f"{rel}.webp"
    svg_path.parent.mkdir(parents=True, exist_ok=True)
    svg_path.write_text(svg_doc(slot["w"], slot["h"], slot["kind"], slot["seed"]), encoding="utf-8")
    img = gradient(slot["w"], slot["h"])
    draw_pillow(img, slot["kind"], slot["seed"])
    img.convert("RGB").save(webp_path, "WEBP", quality=62, method=6)
    return {
        "id": slot["id"],
        "alt": slot["alt"],
        "width": slot["w"],
        "height": slot["h"],
        "placeholder": True,
        "webp": f"{rel}.webp",
        "fallback": f"{rel}.svg",
    }


def main() -> None:
    entries = [write_slot(slot) for slot in SLOTS]
    hero = next(item for item in entries if item["id"] == "hero")
    overlays = [item for item in entries if item["id"] not in {hero["id"]} and not item["id"].startswith("gallery-")]
    gallery = [item for item in entries if item["id"].startswith("gallery-")]
    manifest = {
        "version": 1,
        "notes": "PLACEHOLDER art. Replace WebP files with iRacing screenshots you own. Set placeholder to false and update alt. Do not hotlink third-party images.",
        "hero": hero,
        "overlays": overlays,
        "gallery": gallery,
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(entries)} slots to {OUT}")


if __name__ == "__main__":
    main()
