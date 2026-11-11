CREATE OR REPLACE TABLE staging.stg_order_items AS
SELECT
    order_id,
    order_item_id,
    product_id,
    seller_id,
    TRY_CAST(shipping_limit_date AS TIMESTAMP) AS shipping_limit_at,
    CAST(price AS DOUBLE)         AS price,
    CAST(freight_value AS DOUBLE) AS freight_value
FROM raw.order_items;