from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load_dotenv() -> None:
    path = ROOT / ".env"
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


_load_dotenv()


def _bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    return float(raw) if raw else default


def _int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    return int(raw) if raw else default


@dataclass(frozen=True)
class Settings:
    secret: str
    db_path: Path
    public_url: str
    download_url: str
    dev_entitlement: bool
    stripe_secret_key: str
    stripe_webhook_secret: str
    price_starter: str
    price_pro: str
    price_elite: str
    cors_origins: tuple[str, ...]
    brake_hit_window_m: float
    brake_time_window_s: float
    brake_close_window_m: float
    brake_threshold: float
    brake_hit_points: int
    brake_close_points: int
    lap_pb_points: int
    lap_improve_points: int


def load_settings() -> Settings:
    db = Path(os.environ.get("LAPSIMPRO_DB") or ROOT / "data" / "lapsimpro.db")
    if not db.is_absolute():
        db = ROOT / db
    origins = os.environ.get(
        "LAPSIMPRO_CORS_ORIGINS",
        "https://lapsimpro.com,https://www.lapsimpro.com,http://127.0.0.1:8787,http://localhost:8787",
    )
    return Settings(
        secret=os.environ.get("LAPSIMPRO_SECRET") or "dev-only-change-me",
        db_path=db,
        public_url=(os.environ.get("LAPSIMPRO_PUBLIC_URL") or "http://127.0.0.1:8787").rstrip("/"),
        download_url=os.environ.get("LAPSIMPRO_DOWNLOAD_URL")
        or "https://github.com/immortalesrevinu-art/iracing-coach-overlay/releases/download/v0.1.0/LapSimPro-Setup.zip",
        dev_entitlement=_bool("LAPSIMPRO_DEV_ENTITLEMENT"),
        stripe_secret_key=os.environ.get("STRIPE_SECRET_KEY") or "",
        stripe_webhook_secret=os.environ.get("STRIPE_WEBHOOK_SECRET") or "",
        price_starter=os.environ.get("STRIPE_PRICE_STARTER") or "price_1UGOsMPVazkD4GpuxvLFjoCJ",
        price_pro=os.environ.get("STRIPE_PRICE_PRO") or "price_1UGOsNPVazkD4GpuP7jWZuax",
        price_elite=os.environ.get("STRIPE_PRICE_ELITE") or "price_1UGOsMPVazkD4GpuqAtr8Muv",
        cors_origins=tuple(o.strip() for o in origins.split(",") if o.strip()),
        brake_hit_window_m=_float("BRAKE_HIT_WINDOW_M", 12.0),
        brake_time_window_s=_float("BRAKE_TIME_WINDOW_S", 0.35),
        brake_close_window_m=_float("BRAKE_CLOSE_WINDOW_M", 20.0),
        brake_threshold=_float("BRAKE_THRESHOLD", 0.2),
        brake_hit_points=_int("BRAKE_HIT_POINTS", 10),
        brake_close_points=_int("BRAKE_CLOSE_POINTS", 5),
        lap_pb_points=_int("LAP_PB_POINTS", 50),
        lap_improve_points=_int("LAP_IMPROVE_POINTS", 25),
    )
