WITH m AS (
    SELECT
        purchase_month,
        COUNT(*)                                                  AS orders,
        COUNT(*) FILTER (WHERE delivered_at IS NOT NULL)          AS delivered_orders,
        COUNT(*) FILTER (WHERE is_late = 0 AND review_score >= 4) AS good_delivery_orders,
        ROUND(COUNT(*) FILTER (WHERE is_late = 0 AND review_score >= 4) * 1.0
              / NULLIF(COUNT(*) FILTER (WHERE delivered_at IS NOT NULL), 0), 3) AS good_delivery_rate,
        ROUND(AVG(is_late), 3)                                    AS late_rate,
        ROUND(COUNT(*) FILTER (WHERE order_status = 'canceled') * 1.0 / COUNT(*), 4) AS cancel_rate,
        ROUND(AVG(delivery_days), 1)                              AS avg_delivery_days,
        ROUND(AVG(review_score), 2)                               AS avg_review_score
    FROM marts.fct_orders
    GROUP BY purchase_month
)
SELECT *,
       ROUND(late_rate - LAG(late_rate) OVER (ORDER BY purchase_month), 3) AS late_rate_change
FROM m
ORDER BY purchase_month;