-- Personal Finance Analytics: views used by the Tableau dashboard and reports
USE finance_analytics;

-- One flat row per transaction with everything a dashboard needs.
CREATE OR REPLACE VIEW v_transactions_enriched AS
SELECT
    t.transaction_id,
    t.transaction_date,
    DATE_FORMAT(t.transaction_date, '%Y-%m') AS month,
    u.user_id,
    u.full_name,
    u.city,
    a.account_id,
    a.account_type,
    m.merchant_name,
    c.category_name,
    c.category_type,
    t.amount,
    a.opening_balance + SUM(t.amount) OVER (
        PARTITION BY t.account_id
        ORDER BY t.transaction_date, t.transaction_id
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS running_balance
FROM transactions t
JOIN accounts   a ON a.account_id  = t.account_id
JOIN users      u ON u.user_id     = a.user_id
JOIN merchants  m ON m.merchant_id = t.merchant_id
JOIN categories c ON c.category_id = t.category_id;

-- ---------------------------------------------------------------------------
-- Flagged transactions: flag a purchase when it is more than 3 standard
--     deviations above that user's average for the same category, computed
--     over their PREVIOUS purchases only (so the purchase can't hide its own
--     effect on the average). Requires 5+ prior purchases for a baseline,
--     and the purchase must also be at least 3x the user's typical amount so
--     that small dollar swings on low-variance categories aren't flagged.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_flagged_transactions AS
WITH history AS (
    SELECT
        t.transaction_id,
        u.full_name,
        c.category_name,
        m.merchant_name,
        t.transaction_date,
        -t.amount AS spent,
        AVG(-t.amount) OVER w         AS prior_avg,
        STDDEV_SAMP(-t.amount) OVER w AS prior_stddev,
        COUNT(*) OVER w               AS prior_count
    FROM transactions t
    JOIN accounts   a ON a.account_id  = t.account_id
    JOIN users      u ON u.user_id     = a.user_id
    JOIN categories c ON c.category_id = t.category_id
    JOIN merchants  m ON m.merchant_id = t.merchant_id
    WHERE c.category_type = 'Expense'
    WINDOW w AS (
        PARTITION BY u.user_id, c.category_id
        ORDER BY t.transaction_date, t.transaction_id
        ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
    )
)
SELECT
    transaction_id,
    full_name,
    category_name,
    merchant_name,
    transaction_date,
    ROUND(spent, 2)                                 AS spent,
    ROUND(prior_avg, 2)                             AS typical_spend,
    ROUND((spent - prior_avg) / prior_stddev, 1)    AS z_score
FROM history
WHERE prior_count >= 5
  AND prior_stddev > 0
  AND spent > prior_avg + 3 * prior_stddev
  AND spent >= 3 * prior_avg;
