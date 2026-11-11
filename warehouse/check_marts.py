import duckdb
con = duckdb.connect("warehouse/retail.duckdb", read_only=True)

print("\n--- date range and missing deliveries ---")
print(con.execute("""
    SELECT MIN(purchased_at) AS first_order, MAX(purchased_at) AS last_order,
           COUNT(*) FILTER (WHERE delivered_at IS NULL) AS no_delivery_date,
           COUNT(*) FILTER (WHERE review_score IS NULL) AS no_review
    FROM marts.fct_orders
""").df().to_string(index=False))

print("\n--- order status ---")
print(con.execute("""
    SELECT order_status, COUNT(*) AS n
    FROM marts.fct_orders GROUP BY 1 ORDER BY n DESC
""").df().to_string(index=False))

print("\n--- overall late rate and avg review ---")
print(con.execute("""
    SELECT ROUND(AVG(is_late), 3) AS late_rate,
           ROUND(AVG(delivery_days), 1) AS avg_delivery_days,
           ROUND(AVG(review_score), 2) AS avg_review
    FROM marts.fct_orders
""").df().to_string(index=False))

print("\n--- avg review: late vs on time ---")
print(con.execute("""
    SELECT is_late, COUNT(*) AS n, ROUND(AVG(review_score), 2) AS avg_review
    FROM marts.fct_orders WHERE is_late IS NOT NULL
    GROUP BY 1 ORDER BY 1
""").df().to_string(index=False))

print("\n--- A/B groups ---")
print(con.execute("""
    SELECT test_group, COUNT(*) AS n, ROUND(AVG(converted::INT), 4) AS conv_rate
    FROM staging.stg_marketing_ab GROUP BY 1
""").df().to_string(index=False))