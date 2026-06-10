"""Cap-aware rewards optimization engine.

All calculations assume the uploaded statement covers roughly one month of
spending; category caps are normalized to a monthly capacity (quarterly / 3,
annual / 12) so bonus rates stop applying once a card's cap is exhausted and
spend spills over to the next-best available rate.
"""

CAP_PERIOD_MONTHS = {"monthly": 1, "quarterly": 3, "annual": 12}

# Map common bank-statement category labels onto the reward categories used
# by the card matrix. Unknown labels fall back to "Other".
CATEGORY_SYNONYMS = {
    "dining": "Dining",
    "restaurants": "Dining",
    "restaurant": "Dining",
    "food & drink": "Dining",
    "groceries": "Groceries",
    "grocery": "Groceries",
    "supermarkets": "Groceries",
    "gas": "Gas",
    "gasoline": "Gas",
    "fuel": "Gas",
    "travel": "Travel",
    "airlines": "Travel",
    "hotels": "Travel",
    "transit": "Transit",
    "commuting": "Transit",
    "rideshare": "Transit",
    "streaming": "Streaming",
    "entertainment": "Streaming",
    "drugstores": "Drugstores",
    "pharmacy": "Drugstores",
    "online retail": "Online Retail",
    "online shopping": "Online Retail",
    "amazon": "Online Retail",
    "rent": "Rent",
    "other": "Other",
    "shopping": "Other",
    "utilities": "Other",
}


def normalize_category(raw: str) -> str:
    return CATEGORY_SYNONYMS.get(str(raw).strip().lower(), "Other")


def _monthly_capacity(rate: dict) -> float:
    if rate["cap_amount"] is None:
        return float("inf")
    return rate["cap_amount"] / CAP_PERIOD_MONTHS.get(rate["cap_period"] or "monthly", 1)


def allocate_category(spend: float, category: str, cards: list[dict]) -> dict:
    """Greedily allocate a category's spend across cards by value per dollar.

    Each card contributes a bonus tier (its category rate, limited by any cap)
    and an uncapped base tier (its "Other" rate). Tiers are filled best-first,
    which is optimal because tier capacities are independent.
    """
    tiers = []
    for card in cards:
        base = card["earn_rates"]["Other"]
        rate = card["earn_rates"].get(category)
        if rate is not None and rate["multiplier"] > base["multiplier"]:
            tiers.append(
                {
                    "card": card,
                    "multiplier": rate["multiplier"],
                    "capacity": _monthly_capacity(rate),
                    "cents_per_dollar": rate["multiplier"] * card["point_value_cents"],
                }
            )
        tiers.append(
            {
                "card": card,
                "multiplier": base["multiplier"],
                "capacity": float("inf"),
                "cents_per_dollar": base["multiplier"] * card["point_value_cents"],
            }
        )

    tiers.sort(key=lambda t: t["cents_per_dollar"], reverse=True)

    remaining = spend
    value_usd = 0.0
    points = 0.0
    allocation = []
    for tier in tiers:
        if remaining <= 0:
            break
        amount = min(remaining, tier["capacity"])
        if amount <= 0:
            continue
        value_usd += amount * tier["cents_per_dollar"] / 100
        points += amount * tier["multiplier"]
        allocation.append(
            {
                "card": tier["card"]["name"],
                "amount": amount,
                "multiplier": tier["multiplier"],
            }
        )
        remaining -= amount

    return {"value_usd": value_usd, "points": points, "allocation": allocation}


def evaluate_wallet(spend_by_category: dict[str, float], cards: list[dict]) -> dict:
    """Total monthly reward value of a wallet against a spend profile."""
    total_value = 0.0
    total_points = 0.0
    by_category = {}
    for category, spend in spend_by_category.items():
        result = allocate_category(spend, category, cards)
        total_value += result["value_usd"]
        total_points += result["points"]
        by_category[category] = result

    monthly_fees = sum(c["annual_fee"] for c in cards) / 12
    return {
        "value_usd": total_value,
        "points": total_points,
        "net_value_usd": total_value - monthly_fees,
        "monthly_fees": monthly_fees,
        "by_category": by_category,
    }


def recommend_additions(
    spend_by_category: dict[str, float],
    wallet: list[dict],
    candidates: list[dict],
    top_n: int = 3,
) -> list[dict]:
    """Rank non-owned cards by net monthly gain when added to the wallet."""
    baseline = evaluate_wallet(spend_by_category, wallet)["value_usd"] if wallet else 0.0
    owned = {c["name"] for c in wallet}

    results = []
    for card in candidates:
        if card["name"] in owned:
            continue
        with_card = evaluate_wallet(spend_by_category, wallet + [card])["value_usd"]
        gross_gain = with_card - baseline
        net_gain = gross_gain - card["annual_fee"] / 12
        results.append(
            {
                "card": card,
                "gross_gain_monthly": gross_gain,
                "net_gain_monthly": net_gain,
            }
        )

    results.sort(key=lambda r: r["net_gain_monthly"], reverse=True)
    return results[:top_n]
