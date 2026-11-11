CREATE OR REPLACE TABLE marts.fct_orders AS
WITH reviews AS (
    SELECT order_id, review_score,
           ROW_NUMBER() OVER (
               PARTITION BY order_id
               ORDER BY review_answered_at DESC NULLS LAST, review_created_at DESC
           ) AS rn
    FROM staging.stg_reviews
),
items AS (
    SELECT order_id,
           COUNT(*)                  AS n_items,
           COUNT(DISTINCT seller_id) AS n_sellers,
           SUM(price)                AS items_value,
           SUM(freight_value)        AS freight_value
    FROM staging.stg_order_items
    GROUP BY order_id
),
pay AS (
    SELECT order_id, SUM(payment_value) AS payment_value
    FROM staging.stg_payments
    GROUP BY order_id
)
SELECT
    o.order_id,
    o.customer_id,
    c.customer_unique_id,
    c.state AS customer_state,
    o.order_status,
    o.purchased_at,
    DATE_TRUNC('month', o.purchased_at) AS purchase_month,
    o.delivered_at,
    o.estimated_delivery_at,
    DATE_DIFF('day', o.purchased_at, o.delivered_at)          AS delivery_days,
    DATE_DIFF('day', o.purchased_at, o.estimated_delivery_at) AS estimated_days,
    CASE WHEN o.delivered_at IS NULL THEN NULL
         WHEN o.delivered_at > o.estimated_delivery_at THEN 1
         ELSE 0 END                                           AS is_late,
    r.review_score,
    i.n_items, i.n_sellers, i.items_value, i.freight_value,
    p.payment_value
FROM staging.stg_orders o
LEFT JOIN staging.stg_customers c ON o.customer_id = c.customer_id
LEFT JOIN reviews r ON o.order_id = r.order_id AND r.rn = 1
LEFT JOIN items   i ON o.order_id = i.order_id
LEFT JOIN pay     p ON o.order_id = p.order_id;