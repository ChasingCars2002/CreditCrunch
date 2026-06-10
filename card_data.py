"""Load the CreditCrunch rewards matrix from Supabase, falling back to the
bundled JSON snapshot when the network or credentials are unavailable."""

import json
import os
from pathlib import Path

import requests

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://aacvmspwrhelpziniimo.supabase.co")
# Anon key: read-only access enforced by RLS, safe to ship with the client.
SUPABASE_ANON_KEY = os.environ.get(
    "SUPABASE_ANON_KEY",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFhY3Ztc3B3cmhlbHB6aW5paW1vIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODExMTc3MzgsImV4cCI6MjA5NjY5MzczOH0.uej8hR_F4pQW8P_R2xVUKmP8qAByXaE1kO_1qYWNA_U",
)

SNAPSHOT_PATH = Path(__file__).parent / "data" / "cards.json"


def _normalize(card: dict) -> dict:
    """Normalize a card record (Supabase row or JSON entry) to the app's shape."""
    rates = {}
    for r in card.get("earn_rates", []):
        rates[r["category"]] = {
            "multiplier": float(r["multiplier"]),
            "cap_amount": float(r["cap_amount"]) if r.get("cap_amount") is not None else None,
            "cap_period": r.get("cap_period"),
            "is_rotating": bool(r.get("is_rotating", False)),
            "notes": r.get("notes"),
        }
    if "Other" not in rates:
        rates["Other"] = {
            "multiplier": 1.0,
            "cap_amount": None,
            "cap_period": None,
            "is_rotating": False,
            "notes": None,
        }

    sub = card.get("signup_bonus")
    if sub is None and card.get("signup_bonus_amount") is not None:
        sub = {
            "amount": float(card["signup_bonus_amount"]),
            "unit": card.get("signup_bonus_unit") or "points",
            "min_spend": card.get("signup_bonus_min_spend"),
            "window_days": card.get("signup_bonus_window_days"),
            "estimated_value_usd": card.get("signup_bonus_value_usd"),
        }

    return {
        "name": card["name"],
        "issuer": card.get("issuer", ""),
        "annual_fee": float(card.get("annual_fee", 0)),
        "reward_currency": card.get("reward_currency", "Cashback"),
        "point_value_cents": float(card.get("point_value_cents", 1.0)),
        "earn_rates": rates,
        "signup_bonus": sub,
        "credits_notes": card.get("credits_notes"),
        "as_of": card.get("as_of"),
    }


def _load_from_supabase() -> list[dict]:
    resp = requests.get(
        f"{SUPABASE_URL}/rest/v1/cards",
        params={"select": "*,earn_rates(*)", "is_active": "eq.true", "order": "name"},
        headers={"apikey": SUPABASE_ANON_KEY, "Authorization": f"Bearer {SUPABASE_ANON_KEY}"},
        timeout=10,
    )
    resp.raise_for_status()
    rows = resp.json()
    if not rows:
        raise ValueError("Supabase returned no cards")
    return [_normalize(row) for row in rows]


def _load_from_snapshot() -> list[dict]:
    with open(SNAPSHOT_PATH) as f:
        return [_normalize(card) for card in json.load(f)]


def load_cards() -> tuple[list[dict], str]:
    """Return (cards, source) where source is 'supabase' or 'snapshot'."""
    try:
        return _load_from_supabase(), "supabase"
    except Exception:
        return _load_from_snapshot(), "snapshot"
