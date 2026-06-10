"""Unit tests for the cap-aware optimization engine: python -m pytest test_engine.py"""

from engine import allocate_category, evaluate_wallet, normalize_category, recommend_additions


def make_card(name, rates, fee=0, pv=1.0, currency="Cashback"):
    earn = {
        cat: {
            "multiplier": spec[0],
            "cap_amount": spec[1] if len(spec) > 1 else None,
            "cap_period": spec[2] if len(spec) > 2 else None,
            "is_rotating": False,
            "notes": None,
        }
        for cat, spec in rates.items()
    }
    earn.setdefault("Other", {"multiplier": 1.0, "cap_amount": None, "cap_period": None, "is_rotating": False, "notes": None})
    return {
        "name": name,
        "issuer": "Test",
        "annual_fee": fee,
        "reward_currency": currency,
        "point_value_cents": pv,
        "earn_rates": earn,
        "signup_bonus": None,
        "credits_notes": None,
        "as_of": None,
    }


def test_normalize_category():
    assert normalize_category("Restaurants") == "Dining"
    assert normalize_category(" GAS ") == "Gas"
    assert normalize_category("Crypto") == "Other"


def test_uncapped_allocation_picks_best_card():
    a = make_card("A", {"Dining": (3,)})
    b = make_card("B", {"Dining": (4,)})
    result = allocate_category(100, "Dining", [a, b])
    assert result["points"] == 400
    assert result["allocation"][0]["card"] == "B"


def test_cap_spills_to_next_best_tier():
    # 5x capped at $500/mo, then a 2x catch-all should absorb the rest.
    capped = make_card("Capped5x", {"Groceries": (5, 500, "monthly")})
    flat = make_card("Flat2x", {"Other": (2,)})
    result = allocate_category(800, "Groceries", [capped, flat])
    assert result["points"] == 500 * 5 + 300 * 2
    assert [s["card"] for s in result["allocation"]] == ["Capped5x", "Flat2x"]


def test_quarterly_cap_normalized_to_monthly():
    # $1,500/quarter -> $500/month capacity at the bonus rate.
    rotating = make_card("Rotating", {"Gas": (5, 1500, "quarterly")})
    result = allocate_category(600, "Gas", [rotating])
    assert result["points"] == 500 * 5 + 100 * 1


def test_point_value_beats_raw_multiplier():
    # 2x at 2.05 cents/pt (4.1c/$) should beat 4x at 1 cent/pt (4.0c/$).
    cash = make_card("Cash4x", {"Dining": (4,)}, pv=1.0)
    points = make_card("Points2x", {"Dining": (2,)}, pv=2.05, currency="Points")
    result = allocate_category(100, "Dining", [cash, points])
    assert result["allocation"][0]["card"] == "Points2x"


def test_evaluate_wallet_fees_and_totals():
    card = make_card("Feecard", {"Dining": (4,)}, fee=120)
    result = evaluate_wallet({"Dining": 100, "Other": 50}, [card])
    assert result["points"] == 450
    assert result["monthly_fees"] == 10
    assert abs(result["net_value_usd"] - (4.50 - 10)) < 1e-9


def test_recommendations_ranked_by_net_gain():
    base = make_card("Base1x", {})
    grocery = make_card("Grocery6x", {"Groceries": (6,)}, fee=0)
    pricey = make_card("Pricey6x", {"Groceries": (6,)}, fee=600)
    recs = recommend_additions({"Groceries": 1000}, [base], [base, grocery, pricey])
    assert recs[0]["card"]["name"] == "Grocery6x"
    assert recs[0]["net_gain_monthly"] > recs[1]["net_gain_monthly"]
    # Both add the same gross value; the fee separates them.
    assert abs(recs[0]["gross_gain_monthly"] - recs[1]["gross_gain_monthly"]) < 1e-9
