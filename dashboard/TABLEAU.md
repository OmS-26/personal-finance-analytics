# Building the Tableau Public dashboard

Tableau Public is free but only reads files, so the dashboard is built from the CSVs that
`scripts/export_for_tableau.py` writes to `exports/`.

## 1. Connect the data
1. Download Tableau Public Desktop: https://public.tableau.com/app/discover
2. **Connect → Text file →** `exports/transactions_enriched.csv`
3. In the data source tab, drag `flagged_transactions.csv` onto the canvas and set up a
   **Left join** on `transaction_id`. Flagged rows will have a non-null `z_score`.
4. Check data types: `transaction_date` = Date, `amount` / `running_balance` = Number (decimal).

## 2. Calculated fields
Create these with **Analysis → Create Calculated Field**:

| Name | Formula |
|---|---|
| Income | `IF [category_type] = "Income" THEN [amount] END` |
| Spending | `IF [category_type] = "Expense" THEN -[amount] END` |
| Net Cash Flow | `SUM([Income]) - SUM([Spending])` |
| Savings Rate | `(SUM([Income]) - SUM([Spending])) / SUM([Income])` (format as %) |
| Is Flagged | `NOT ISNULL([z_score])` |

## 3. Sheets
1. **Monthly cash flow** — Columns: `MONTH(transaction_date)`. Rows: `SUM(Income)` and `SUM(Spending)`
   as a dual-axis line, plus `Net Cash Flow` as bars.
2. **Spending by category** — Stacked bar: Columns `MONTH(transaction_date)`, Rows `SUM(Spending)`,
   Color `category_name`.
3. **Account balances** — Line: Columns `transaction_date` (exact date), Rows `AVG(running_balance)`,
   Detail `account_id`, filter `account_type`. Add a reference line at 0 to show overdrafts.
4. **Flagged transactions** — Table filtered to `Is Flagged = True`, showing user, merchant, date,
   amount, typical spend and z-score, sorted by z-score.
5. **KPI tiles** — Text sheets for total income, total spending, average savings rate, and number
   of flagged transactions.

## 4. Dashboard
- **Dashboard → New Dashboard**, set size to *Automatic*.
- Put the KPI tiles across the top, cash flow and category charts in the middle, and the flagged
  transactions table at the bottom.
- Add a `full_name` filter and set it to **Apply to Worksheets → All Using This Data Source**, so
  the whole dashboard can be viewed per user.

## 5. Publish
**File → Save to Tableau Public.** Copy the link into the README's Dashboard section and add a
screenshot as `dashboard/screenshot.png`.
