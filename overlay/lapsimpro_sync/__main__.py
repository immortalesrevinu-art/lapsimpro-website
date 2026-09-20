from __future__ import annotations

import argparse
import json
import os
import sys
from getpass import getpass

from .catalog_sample import (
    CAR,
    MARKERS,
    REF_SOURCE,
    TRACK,
    driver_fast_samples,
    driver_slow_samples,
    reference_samples,
)
from .client import AccountClient
from .engine import TrainingAid
from .store import clear_session, load_session


def _api_url(args: argparse.Namespace) -> str:
    return (
        args.api
        or os.environ.get("LAPSIPRO_API_URL")
        or os.environ.get("LAPSIMPRO_API_URL")
        or os.environ.get("LAPSIMPRO_PUBLIC_URL")
        or "http://127.0.0.1:8787"
    ).rstrip("/")


def cmd_login(args: argparse.Namespace) -> int:
    email = args.email or input("Email: ").strip()
    password = args.password or getpass("Password: ")
    client = AccountClient(_api_url(args))
    data = client.login(email, password, device_name=args.device)
    print(f"Signed in as {data['user']['email']}")
    entitlement = data["user"].get("entitlement") or {}
    print(f"Entitlement: {entitlement.get('plan') or 'none'} active={entitlement.get('active')}")
    return 0


def cmd_status(_: argparse.Namespace) -> int:
    saved = load_session()
    if not saved:
        print("Not signed in.")
        return 1
    client = AccountClient(saved["api_url"], saved["token"])
    me = client.me()
    print(json.dumps(me, indent=2))
    return 0


def cmd_logout(_: argparse.Namespace) -> int:
    clear_session()
    print("Local overlay session cleared.")
    return 0


def _drive(aid: TrainingAid, samples: list[dict], lap_time: float) -> None:
    for sample in samples:
        aid.tick(sample["d"], sample["v"], sample["b"], sample["t"], on_track=True)
    aid.end_lap(lap_time, valid=True)


def cmd_replay(args: argparse.Namespace) -> int:
    client = AccountClient.from_saved()
    me = client.me()
    if not me.get("entitlement", {}).get("active") and not os.environ.get("LAPSIMPRO_DEV_ENTITLEMENT"):
        print("Active subscription required to sync training data.")
        return 2
    aid = TrainingAid()
    aid.bind_session(TRACK, CAR)
    reason = aid.set_reference(TRACK, CAR, REF_SOURCE, MARKERS, reference_samples())
    print(f"Bind: {reason}")
    _drive(aid, driver_slow_samples(), 83.200)
    _drive(aid, driver_fast_samples(), 82.100)
    payload = aid.flush_payload()
    result = client.sync(payload)
    print(json.dumps({"hud": aid.hud.snapshot(), "sync": result}, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m lapsimpro_sync")
    sub = parser.add_subparsers(dest="cmd", required=True)

    login = sub.add_parser("login", help="Sign the overlay into a lapsimpro.com account")
    login.add_argument("--email")
    login.add_argument("--password")
    login.add_argument("--api")
    login.add_argument("--device", default="overlay")
    login.set_defaults(func=cmd_login)

    status = sub.add_parser("status", help="Show saved account + entitlement")
    status.set_defaults(func=cmd_status)

    logout = sub.add_parser("logout", help="Forget the local device token")
    logout.set_defaults(func=cmd_logout)

    replay = sub.add_parser("replay", help="Score a catalog_sample session and sync it")
    replay.add_argument("--api")
    replay.set_defaults(func=cmd_replay)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except Exception as exc:  # noqa: BLE001 — CLI surface
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
