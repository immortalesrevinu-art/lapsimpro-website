from __future__ import annotations

import json
import secrets
import sys
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import entitlements
from .auth import expires_in, hash_password, hash_token, iso, new_token, normalize_email, verify_password
from .config import ROOT, load_settings
from .db import session as db_session

if str(ROOT / "overlay") not in sys.path:
    sys.path.insert(0, str(ROOT / "overlay"))

from lapsimpro_sync.catalog_sample import (  # noqa: E402
    CAR as SAMPLE_CAR,
    MARKERS as SAMPLE_MARKERS,
    REF_SOURCE as SAMPLE_SOURCE,
    TRACK as SAMPLE_TRACK,
    driver_fast_samples,
    driver_slow_samples,
    reference_samples,
)
from lapsimpro_sync.coaching import analyze  # noqa: E402
from lapsimpro_sync.engine import TrainingAid  # noqa: E402
from lapsimpro_sync.scoring import ScoreConfig, score_session  # noqa: E402

settings = load_settings()
COOKIE = "lsp_session"

app = FastAPI(title="LapSimPro training API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def score_config() -> ScoreConfig:
    return ScoreConfig(
        brake_hit_window_m=settings.brake_hit_window_m,
        brake_close_window_m=settings.brake_close_window_m,
        brake_threshold=settings.brake_threshold,
        brake_hit_points=settings.brake_hit_points,
        brake_close_points=settings.brake_close_points,
        lap_pb_points=settings.lap_pb_points,
        lap_improve_points=settings.lap_improve_points,
    )


def row_user(row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "email": row["email"],
        "created_at": row["created_at"],
        "stripe_customer_id": row["stripe_customer_id"],
        "plan": row["plan"],
        "entitlement_active": bool(row["entitlement_active"]),
        "entitlement_checked_at": row["entitlement_checked_at"],
    }


def persist_entitlement(conn, user_id: str, result: dict[str, Any]) -> None:
    conn.execute(
        """
        UPDATE users
        SET stripe_customer_id = COALESCE(?, stripe_customer_id),
            plan = ?,
            entitlement_active = ?,
            entitlement_checked_at = ?
        WHERE id = ?
        """,
        (
            result.get("customer_id"),
            result.get("plan"),
            1 if result.get("active") else 0,
            iso(),
            user_id,
        ),
    )


def current_user(request: Request, authorization: str | None) -> dict[str, Any]:
    token = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
    if not token:
        token = request.cookies.get(COOKIE)
    if not token:
        raise HTTPException(status_code=401, detail="Sign in required")
    token_hash = hash_token(token, settings.secret)
    with db_session(settings.db_path) as conn:
        row = conn.execute(
            """
            SELECT u.*, t.expires_at
            FROM auth_tokens t
            JOIN users u ON u.id = t.user_id
            WHERE t.token_hash = ?
            """,
            (token_hash,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=401, detail="Session expired")
        if row["expires_at"] and row["expires_at"] < iso():
            conn.execute("DELETE FROM auth_tokens WHERE token_hash = ?", (token_hash,))
            raise HTTPException(status_code=401, detail="Session expired")
        user = row_user(row)
    return user


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        COOKIE,
        token,
        httponly=True,
        samesite="lax",
        secure=settings.public_url.startswith("https://"),
        max_age=60 * 60 * 24 * 30,
        path="/",
    )


def issue_token(conn, user_id: str, kind: str, name: str | None, hours: float) -> str:
    token = new_token()
    conn.execute(
        "INSERT INTO auth_tokens (token_hash, user_id, kind, name, created_at, expires_at) VALUES (?,?,?,?,?,?)",
        (hash_token(token, settings.secret), user_id, kind, name, iso(), expires_in(hours)),
    )
    return token


def require_entitlement(user: dict[str, Any]) -> dict[str, Any]:
    result = entitlements.entitlement_for_user(settings, user)
    with db_session(settings.db_path) as conn:
        persist_entitlement(conn, user["id"], result)
    if not result.get("active"):
        raise HTTPException(
            status_code=402,
            detail="Active LapSimPro subscription required for download and cloud training.",
        )
    return result


def _email(value: str) -> str:
    email = normalize_email(value)
    if "@" not in email or "." not in email.split("@")[-1]:
        raise HTTPException(status_code=400, detail="Enter a valid email")
    return email


class RegisterBody(BaseModel):
    email: str
    password: str = Field(min_length=8, max_length=200)


class LoginBody(BaseModel):
    email: str
    password: str
    device_name: str | None = None


class MagicBody(BaseModel):
    email: str


class DeviceBody(BaseModel):
    name: str = "overlay"


class CheckoutBody(BaseModel):
    plan: str


class ClaimBody(BaseModel):
    session_id: str


class SyncBody(BaseModel):
    session: dict[str, Any]
    reference: dict[str, Any]
    laps: list[dict[str, Any]] = Field(default_factory=list)
    point_events: list[dict[str, Any]] = Field(default_factory=list)
    coaching: list[dict[str, Any]] = Field(default_factory=list)


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {"ok": True, "dev_entitlement": settings.dev_entitlement, "stripe": bool(settings.stripe_secret_key)}


@app.post("/api/auth/register")
def register(body: RegisterBody, response: Response) -> dict[str, Any]:
    email = _email(body.email)
    user_id = secrets.token_hex(8)
    with db_session(settings.db_path) as conn:
        exists = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if exists:
            raise HTTPException(status_code=409, detail="An account with that email already exists")
        conn.execute(
            "INSERT INTO users (id, email, password_hash, created_at) VALUES (?,?,?,?)",
            (user_id, email, hash_password(body.password), iso()),
        )
        token = issue_token(conn, user_id, "web", "browser", 24 * 30)
        user = row_user(conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone())
    set_session_cookie(response, token)
    return {"token": token, "user": public_user(user)}


@app.post("/api/auth/login")
def login(body: LoginBody, response: Response) -> dict[str, Any]:
    email = _email(body.email)
    with db_session(settings.db_path) as conn:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if not row or not verify_password(body.password, row["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid email or password")
        kind = "device" if body.device_name else "web"
        token = issue_token(conn, row["id"], kind, body.device_name or "browser", 24 * 30)
        user = row_user(row)
    set_session_cookie(response, token)
    return {"token": token, "user": public_user(user)}


@app.post("/api/auth/magic-link")
def magic_link(body: MagicBody) -> dict[str, Any]:
    email = _email(body.email)
    with db_session(settings.db_path) as conn:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if not row:
            user_id = secrets.token_hex(8)
            conn.execute(
                "INSERT INTO users (id, email, password_hash, created_at) VALUES (?,?,?,?)",
                (user_id, email, None, iso()),
            )
        else:
            user_id = row["id"]
        token = issue_token(conn, user_id, "magic", "magic-link", 0.25)
    url = f"{settings.public_url}/api/auth/magic?token={token}"
    # Production should email this. Local/dev returns the URL so the flow is testable.
    return {"ok": True, "dev_url": url}


@app.get("/api/auth/magic")
def consume_magic(token: str, response: Response) -> Response:
    token_hash = hash_token(token, settings.secret)
    with db_session(settings.db_path) as conn:
        row = conn.execute(
            "SELECT * FROM auth_tokens WHERE token_hash = ? AND kind = 'magic'",
            (token_hash,),
        ).fetchone()
        if not row or (row["expires_at"] and row["expires_at"] < iso()):
            raise HTTPException(status_code=401, detail="Magic link expired")
        conn.execute("DELETE FROM auth_tokens WHERE token_hash = ?", (token_hash,))
        session_token = issue_token(conn, row["user_id"], "web", "browser", 24 * 30)
    redirect = Response(status_code=303)
    redirect.headers["Location"] = "/dashboard.html"
    set_session_cookie(redirect, session_token)
    return redirect


@app.post("/api/auth/logout")
def logout(request: Request, response: Response, authorization: str | None = Header(default=None)) -> dict[str, bool]:
    token = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
    token = token or request.cookies.get(COOKIE)
    if token:
        with db_session(settings.db_path) as conn:
            conn.execute("DELETE FROM auth_tokens WHERE token_hash = ?", (hash_token(token, settings.secret),))
    response.delete_cookie(COOKIE, path="/")
    return {"ok": True}


@app.post("/api/devices")
def create_device(
    body: DeviceBody, request: Request, authorization: str | None = Header(default=None)
) -> dict[str, str]:
    user = current_user(request, authorization)
    with db_session(settings.db_path) as conn:
        token = issue_token(conn, user["id"], "device", body.name, 24 * 90)
    return {"token": token, "name": body.name}


def public_user(user: dict[str, Any]) -> dict[str, Any]:
    entitlement = entitlements.entitlement_for_user(settings, user)
    with db_session(settings.db_path) as conn:
        persist_entitlement(conn, user["id"], entitlement)
    return {
        "id": user["id"],
        "email": user["email"],
        "entitlement": entitlement,
    }


@app.get("/api/me")
def me(request: Request, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    user = current_user(request, authorization)
    return public_user(user)


@app.get("/api/entitlement")
def get_entitlement(request: Request, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    user = current_user(request, authorization)
    result = entitlements.entitlement_for_user(settings, user)
    with db_session(settings.db_path) as conn:
        persist_entitlement(conn, user["id"], result)
    return result


@app.post("/api/billing/checkout")
def billing_checkout(
    body: CheckoutBody, request: Request, authorization: str | None = Header(default=None)
) -> dict[str, Any]:
    user = current_user(request, authorization)
    plan = body.plan.strip().casefold()
    if plan not in {"starter", "pro", "elite"}:
        raise HTTPException(status_code=400, detail="Plan must be starter, pro, or elite")
    try:
        session = entitlements.create_checkout_session(
            settings,
            plan=plan,
            user_id=user["id"],
            email=user["email"],
            customer_id=user.get("stripe_customer_id"),
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"url": session.get("url"), "id": session.get("id")}


@app.post("/api/billing/claim")
def billing_claim(
    body: ClaimBody, request: Request, authorization: str | None = Header(default=None)
) -> dict[str, Any]:
    user = current_user(request, authorization)
    try:
        checkout = entitlements.retrieve_checkout_session(settings, body.session_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    email = ((checkout.get("customer_details") or {}).get("email") or checkout.get("customer_email") or "").casefold()
    ref = checkout.get("client_reference_id")
    if ref and ref != user["id"] and email and email != user["email"]:
        raise HTTPException(status_code=403, detail="Checkout session belongs to another account")
    customer = checkout.get("customer")
    customer_id = customer if isinstance(customer, str) else (customer or {}).get("id")
    if customer_id:
        with db_session(settings.db_path) as conn:
            conn.execute("UPDATE users SET stripe_customer_id = ? WHERE id = ?", (customer_id, user["id"]))
        user["stripe_customer_id"] = customer_id
    result = entitlements.entitlement_for_user(settings, user)
    if checkout.get("payment_status") == "paid" and not result.get("active"):
        result = {
            "active": True,
            "plan": (checkout.get("metadata") or {}).get("plan") or "starter",
            "customer_id": customer_id,
            "reason": "checkout_paid",
        }
    with db_session(settings.db_path) as conn:
        persist_entitlement(conn, user["id"], result)
    return result


@app.post("/api/billing/portal")
def billing_portal(request: Request, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    user = current_user(request, authorization)
    if not user.get("stripe_customer_id"):
        raise HTTPException(status_code=400, detail="No Stripe customer on this account yet")
    try:
        portal = entitlements.create_portal_session(settings, user["stripe_customer_id"])
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"url": portal.get("url")}


@app.post("/api/webhooks/stripe")
async def stripe_webhook(request: Request, stripe_signature: str | None = Header(default=None, alias="Stripe-Signature")):
    payload = await request.body()
    if not settings.stripe_webhook_secret:
        raise HTTPException(status_code=503, detail="STRIPE_WEBHOOK_SECRET is not set")
    try:
        from stripe import Webhook

        event = Webhook.construct_event(payload, stripe_signature, settings.stripe_webhook_secret)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Invalid webhook: {exc}") from exc

    obj = event.get("data", {}).get("object") or {}
    customer_id = obj.get("customer") if isinstance(obj.get("customer"), str) else None
    user_id = (obj.get("client_reference_id") or (obj.get("metadata") or {}).get("user_id"))
    if event["type"] in {
        "checkout.session.completed",
        "customer.subscription.updated",
        "customer.subscription.deleted",
        "customer.subscription.created",
    }:
        with db_session(settings.db_path) as conn:
            row = None
            if user_id:
                row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
            if not row and customer_id:
                row = conn.execute("SELECT * FROM users WHERE stripe_customer_id = ?", (customer_id,)).fetchone()
            email = ((obj.get("customer_details") or {}).get("email") or obj.get("customer_email") or "").casefold()
            if not row and email:
                row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
            if row:
                if customer_id:
                    conn.execute("UPDATE users SET stripe_customer_id = ? WHERE id = ?", (customer_id, row["id"]))
                user = row_user(row)
                user["stripe_customer_id"] = customer_id or user.get("stripe_customer_id")
                result = entitlements.entitlement_for_user(settings, user)
                persist_entitlement(conn, row["id"], result)
    return {"ok": True}


@app.get("/api/download")
def download(request: Request, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    user = current_user(request, authorization)
    require_entitlement(user)
    return {"url": settings.download_url}


def _best_lap(conn, user_id: str, track: str, car: str) -> float | None:
    row = conn.execute(
        "SELECT lap_time_s FROM best_laps WHERE user_id = ? AND track = ? AND car = ?",
        (user_id, track, car),
    ).fetchone()
    return float(row["lap_time_s"]) if row else None


@app.post("/api/overlay/sync")
def overlay_sync(
    body: SyncBody, request: Request, authorization: str | None = Header(default=None)
) -> dict[str, Any]:
    user = current_user(request, authorization)
    require_entitlement(user)
    session_meta = body.session
    reference = body.reference
    track = session_meta.get("track") or ""
    car = session_meta.get("car") or ""
    cfg = score_config()
    session_id = secrets.token_hex(8)
    events: list[dict[str, Any]] = []
    cards: list[dict[str, Any]] = []
    seen_titles: set[str] = set()
    best_this = None

    with db_session(settings.db_path) as conn:
        previous = _best_lap(conn, user["id"], track, car)
        running_best = previous
        for lap in body.laps:
            samples = lap.get("samples") or []
            result = score_session(
                session_track=track,
                session_car=car,
                ref_track=reference.get("track") or track,
                ref_car=reference.get("car") or car,
                ref_source=reference.get("source") or session_meta.get("reference_source") or "",
                samples=samples,
                markers=reference.get("markers") or [],
                lap_time_s=lap.get("lap_time_s"),
                previous_best_s=running_best,
                valid_lap=bool(lap.get("valid", True)),
                config=cfg,
            )
            if result.rejected:
                continue
            for event in result.events:
                events.append(event.__dict__)
            lap_time = lap.get("lap_time_s")
            if lap.get("valid", True) and lap_time:
                best_this = lap_time if best_this is None else min(best_this, lap_time)
                if running_best is None or lap_time < running_best:
                    running_best = lap_time
            if samples and reference.get("samples"):
                for card in analyze(
                    session_track=track,
                    session_car=car,
                    ref_track=reference.get("track") or track,
                    ref_car=reference.get("car") or car,
                    ref_source=reference.get("source") or "",
                    driver_samples=samples,
                    ref_samples=reference.get("samples") or [],
                    markers=reference.get("markers") or [],
                ):
                    payload = card.__dict__
                    if payload["title"] in seen_titles:
                        continue
                    seen_titles.add(payload["title"])
                    cards.append(payload)

        now = iso()
        conn.execute(
            """
            INSERT INTO training_sessions
            (id, user_id, track, car, started_at, ended_at, best_lap_s, reference_source, bind_ok, summary_json)
            VALUES (?,?,?,?,?,?,?,?,?,?)
            """,
            (
                session_id,
                user["id"],
                track,
                car,
                session_meta.get("started_at") or now,
                now,
                best_this,
                reference.get("source"),
                1 if events else 0,
                json.dumps({"laps": len(body.laps), "points": sum(e["points"] for e in events)}),
            ),
        )
        if running_best is not None:
            conn.execute(
                """
                INSERT INTO best_laps (user_id, track, car, lap_time_s, session_id, updated_at)
                VALUES (?,?,?,?,?,?)
                ON CONFLICT(user_id, track, car) DO UPDATE SET
                    lap_time_s = excluded.lap_time_s,
                    session_id = excluded.session_id,
                    updated_at = excluded.updated_at
                WHERE excluded.lap_time_s < best_laps.lap_time_s
                """,
                (user["id"], track, car, running_best, session_id, now),
            )
        for event in events:
            conn.execute(
                "INSERT INTO point_events (id, user_id, session_id, kind, points, detail, created_at) VALUES (?,?,?,?,?,?,?)",
                (secrets.token_hex(8), user["id"], session_id, event["kind"], event["points"], event["detail"], now),
            )
        for card in cards:
            conn.execute(
                "INSERT INTO coaching_cards (id, user_id, session_id, title, body, tone, created_at) VALUES (?,?,?,?,?,?,?)",
                (secrets.token_hex(8), user["id"], session_id, card["title"], card["body"], card["tone"], now),
            )

    return {
        "session_id": session_id,
        "points_awarded": sum(e["points"] for e in events),
        "events": events,
        "coaching": cards,
    }


@app.get("/api/dashboard")
def dashboard(request: Request, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    user = current_user(request, authorization)
    entitlement = entitlements.entitlement_for_user(settings, user)
    with db_session(settings.db_path) as conn:
        persist_entitlement(conn, user["id"], entitlement)
        points_row = conn.execute(
            "SELECT COALESCE(SUM(points), 0) AS total FROM point_events WHERE user_id = ?",
            (user["id"],),
        ).fetchone()
        sessions = [
            dict(r)
            for r in conn.execute(
                """
                SELECT id, track, car, started_at, best_lap_s, reference_source
                FROM training_sessions WHERE user_id = ?
                ORDER BY started_at DESC LIMIT 12
                """,
                (user["id"],),
            ).fetchall()
        ]
        bests = [
            dict(r)
            for r in conn.execute(
                "SELECT track, car, lap_time_s, updated_at FROM best_laps WHERE user_id = ? ORDER BY updated_at DESC",
                (user["id"],),
            ).fetchall()
        ]
        events = [
            dict(r)
            for r in conn.execute(
                """
                SELECT kind, points, detail, created_at FROM point_events
                WHERE user_id = ? ORDER BY created_at DESC LIMIT 20
                """,
                (user["id"],),
            ).fetchall()
        ]
        cards = [
            dict(r)
            for r in conn.execute(
                """
                SELECT title, body, tone, created_at FROM coaching_cards
                WHERE user_id = ? ORDER BY created_at DESC LIMIT 8
                """,
                (user["id"],),
            ).fetchall()
        ]
    return {
        "user": {"email": user["email"], "id": user["id"]},
        "entitlement": entitlement,
        "points_total": int(points_row["total"]),
        "sessions": sessions,
        "best_laps": bests,
        "point_events": events,
        "coaching": cards,
    }


@app.post("/api/demo/session")
def demo_session(request: Request, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    """Local/demo: drive the catalog_sample through the same overlay engine + sync path."""
    user = current_user(request, authorization)
    require_entitlement(user)
    aid = TrainingAid(score_config())
    aid.bind_session(SAMPLE_TRACK, SAMPLE_CAR)
    aid.set_reference(SAMPLE_TRACK, SAMPLE_CAR, SAMPLE_SOURCE, SAMPLE_MARKERS, reference_samples())
    for sample in driver_slow_samples():
        aid.tick(sample["d"], sample["v"], sample["b"], sample["t"])
    aid.end_lap(83.200, valid=True)
    for sample in driver_fast_samples():
        aid.tick(sample["d"], sample["v"], sample["b"], sample["t"])
    aid.end_lap(82.100, valid=True)
    payload = aid.flush_payload()
    result = overlay_sync(SyncBody(**payload), request, authorization)
    result["hud"] = aid.hud.snapshot()
    return result


@app.get("/api/config")
def public_config() -> dict[str, Any]:
    return {
        "public_url": settings.public_url,
        "dev_entitlement": settings.dev_entitlement,
        "stripe_configured": bool(settings.stripe_secret_key),
        "plans": {
            "starter": {"price": "$5.99", "price_id_set": bool(settings.price_starter)},
            "pro": {"price": "$9.99", "price_id_set": bool(settings.price_pro)},
            "elite": {"price": "$18.99", "price_id_set": bool(settings.price_elite)},
        },
    }


app.mount("/", StaticFiles(directory=str(ROOT), html=True), name="site")
