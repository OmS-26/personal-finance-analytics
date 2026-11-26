-- Personal Finance Analytics: analysis queries
-- Run after 01_schema.sql, 02_seed_data.sql and 03_views.sql. Each query is independent.
USE finance_analytics;

-- ---------------------------------------------------------------------------
-- Q1. Monthly cash flow per user: income, spending, net, and savings rate.
--     Transfers between a user's own accounts are excluded so they don't
--     count as income or spending.
-- ---------------------------------------------------------------------------
WITH monthly AS (
    SELECT
        u.user_id,
        u.full_name,
        DATE_FORMAT(t.transaction_date, '%Y-%m') AS month,
        SUM(CASE WHEN c.category_type = 'Income'  THEN t.amount ELSE 0 END)  AS income,
        SUM(CASE WHEN c.category_type = 'Expense' THEN -t.amount ELSE 0 END) AS spending
    FROM transactions t
    JOIN accounts   a ON a.account_id  = t.account_id
    JOIN users      u ON u.user_id     = a.user_id
    JOIN categories c ON c.category_id = t.category_id
    GROUP BY u.user_id, u.full_name, month
)
SELECT
    full_name,
    month,
    ROUND(income, 2)                                       AS income,
    ROUND(spending, 2)                                     AS spending,
    ROUND(income - spending, 2)                            AS net_cash_flow,
    ROUND(100 * (income - spending) / NULLIF(income, 0), 1) AS savings_rate_pct
FROM monthly
ORDER BY full_name, month;


-- ---------------------------------------------------------------------------
-- Q2. Running balance per account (opening balance + every transaction to date).
--     transaction_id breaks ties for same-day transactions.
-- ---------------------------------------------------------------------------
SELECT
    a.account_id,
    a.account_type,
    t.transaction_date,
    t.amount,
    a.opening_balance + SUM(t.amount) OVER (
        PARTITION BY t.account_id
        ORDER BY t.transaction_date, t.transaction_id
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS running_balance
FROM transactions t
JOIN accounts a ON a.account_id = t.account_id
ORDER BY a.account_id, t.transaction_date, t.transaction_id;


-- ---------------------------------------------------------------------------
-- Q3. Accounts that went into overdraft: first date the chequing balance
--     dropped below zero, and the lowest balance reached.
-- ---------------------------------------------------------------------------
WITH balances AS (
    SELECT
        a.account_id,
        a.user_id,
        t.transaction_date,
        a.opening_balance + SUM(t.amount) OVER (
            PARTITION BY t.account_id
            ORDER BY t.transaction_date, t.transaction_id
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS balance
    FROM transactions t
    JOIN accounts a ON a.account_id = t.account_id
    WHERE a.account_type = 'Chequing'
)
SELECT
    u.full_name,
    b.account_id,
    MIN(CASE WHEN b.balance < 0 THEN b.transaction_date END) AS first_overdraft_date,
    ROUND(MIN(b.balance), 2)                                 AS lowest_balance
FROM balances b
JOIN users u ON u.user_id = b.user_id
GROUP BY u.full_name, b.account_id
HAVING MIN(b.balance) < 0
ORDER BY lowest_balance;


-- ---------------------------------------------------------------------------
-- Q4. Spending by category per month, with each category's share of the
--     month's total and its month-over-month change.
-- ---------------------------------------------------------------------------
WITH cat_month AS (
    SELECT
        DATE_FORMAT(t.transaction_date, '%Y-%m') AS month,
        c.category_name,
        SUM(-t.amount) AS spent
    FROM transactions t
    JOIN categories c ON c.category_id = t.category_id
    WHERE c.category_type = 'Expense'
    GROUP BY month, c.category_name
)
SELECT
    month,
    category_name,
    ROUND(spent, 2) AS spent,
    ROUND(100 * spent / SUM(spent) OVER (PARTITION BY month), 1) AS pct_of_month,
    ROUND(spent - LAG(spent) OVER (PARTITION BY category_name ORDER BY month), 2) AS change_vs_prev_month
FROM cat_month
ORDER BY month, spent DESC;


-- ---------------------------------------------------------------------------
-- Q5. Top 3 merchants by total spend for each user (ties share a rank).
-- ---------------------------------------------------------------------------
WITH merchant_spend AS (
    SELECT
        u.full_name,
        m.merchant_name,
        SUM(-t.amount) AS spent,
        RANK() OVER (PARTITION BY u.user_id ORDER BY SUM(-t.amount) DESC) AS spend_rank
    FROM transactions t
    JOIN accounts   a ON a.account_id  = t.account_id
    JOIN users      u ON u.user_id     = a.user_id
    JOIN merchants  m ON m.merchant_id = t.merchant_id
    JOIN categories c ON c.category_id = t.category_id
    WHERE c.category_type = 'Expense'
      AND c.category_name <> 'Rent'
    GROUP BY u.user_id, u.full_name, m.merchant_name
)
SELECT full_name, spend_rank, merchant_name, ROUND(spent, 2) AS spent
FROM merchant_spend
WHERE spend_rank <= 3
ORDER BY full_name, spend_rank;


-- ---------------------------------------------------------------------------
-- Q6. Recurring charges: same merchant, same amount, in 3+ different months.
--     Catches subscriptions and fixed bills a user may have forgotten about.
-- ---------------------------------------------------------------------------
SELECT
    u.full_name,
    m.merchant_name,
    -t.amount                                         AS monthly_amount,
    COUNT(DISTINCT DATE_FORMAT(t.transaction_date, '%Y-%m')) AS months_charged,
    ROUND(-t.amount * 12, 2)                          AS annualized_cost
FROM transactions t
JOIN accounts   a ON a.account_id  = t.account_id
JOIN users      u ON u.user_id     = a.user_id
JOIN merchants  m ON m.merchant_id = t.merchant_id
JOIN categories c ON c.category_id = t.category_id
WHERE c.category_type = 'Expense'
GROUP BY u.user_id, u.full_name, m.merchant_name, t.amount
HAVING months_charged >= 3
ORDER BY u.full_name, annualized_cost DESC;


-- ---------------------------------------------------------------------------
-- Q7. Anomaly detection. The logic lives in the v_flagged_transactions view
--     (03_views.sql) so the dashboard and this report use the same rule.
-- ---------------------------------------------------------------------------
SELECT *
FROM v_flagged_transactions
ORDER BY z_score DESC;
