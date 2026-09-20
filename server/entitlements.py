"""Stripe subscription entitlement for download + cloud training sync."""

from __future__ import annotations

import secrets
from typing import Any

from .config import Settings

ACTIVE_STATUSES = frozenset({"active", "trialing", "past_due"})
TIER_ORDER = {"starter": 1, "pro": 2, "elite": 3}


def _client(settings: Settings):
    if not settings.stripe_secret_key:
        return None
    from stripe import StripeClient

    return StripeClient(settings.stripe_secret_key)


def _obj(value: Any) -> Any:
    if hasattr(value, "to_dict"):
        return value.to_dict()
    return value


def _get(value: Any, key: str, default=None):
    if value is None:
        return default
    if isinstance(value, dict):
        return value.get(key, default)
    return getattr(value, key, default)


def plan_from_product(product: Any) -> str | None:
    data = _obj(product) or {}
    meta = _get(data, "metadata") or {}
    if isinstance(meta, dict) and meta.get("tier"):
        return str(meta["tier"]).casefold()
    name = str(_get(data, "name") or "").casefold()
    for tier in ("elite", "pro", "starter"):
        if tier in name:
            return tier
    return None


def price_id_for_plan(settings: Settings, plan: str) -> str:
    mapping = {
        "starter": settings.price_starter,
        "pro": settings.price_pro,
        "elite": settings.price_elite,
    }
    price = mapping.get(plan)
    if not price:
        raise ValueError(f"Unknown plan {plan}")
    return price


def check_customer_entitlement(settings: Settings, customer_id: str) -> dict[str, Any]:
    client = _client(settings)
    if client is None:
        return {"active": False, "plan": None, "customer_id": customer_id, "reason": "stripe_unconfigured"}

    listed = client.v1.subscriptions.list(params={"customer": customer_id, "status": "all", "limit": 20})
    data = _get(_obj(listed), "data") or []
    best_plan = None
    best_rank = 0
    matched = None
    for sub in data:
        sub = _obj(sub)
        status = _get(sub, "status")
        if status not in ACTIVE_STATUSES:
            continue
        items = _get(_get(sub, "items"), "data") or []
        plan = None
        for item in items:
            item = _obj(item)
            price = _obj(_get(item, "price") or {})
            product = _get(price, "product")
            if isinstance(product, str):
                try:
                    product = _obj(client.v1.products.retrieve(product))
                except Exception:
                    product = {"id": product}
            plan = plan_from_product(product) or plan
        rank = TIER_ORDER.get(plan or "", 1)
        if rank >= best_rank:
            best_rank = rank
            best_plan = plan or "starter"
            matched = sub
    if not matched:
        return {"active": False, "plan": None, "customer_id": customer_id, "reason": "no_active_subscription"}
    return {
        "active": True,
        "plan": best_plan,
        "customer_id": customer_id,
        "subscription_id": _get(matched, "id"),
        "status": _get(matched, "status"),
        "reason": "subscription",
    }


def find_customer_id(settings: Settings, email: str) -> str | None:
    client = _client(settings)
    if client is None:
        return None
    listed = client.v1.customers.list(params={"email": email, "limit": 5})
    data = _get(_obj(listed), "data") or []
    if not data:
        return None
    return _get(_obj(data[0]), "id")


def retrieve_checkout_session(settings: Settings, session_id: str) -> dict[str, Any]:
    client = _client(settings)
    if client is None:
        raise RuntimeError("Stripe is not configured")
    session = client.v1.checkout.sessions.retrieve(
        session_id,
        params={"expand": ["subscription", "customer"]},
    )
    return _obj(session)


def create_checkout_session(
    settings: Settings,
    *,
    plan: str,
    user_id: str,
    email: str,
    customer_id: str | None,
) -> dict[str, Any]:
    client = _client(settings)
    if client is None:
        raise RuntimeError("Stripe is not configured")
    price = price_id_for_plan(settings, plan)
    suffix = "".join(secrets.choice("abcdefghijklmnopqrstuvwxyz") for _ in range(8))
    params: dict[str, Any] = {
        "mode": "subscription",
        "line_items": [{"price": price, "quantity": 1}],
        "success_url": f"{settings.public_url}/download.html?session_id={{CHECKOUT_SESSION_ID}}",
        "cancel_url": f"{settings.public_url}/pricing.html",
        "client_reference_id": user_id,
        "metadata": {"user_id": user_id, "plan": plan},
        "integration_identifier": f"lapsimpro_dash_{suffix}",
    }
    if customer_id:
        params["customer"] = customer_id
    else:
        params["customer_email"] = email
    session = client.v1.checkout.sessions.create(params=params)
    return _obj(session)


def create_portal_session(settings: Settings, customer_id: str) -> dict[str, Any]:
    client = _client(settings)
    if client is None:
        raise RuntimeError("Stripe is not configured")
    session = client.v1.billing_portal.sessions.create(
        params={"customer": customer_id, "return_url": f"{settings.public_url}/account.html"}
    )
    return _obj(session)


def entitlement_for_user(settings: Settings, user: dict[str, Any]) -> dict[str, Any]:
    if settings.dev_entitlement:
        return {
            "active": True,
            "plan": user.get("plan") or "starter",
            "customer_id": user.get("stripe_customer_id"),
            "reason": "dev",
        }
    if not settings.stripe_secret_key:
        return {
            "active": bool(user.get("entitlement_active")),
            "plan": user.get("plan"),
            "customer_id": user.get("stripe_customer_id"),
            "reason": "cached_or_unconfigured",
        }
    customer_id = user.get("stripe_customer_id") or find_customer_id(settings, user["email"])
    if not customer_id:
        return {"active": False, "plan": None, "customer_id": None, "reason": "no_stripe_customer"}
    return check_customer_entitlement(settings, customer_id)
