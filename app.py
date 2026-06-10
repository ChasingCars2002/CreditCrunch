import pandas as pd
import streamlit as st

# -------------------------------------------------------------
# 1. DATABASE OF POPULAR CREDIT CARDS (Multipliers & Fees)
# -------------------------------------------------------------
CARD_DATABASE = {
    "Amex Gold": {
        "Groceries": 4,
        "Dining": 4,
        "Travel": 3,
        "Gas": 1,
        "Other": 1,
        "Fee": 250,
    },
    "Chase Sapphire Preferred": {
        "Groceries": 1,
        "Dining": 3,
        "Travel": 2,
        "Gas": 1,
        "Other": 1,
        "Fee": 95,
    },
    "Citi Custom Cash": {
        "Groceries": 5,
        "Dining": 1,
        "Travel": 1,
        "Gas": 1,
        "Other": 1,
        "Fee": 0,
    },  # Simplification: 5x on top category
    "Capital One SavorOne": {
        "Groceries": 3,
        "Dining": 3,
        "Travel": 1,
        "Gas": 1,
        "Other": 1,
        "Fee": 0,
    },
    "Catch-All 2% Card (e.g., Citi Double Cash)": {
        "Groceries": 2,
        "Dining": 2,
        "Travel": 2,
        "Gas": 2,
        "Other": 2,
        "Fee": 0,
    },
}

# -------------------------------------------------------------
# 2. APP UI SETUP
# -------------------------------------------------------------
st.set_page_config(page_title="CreditCrunch - Credit Card Optimizer", layout="wide")
st.title("💳 CreditCrunch")
st.subheader("Optimize your spending. Maximize your points.")
st.write("---")

# Sidebar - User Inventory
st.sidebar.header("Your Current Wallet")
user_current_cards = st.sidebar.multiselect(
    "Select the cards you currently own:",
    options=list(CARD_DATABASE.keys()),
    default=["Chase Sapphire Preferred"],
)

point_value = st.sidebar.slider(
    "Estimated Point Value (Cents per Point)", 1.0, 2.0, 1.25, step=0.25
)

# -------------------------------------------------------------
# 3. FILE UPLOADER & PROCESSING
# -------------------------------------------------------------
uploaded_file = st.file_uploader(
    "Upload your credit card statement CSV", type=["csv"]
)

if uploaded_file is not None and len(user_current_cards) > 0:
    # Load and display data
    df = pd.read_csv(uploaded_file)
    st.success("CSV Successfully Loaded!")

    # Calculate Spend Breakdown
    spend_summary = df.groupby("Category")["Amount"].sum().reset_index()

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 📊 Your Spending Breakdown")
        st.dataframe(spend_summary.style.format({"Amount": "${:,.2f}"}))

    # -------------------------------------------------------------
    # 4. CALCULATION ENGINE
    # -------------------------------------------------------------
    # Calculate what they ACTUALLY earned with their current stack
    total_current_points = 0
    for idx, row in df.iterrows():
        cat = row["Category"]
        amt = row["Amount"]

        # Find the best multiplier among the user's CURRENT cards
        best_current_mult = max(
            [CARD_DATABASE[card].get(cat, 1) for card in user_current_cards]
        )
        total_current_points += amt * best_current_mult

    # Calculate what they COULD earn with the absolute optimal card in the DB for each category
    total_optimal_points = 0
    optimal_card_choices = []

    for idx, row in df.iterrows():
        cat = row["Category"]
        amt = row["Amount"]

        # Find the absolute best card in the database for this specific transaction
        best_db_card = max(
            CARD_DATABASE.keys(), key=lambda k: CARD_DATABASE[k].get(cat, 1)
        )
        best_db_mult = CARD_DATABASE[best_db_card].get(cat, 1)

        total_optimal_points += amt * best_db_mult
        optimal_card_choices.append(best_db_card)

    current_value = (total_current_points * (point_value / 100)) - sum(
        [CARD_DATABASE[c]["Fee"] / 12 for c in user_current_cards]
    )  # rough monthly fee offset
    optimal_value = total_optimal_points * (point_value / 100)

    # -------------------------------------------------------------
    # 5. RESULTS & RECOMMENDATIONS DASHBOARD
    # -------------------------------------------------------------
    with col2:
        st.markdown("### 🎯 Your CreditCrunch Metrics")

        # Score calculation (Current Points / Optimal Points)
        score = min(int((total_current_points / total_optimal_points) * 100), 100)
        st.metric(label="Optimization Score", value=f"{score}%")

        if score >= 90:
            st.balloons()
            st.success("Excellent! You are squeezing serious value out of your spend.")
        elif score >= 70:
            st.warning("Good, but you're leaving points on the table.")
        else:
            st.error("You are drastically under-earning on your daily spend!")

    st.write("---")
    st.markdown("### 💡 Recommended Strategy")

    rec_col1, rec_col2 = st.columns(2)

    with rec_col1:
        st.write(f"**Current Monthly Earnings:** {int(total_current_points):,} Points")
        st.write(f"**Potential Monthly Earnings:** {int(total_optimal_points):,} Points")

    with rec_col2:
        missed_points = int(total_optimal_points - total_current_points)
        st.write(f"❌ **Missed Points:** {missed_points:,} points per month")

        # Basic Recommendation Engine Logic
        df["Optimal_Card"] = optimal_card_choices
        top_suggested_card = (
            df[~df["Optimal_Card"].isin(user_current_cards)]["Optimal_Card"]
            .mode()
            .to_list()
        )

        if top_suggested_card:
            st.markdown(
                f"### ✨ Top Recommendation: Add **{top_suggested_card[0]}** to your wallet!"
            )
            st.write(
                f"This card matches your heavy spend categories perfectly based on your statement analysis."
            )
        else:
            st.markdown("### ✨ Your current stack is optimal for this statement period!")

elif len(user_current_cards) == 0:
    st.info("Please select at least one card in the sidebar to begin analysis.")
else:
    st.info("Please upload a transaction CSV file to see your optimization strategy.")
