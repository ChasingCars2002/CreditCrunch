import pandas as pd
import streamlit as st

from card_data import load_cards
from engine import evaluate_wallet, normalize_category, recommend_additions

st.set_page_config(page_title="CreditCrunch - Credit Card Optimizer", layout="wide")
st.title("💳 CreditCrunch")
st.subheader("Optimize your spending. Maximize your points.")
st.write("---")


@st.cache_data(ttl=3600)
def get_cards():
    return load_cards()


all_cards, data_source = get_cards()
cards_by_name = {c["name"]: c for c in all_cards}

# -------------------------------------------------------------
# SIDEBAR — wallet + preferences
# -------------------------------------------------------------
st.sidebar.header("Your Current Wallet")
user_current_cards = st.sidebar.multiselect(
    "Select the cards you currently own:",
    options=sorted(cards_by_name),
    default=["Chase Sapphire Preferred"] if "Chase Sapphire Preferred" in cards_by_name else [],
)

preference = st.sidebar.radio(
    "Reward preference for recommendations:",
    ["Both", "Cashback only", "Points & Miles only"],
)

if data_source == "supabase":
    st.sidebar.caption(f"📡 Live rewards matrix from Supabase · {len(all_cards)} cards")
else:
    st.sidebar.caption(f"📦 Offline snapshot (Supabase unreachable) · {len(all_cards)} cards")

wallet = [cards_by_name[name] for name in user_current_cards]

if preference == "Cashback only":
    candidates = [c for c in all_cards if c["reward_currency"] == "Cashback"]
elif preference == "Points & Miles only":
    candidates = [c for c in all_cards if c["reward_currency"] != "Cashback"]
else:
    candidates = all_cards

# -------------------------------------------------------------
# FILE UPLOADER & PROCESSING
# -------------------------------------------------------------
uploaded_file = st.file_uploader("Upload your credit card statement CSV", type=["csv"])

