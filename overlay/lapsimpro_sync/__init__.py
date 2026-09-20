"""LapSimPro overlay training aid: login, live points, coaching, sync."""

from .client import AccountClient
from .engine import TrainingAid
from .honesty import bind_gates
from .hud import PointsHud
from .paints import (
    CATALOG_CAR_PATHS,
    PACK_ID,
    install_files,
    paint_dest,
    parse_protocol_url,
    protocol_url,
    validate_manifest,
)
from .scoring import ScoreConfig, score_session
from .store import clear_session, load_session, save_session

__all__ = [
    "AccountClient",
    "CATALOG_CAR_PATHS",
    "PACK_ID",
    "PointsHud",
    "ScoreConfig",
    "TrainingAid",
    "bind_gates",
    "clear_session",
    "install_files",
    "load_session",
    "paint_dest",
    "parse_protocol_url",
    "protocol_url",
    "save_session",
    "score_session",
    "validate_manifest",
]
