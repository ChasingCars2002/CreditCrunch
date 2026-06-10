"""Seed (or refresh) the Supabase rewards matrix from data/cards.json.

Usage:
    SUPABASE_SERVICE_ROLE_KEY=... python seed_supabase.py

Writes require the service role key (RLS only allows public reads). The
script replaces each card's earn rates wholesale, so data/cards.json is the
single source of truth for updates.
"""

import json
import os
import sys
from pathlib import Path

import requests

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://aacvmspwrhelpziniimo.supabase.co")
SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not SERVICE_KEY:
    sys.exit("Set SUPABASE_SERVICE_ROLE_KEY (Supabase dashboard → Settings → API keys).")

HEADERS = {
    "apikey": SERVICE_KEY,
    "Authorization": f"Bearer {SERVICE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation,resolution=merge-duplicates",
}


def main():
    cards = json.loads((Path(__file__).parent / "data" / "cards.json").read_text())

    for card in cards:
        sub = card.get("signup_bonus") or {}
        row = {
            "name": card["name"],
            "issuer": card["issuer"],
            "annual_fee": card["annual_fee"],
            "reward_currency": card["reward_currency"],
            "point_value_cents": card["point_value_cents"],
            "signup_bonus_amount": sub.get("amount"),
            "signup_bonus_unit": sub.get("unit"),
            "signup_bonus_min_spend": sub.get("min_spend"),
            "signup_bonus_window_days": sub.get("window_days"),
            "signup_bonus_value_usd": sub.get("estimated_value_usd"),
            "credits_notes": card.get("credits_notes"),
            "source_urls": card.get("source_urls"),
            "as_of": (card.get("as_of") or "2026-06") + "-01",
            "is_active": True,
            "updated_at": "now()",
        }
        resp = requests.post(
            f"{SUPABASE_URL}/rest/v1/cards?on_conflict=name",
            headers=HEADERS,
            json=row,
            timeout=15,
        )
        resp.raise_for_status()
        card_id = resp.json()[0]["id"]

        requests.delete(
            f"{SUPABASE_URL}/rest/v1/earn_rates?card_id=eq.{card_id}",
            headers=HEADERS,
            timeout=15,
        ).raise_for_status()

        rates = [
            {
                "card_id": card_id,
                "category": r["category"],
                "multiplier": r["multiplier"],
                "cap_amount": r.get("cap_amount"),
                "cap_period": r.get("cap_period"),
                "is_rotating": bool(r.get("is_rotating", False)),
                "notes": r.get("notes"),
            }
            for r in card["earn_rates"]
        ]
        requests.post(
            f"{SUPABASE_URL}/rest/v1/earn_rates",
            headers=HEADERS,
            json=rates,
            timeout=15,
        ).raise_for_status()

        print(f"Seeded {card['name']} ({len(rates)} earn rates)")

    print(f"\nDone — {len(cards)} cards seeded.")


if __name__ == "__main__":
    main()
