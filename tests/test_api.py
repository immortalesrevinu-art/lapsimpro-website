from overlay.lapsimpro_sync.catalog_sample import (
    CAR,
    MARKERS,
    REF_SOURCE,
    TRACK,
    driver_fast_samples,
    driver_slow_samples,
    reference_samples,
)
from overlay.lapsimpro_sync.engine import TrainingAid


def _register(client, email="driver@example.com"):
    res = client.post("/api/auth/register", json={"email": email, "password": "password1"})
    assert res.status_code == 200, res.text
    return res.json()


def test_register_login_and_me(client):
    created = _register(client)
    assert created["user"]["email"] == "driver@example.com"
    assert created["user"]["entitlement"]["active"] is True
    me = client.get("/api/me")
    assert me.status_code == 200
    login = client.post("/api/auth/login", json={"email": "driver@example.com", "password": "password1"})
    assert login.status_code == 200


def test_download_requires_entitlement(gated_client):
    gated_client.post("/api/auth/register", json={"email": "free@example.com", "password": "password1"})
    res = gated_client.get("/api/download")
    assert res.status_code == 402


def test_overlay_sync_awards_points_and_coaching(client):
    _register(client)
    aid = TrainingAid()
    aid.bind_session(TRACK, CAR)
    aid.set_reference(TRACK, CAR, REF_SOURCE, MARKERS, reference_samples())
    for sample in driver_slow_samples():
        aid.tick(sample["d"], sample["v"], sample["b"], sample["t"])
    aid.end_lap(83.200, True)
    for sample in driver_fast_samples():
        aid.tick(sample["d"], sample["v"], sample["b"], sample["t"])
    aid.end_lap(82.100, True)
    payload = aid.flush_payload()
    sync = client.post("/api/overlay/sync", json=payload)
    assert sync.status_code == 200, sync.text
    body = sync.json()
    assert body["points_awarded"] >= 60
    kinds = {e["kind"] for e in body["events"]}
    assert "brake_hit" in kinds or "brake_close" in kinds
    assert "lap_pb" in kinds
    assert "lap_improve" in kinds
    assert body["coaching"]

    dash = client.get("/api/dashboard")
    assert dash.status_code == 200
    data = dash.json()
    assert data["points_total"] >= 60
    assert data["sessions"]
    assert data["best_laps"]
    assert data["coaching"]


def test_demo_session_endpoint(client):
    _register(client)
    res = client.post("/api/demo/session")
    assert res.status_code == 200, res.text
    assert res.json()["points_awarded"] > 0
    dash = client.get("/api/dashboard").json()
    assert dash["points_total"] > 0