if uploaded_file is not None and wallet:
    df = pd.read_csv(uploaded_file)
    st.success("CSV Successfully Loaded!")

    df["Reward Category"] = df["Category"].map(normalize_category)
    spend_by_category = df.groupby("Reward Category")["Amount"].sum().to_dict()

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 📊 Your Spending Breakdown")
        spend_summary = (
            df.groupby("Reward Category")["Amount"].sum().reset_index()
            .sort_values("Amount", ascending=False)
        )
        st.dataframe(spend_summary.style.format({"Amount": "${:,.2f}"}), hide_index=True)
        st.bar_chart(spend_summary.set_index("Reward Category")["Amount"])

    # -------------------------------------------------------------
    # CALCULATION ENGINE (cap-aware)
    # -------------------------------------------------------------
    current = evaluate_wallet(spend_by_category, wallet)
    # Optimal = best achievable using any cards in the matrix (respecting caps),
    # filtered by the user's reward preference.
    optimal = evaluate_wallet(spend_by_category, candidates)

    with col2:
        st.markdown("### 🎯 Your CreditCrunch Metrics")
        score = min(int((current["value_usd"] / optimal["value_usd"]) * 100), 100) if optimal["value_usd"] else 100
        st.metric(label="Optimization Score", value=f"{score}%")

        m1, m2, m3 = st.columns(3)
        m1.metric("Current Value / mo", f"${current['value_usd']:,.2f}")
        m2.metric("Optimal Value / mo", f"${optimal['value_usd']:,.2f}")
        m3.metric(
            "Missed Value / mo",
            f"${optimal['value_usd'] - current['value_usd']:,.2f}",
            delta=f"-${(optimal['value_usd'] - current['value_usd']) * 12:,.0f}/yr",
            delta_color="inverse",
        )
        st.caption(
            f"Current wallet annual fees: ${current['monthly_fees'] * 12:,.0f}/yr "
            f"(${current['monthly_fees']:,.2f}/mo)"
        )

        if score >= 90:
            st.balloons()
            st.success("Excellent! You are squeezing serious value out of your spend.")
        elif score >= 70:
            st.warning("Good, but you're leaving points on the table.")
        else:
            st.error("You are drastically under-earning on your daily spend!")

    st.write("---")
    st.markdown("### 💡 Recommended Strategy")

    recs = recommend_additions(spend_by_category, wallet, candidates, top_n=3)
    recs = [r for r in recs if r["gross_gain_monthly"] > 0.005]

    if not recs:
        st.success("✨ Your current stack is already optimal for this statement period!")
    else:
        for i, rec in enumerate(recs):
            card = rec["card"]
            with st.container(border=True):
                header = f"{'✨ Top Recommendation' if i == 0 else f'#{i + 1}'}: **{card['name']}**"
                st.markdown(header)
                fee_label = f"${card['annual_fee']:,.0f}/yr fee" if card["annual_fee"] else "no annual fee"
                st.write(
                    f"Adding this card earns you **${rec['gross_gain_monthly']:,.2f}/mo** more "
                    f"(**${rec['net_gain_monthly'] * 12:,.2f}/yr** after its {fee_label})."
                )
                sub = card.get("signup_bonus")
                if sub and sub.get("estimated_value_usd"):
                    st.write(
                        f"🎁 Current sign-up bonus: **{sub['amount']:,.0f} {sub['unit']}** "
                        f"(~${sub['estimated_value_usd']:,.0f}) after spending "
                        f"${sub.get('min_spend') or 0:,.0f} in {sub.get('window_days') or 90} days."
                    )
                if card.get("credits_notes"):
                    st.caption(card["credits_notes"])

    # -------------------------------------------------------------
    # CARD-PER-CATEGORY CHEAT SHEET
    # -------------------------------------------------------------
    st.write("---")
    st.markdown("### 🗂️ Which card to pull out (your current wallet)")
    rows = []
    for category, result in sorted(current["by_category"].items()):
        for slice_ in result["allocation"]:
            rows.append(
                {
                    "Category": category,
                    "Use Card": slice_["card"],
                    "Earn Rate": f"{slice_['multiplier']:g}x",
                    "Monthly Spend": slice_["amount"],
                }
            )
    cheat = pd.DataFrame(rows)
    st.dataframe(cheat.style.format({"Monthly Spend": "${:,.2f}"}), hide_index=True)
    st.caption(
        "When a category shows two cards, the first card's bonus cap runs out "
        "mid-month — switch to the second card after that."
    )

elif not wallet:
    st.info("Please select at least one card in the sidebar to begin analysis.")
else:
    st.info("Please upload a transaction CSV file to see your optimization strategy.")

# -------------------------------------------------------------
# CARD DATABASE EXPLORER
# -------------------------------------------------------------
with st.expander("🔍 Browse the full card database"):
    rows = []
    for card in all_cards:
        bonus_rates = ", ".join(
            f"{cat} {r['multiplier']:g}x" + (" (rotating)" if r["is_rotating"] else "")
            for cat, r in sorted(card["earn_rates"].items())
            if cat != "Other" and r["multiplier"] > card["earn_rates"]["Other"]["multiplier"]
        )
        sub = card.get("signup_bonus")
        rows.append(
            {
                "Card": card["name"],
                "Issuer": card["issuer"],
                "Annual Fee": card["annual_fee"],
                "Currency": card["reward_currency"],
                "Bonus Categories": bonus_rates or "—",
                "Base Rate": f"{card['earn_rates']['Other']['multiplier']:g}x",
                "Sign-Up Bonus": (
                    f"{sub['amount']:,.0f} {sub['unit']} (~${sub['estimated_value_usd']:,.0f})"
                    if sub and sub.get("estimated_value_usd")
                    else "—"
                ),
                "Data As Of": card.get("as_of") or "—",
            }
        )
    st.dataframe(
        pd.DataFrame(rows).style.format({"Annual Fee": "${:,.0f}"}),
        hide_index=True,
    )
