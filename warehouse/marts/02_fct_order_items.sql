CREATE OR REPLACE TABLE marts.fct_order_items AS
SELECT
    i.order_id,
    i.order_item_id,
    i.product_id,
    pr.category,
    i.seller_id,
    s.state AS seller_state,
    i.price,
    i.freight_value,
    f.customer_state,
    f.purchase_month,
    f.delivery_days,
    f.is_late,
    f.review_score
FROM staging.stg_order_items i
LEFT JOIN staging.stg_products pr ON i.product_id = pr.product_id
LEFT JOIN staging.stg_sellers  s  ON i.seller_id  = s.seller_id
LEFT JOIN marts.fct_orders     f  ON i.order_id   = f.order_id;