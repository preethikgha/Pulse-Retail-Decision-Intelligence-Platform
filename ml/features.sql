CREATE OR REPLACE TABLE marts.ml_features AS
WITH geo AS (
    SELECT geolocation_zip_code_prefix AS zip_prefix,
           AVG(geolocation_lat) AS lat,
           AVG(geolocation_lng) AS lng
    FROM raw.geolocation
    GROUP BY 1
),
item_agg AS (
    SELECT i.order_id,
           arg_min(i.seller_id, i.order_item_id) AS seller_id,
           arg_min(p.category, i.order_item_id)  AS category,
           SUM(p.product_weight_g) AS weight_g,
           SUM(p.product_length_cm * p.product_height_cm * p.product_width_cm) AS volume_cm3
    FROM staging.stg_order_items i
    LEFT JOIN staging.stg_products p USING (product_id)
    GROUP BY i.order_id
)
SELECT
    f.order_id,
    strftime(f.purchased_at, '%Y-%m') AS month,
    hour(f.purchased_at)      AS purchase_hour,
    dayofweek(f.purchased_at) AS purchase_dow,
    month(f.purchased_at)     AS purchase_month_num,
    f.estimated_days,
    f.n_items, f.n_sellers, f.items_value, f.freight_value,
    f.freight_value / NULLIF(f.items_value, 0) AS freight_ratio,
    a.weight_g, a.volume_cm3,
    a.category,
    f.customer_state,
    s.state AS seller_state,
    CASE WHEN f.customer_state = s.state THEN 1 ELSE 0 END AS same_state,
    2 * 6371 * asin(sqrt(
        pow(sin(radians(cg.lat - sg.lat) / 2), 2)
        + cos(radians(sg.lat)) * cos(radians(cg.lat)) * pow(sin(radians(cg.lng - sg.lng) / 2), 2)
    )) AS distance_km,
    f.is_late
FROM marts.fct_orders f
LEFT JOIN item_agg a ON f.order_id = a.order_id
LEFT JOIN staging.stg_sellers s ON a.seller_id = s.seller_id
LEFT JOIN staging.stg_customers c ON f.customer_id = c.customer_id
LEFT JOIN geo cg ON c.zip_prefix = cg.zip_prefix
LEFT JOIN geo sg ON s.zip_prefix = sg.zip_prefix
WHERE f.is_late IS NOT NULL
  AND f.purchased_at >= '2017-01-01' AND f.purchased_at < '2018-09-01';