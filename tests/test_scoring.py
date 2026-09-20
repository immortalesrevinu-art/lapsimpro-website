from overlay.lapsimpro_sync.coaching import analyze
from overlay.lapsimpro_sync.honesty import bind_gates
from overlay.lapsimpro_sync.scoring import ScoreConfig, score_session


def test_bind_refuses_invented_g61():
    ok, reason = bind_gates(
        "Laguna Seca",
        "Huracan GT3 EVO",
        "Laguna Seca",
        "Huracan GT3 EVO",
        "g61_placeholder",
    )
    assert ok is False
    assert "NO REFERENCE" in reason


def test_bind_refuses_track_mismatch():
    ok, reason = bind_gates("Barcelona", "Ferrari 296 GT3", "Laguna Seca", "Ferrari 296 GT3", "catalog")
    assert ok is False
    assert "NO REFERENCE FOR THIS TRACK" in reason


def test_brake_hit_and_personal_best():
    markers = [{"name": "T1 Andretti", "dist_m": 180}]
    samples = []
    for d in range(0, 240, 4):
        samples.append({"d": d, "v": 40, "b": 0.7 if 178 <= d < 210 else 0.0, "t": 0.0 if 178 <= d < 210 else 1.0})
    result = score_session(
        session_track="Laguna Seca",
        session_car="Huracan",
        ref_track="Laguna Seca",
        ref_car="Huracan",
        ref_source="catalog",
        samples=samples,
        markers=markers,
        lap_time_s=83.2,
        previous_best_s=None,
        config=ScoreConfig(),
    )
    kinds = {e.kind for e in result.events}
    assert "brake_hit" in kinds
    assert "lap_pb" in kinds
    assert result.points == 60


def test_faster_lap_awards_improve():
    result = score_session(
        session_track="Laguna",
        session_car="Huracan",
        ref_track="Laguna",
        ref_car="Huracan",
        ref_source="catalog",
        samples=[{"d": 0, "v": 50, "b": 0, "t": 1}],
        markers=[],
        lap_time_s=82.1,
        previous_best_s=83.2,
    )
    assert result.events[0].kind == "lap_improve"
    assert result.events[0].points == 25


def test_coaching_late_brake():
    markers = [{"name": "T1 Andretti", "dist_m": 180}]
    ref = []
    driver = []
    for d in range(0, 280, 4):
        ref.append({"d": d, "v": 40 if d < 176 or d > 220 else 32, "b": 0.8 if 176 <= d < 210 else 0.0, "t": 0.8 if d > 220 else 0.0})
        driver.append({"d": d, "v": 36 if d < 192 or d > 250 else 28, "b": 0.8 if 192 <= d < 230 else 0.0, "t": 0.6 if d > 250 else 0.0})
    cards = analyze(
        session_track="Laguna Seca",
        session_car="Huracan",
        ref_track="Laguna Seca",
        ref_car="Huracan",
        ref_source="catalog_sample",
        driver_samples=driver,
        ref_samples=ref,
        markers=markers,
    )
    titles = " ".join(c.title for c in cards)
    assert "late brake" in titles.lower()
