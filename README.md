# 💳 CreditCrunch

CreditCrunch is a smart credit card optimization tool that analyzes your real-world spending habits and matches them with the perfect card "stack" to maximize points, miles, or cashback.

Instead of guessing which card to pull out at the grocery store, CreditCrunch does the math — it looks at your actual transaction history and simulates how much more you could have earned.

## Features

- **CSV Uploader** — drag-and-drop your transaction history exported from your bank (Chase, Amex, Citi, etc.).
- **Live Rewards Matrix** — 24 popular cards with researched June 2026 earn rates, category caps, annual fees, and current sign-up bonuses, served from Supabase (with a bundled offline snapshot as fallback).
- **Cap-Aware Optimization Engine** — honors bonus-category spending caps (e.g., Citi Custom Cash's $500/month at 5%, Amex Blue Cash Preferred's $6,000/year at 6%) and spills excess spend to the next-best card; quarterly/annual caps are normalized to monthly capacity.
- **Per-Card Point Valuations** — a 2x Chase Ultimate Rewards point (~2.05¢) is correctly valued above 2% cashback, so comparisons are in real dollars, not raw multipliers.
- **Optimization Score (0–100%)** — your current wallet's dollar value vs. the best possible allocation across the whole matrix.
- **Missed Value Calculator** — dollars per month (and per year) left on the table.
- **Ranked Recommendations** — top 3 cards to add, ranked by net gain after annual fees, with current sign-up bonus details.
- **Wallet Cheat Sheet** — which card to pull out per category, including when to switch cards mid-month as caps run out.

## Quick Start

1. Make sure you have Python 3.9+ installed.
2. Install the dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Run the app:

   ```bash
   streamlit run app.py
   ```

4. In the sidebar, select the cards you currently own and your reward preference (cashback vs. points & miles).
5. Upload a transaction CSV — a sample file (`transactions.csv`) is included in this repo.

## CSV Format

The uploader expects a CSV with at least `Amount` and `Category` columns:

```csv
Date,Description,Amount,Category
2026-05-01,Whole Foods,150.00,Groceries
2026-05-02,Local Bistro,85.00,Dining
2026-05-04,ExxonMobil,45.00,Gas
2026-05-05,Delta Air Lines,350.00,Travel
```

Common bank category labels (Restaurants, Supermarkets, Gasoline, Rideshare, Pharmacy, …) are automatically mapped to the reward categories: `Dining`, `Groceries`, `Gas`, `Travel`, `Transit`, `Streaming`, `Drugstores`, `Online Retail`, `Rent`, `Other`.

## Architecture

| File | Purpose |
|------|---------|
| `app.py` | Streamlit dashboard |
| `engine.py` | Pure-Python cap-aware allocation, scoring, and recommendation logic |
| `card_data.py` | Loads the rewards matrix from Supabase; falls back to `data/cards.json` |
| `data/cards.json` | Offline snapshot of the matrix (also the seed source of truth) |
| `seed_supabase.py` | Pushes `data/cards.json` into Supabase (requires service-role key) |
| `test_engine.py` | Unit tests for the engine (`python -m pytest`) |

### Supabase Schema

Two tables behind row-level security (public read, service-role write):

- **`cards`** — name, issuer, annual fee, reward currency, point value (cents), sign-up bonus (amount/unit/min-spend/window/estimated value), perk notes, source URLs, data-as-of date.
- **`earn_rates`** — per-card category multipliers with `cap_amount`, `cap_period` (monthly/quarterly/annual), and an `is_rotating` flag for rotating-category cards.

### Updating Card Data

Rates and sign-up bonuses change constantly. To refresh:

1. Edit `data/cards.json` (each entry documents its `source_urls` and `as_of` date).
2. Run `SUPABASE_SERVICE_ROLE_KEY=... python seed_supabase.py`.

The app caches the matrix for 1 hour, so changes appear on the next reload.

### Data Caveats (June 2026 snapshot)

- Several offers are time-limited: the Sapphire Reserve 150k bonus and the elevated Freedom Unlimited $250 bonus end mid-June 2026; the Sapphire Preferred refresh (3x gas, $100 hotel credit) takes effect June 15, 2026.
- Citi Custom Cash closed to new applications May 28, 2026 (kept in the matrix for existing cardholders).
- Choose-your-category cards (Custom Cash, US Bank Cash+, BofA Customized Cash) are modeled with their most common category choice.
- Portal-only multipliers (e.g., 8x via Chase Travel) are recorded in rate notes but not used as the headline rate.
- Amex "as high as" welcome offers vary by applicant.

## Roadmap

- **Bank Integrations (Plaid)** — securely link accounts so data syncs automatically instead of manual CSV exports.
- **MCC Mapping** — auto-categorize transactions from the `Description` column instead of relying on a pre-filled `Category` column.
- **Multi-Card Stack Simulator** — exhaustive best 2/3/4-card combinations (the current engine ranks single-card additions to your existing wallet).
- **Sign-Up Bonus (SUB) Tracker** — flag upcoming large expenses that could knock out a new card's minimum spend requirement.
- **Production Stack** — Next.js + Tailwind frontend on top of the same Supabase rewards matrix.
