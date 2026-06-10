# 💳 CreditCrunch

CreditCrunch is a smart credit card optimization tool that analyzes your real-world spending habits and matches them with the perfect card "stack" to maximize points, miles, or cashback.

Instead of guessing which card to pull out at the grocery store, CreditCrunch does the math — it looks at your actual transaction history and simulates how much more you could have earned.

## Features

- **CSV Uploader** — drag-and-drop your transaction history exported from your bank (Chase, Amex, Citi, etc.).
- **Spend Breakdown** — see where your money actually goes by reward category (Dining, Groceries, Gas, Travel, Other).
- **Optimization Score (0–100%)** — how well your current wallet performs against the best possible card for every transaction.
- **Missed Points Calculator** — the painful (but motivating) number of points you left on the table.
- **Top Recommendation** — the single card that would best plug the gap in your current stack.

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

4. In the sidebar, select the cards you currently own and set your estimated point value.
5. Upload a transaction CSV — a sample file (`transactions.csv`) is included in this repo.

## CSV Format

The uploader expects a CSV with at least these columns:

```csv
Date,Description,Amount,Category
2026-05-01,Whole Foods,150.00,Groceries
2026-05-02,Local Bistro,85.00,Dining
2026-05-04,ExxonMobil,45.00,Gas
2026-05-05,Delta Air Lines,350.00,Travel
2026-05-06,Target,120.00,Other
```

Supported categories: `Groceries`, `Dining`, `Gas`, `Travel`, `Other` (anything else is treated as 1x).

## Card Database

The prototype ships with a small mock database of popular cards:

| Card | Groceries | Dining | Travel | Gas | Other | Annual Fee |
|------|-----------|--------|--------|-----|-------|------------|
| Amex Gold | 4x | 4x | 3x | 1x | 1x | $250 |
| Chase Sapphire Preferred | 1x | 3x | 2x | 1x | 1x | $95 |
| Citi Custom Cash | 5x | 1x | 1x | 1x | 1x | $0 |
| Capital One SavorOne | 3x | 3x | 1x | 1x | 1x | $0 |
| Catch-All 2% (e.g., Citi Double Cash) | 2x | 2x | 2x | 2x | 2x | $0 |

## Roadmap

- **Bank Integrations (Plaid)** — securely link accounts so data syncs automatically instead of manual CSV exports.
- **MCC Mapping** — auto-categorize transactions from the `Description` column instead of relying on a pre-filled `Category` column.
- **Multi-Card Stack Recommendations** — simulate the highest-yielding 2-, 3-, and 4-card combinations, factoring in annual fees and cashback vs. travel preferences.
- **Sign-Up Bonus (SUB) Tracker** — flag upcoming large expenses that could knock out a new card's minimum spend requirement.
- **Production Stack** — Next.js + Tailwind frontend with a PostgreSQL/Supabase-backed rewards matrix.
