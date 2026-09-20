def test_v1_device_code_session_and_pbs(client):
    client.post("/api/auth/register", json={"email": "overlay@example.com", "password": "password1"})
    minted = client.post("/api/devices/code")
    assert minted.status_code == 200
    code = minted.json()["device_code"]
    assert code.startswith("LSP-")

    auth = client.post("/api/v1/auth/device", json={"device_code": code})
    assert auth.status_code == 200, auth.text
    token = auth.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    me = client.get("/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["email"] == "overlay@example.com"

    payload = {
        "schema": "lapsimpro.session.v1",
        "client_session_id": "sess-laguna-1",
        "track": "WeatherTech Raceway at Laguna Seca",
        "car": "Lamborghini Huracán GT3 EVO",
        "reference_source": "catalog",
        "markers": [{"name": "T1 Andretti", "dist_m": 180}],
        "laps": [
            {
                "lap_time_s": 83.2,
                "valid": True,
                "samples": [
                    {"d": d, "v": 40, "b": 0.7 if 178 <= d < 210 else 0.0, "t": 0.0}
                    for d in range(0, 240, 4)
                ],
            }
        ],
        "point_events": [{"kind": "brake_hit", "points": 10, "detail": "T1 Andretti"}],
    }
    first = client.post("/sessions", headers=headers, json=payload)
    assert first.status_code == 200, first.text
    assert first.json()["points_awarded"] >= 50
    session_id = first.json()["session_id"]

    payload["laps"][0]["lap_time_s"] = 82.1
    second = client.post("/api/v1/sessions", headers=headers, json=payload)
    assert second.status_code == 200
    assert second.json()["session_id"] == session_id

    pbs = client.get("/pbs", headers=headers)
    assert pbs.status_code == 200
    assert pbs.json()["pbs"]

    put = client.put(
        "/pbs",
        headers=headers,
        json={"track": "Barcelona", "car": "Ferrari 296 GT3", "lap_time_s": 101.2},
    )
    assert put.status_code == 200
    tracks = {row["track"] for row in put.json()["pbs"]}
    assert "Barcelona" in tracks


def test_v1_sessions_require_login_not_stripe(gated_client):
    gated_client.post("/api/auth/register", json={"email": "free.overlay@example.com", "password": "password1"})
    assert gated_client.get("/api/download").status_code == 402
    res = gated_client.post(
        "/sessions",
        json={
            "schema": "lapsimpro.session.v1",
            "client_session_id": "free-1",
            "track": "Laguna",
            "car": "Huracan",
            "reference_source": "catalog",
            "point_events": [{"kind": "brake_hit", "points": 10, "detail": "T1", "marker": "T1"}],
            "laps": [{"lap_time_s": 90.0, "valid": True, "samples": []}],
        },
    )
    assert res.status_code == 200, res.text
    assert res.json()["points_awarded"] >= 10


def test_v1_magic_token_login(client):
    link = client.post("/api/v1/auth/magic", json={"email": "magic.driver@example.com"})
    assert link.status_code == 200
    url = link.json()["dev_url"]
    token = url.split("token=")[1]
    auth = client.post("/api/v1/auth/magic", json={"magic_token": token})
    assert auth.status_code == 200
    me = client.get("/api/v1/me", headers={"Authorization": f"Bearer {auth.json()['token']}"})
    assert me.json()["email"] == "magic.driver@example.com"
