CREATE OR REPLACE TABLE staging.stg_orders AS
SELECT
    order_id,
    customer_id,
    order_status,
    TRY_CAST(order_purchase_timestamp      AS TIMESTAMP) AS purchased_at,
    TRY_CAST(order_approved_at             AS TIMESTAMP) AS approved_at,
    TRY_CAST(order_delivered_carrier_date  AS TIMESTAMP) AS shipped_at,
    TRY_CAST(order_delivered_customer_date AS TIMESTAMP) AS delivered_at,
    TRY_CAST(order_estimated_delivery_date AS TIMESTAMP) AS estimated_delivery_at
FROM raw.orders;