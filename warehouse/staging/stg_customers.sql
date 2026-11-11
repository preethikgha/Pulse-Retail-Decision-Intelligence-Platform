CREATE OR REPLACE TABLE staging.stg_customers AS
SELECT
    customer_id,
    customer_unique_id,
    customer_zip_code_prefix AS zip_prefix,
    customer_city            AS city,
    customer_state           AS state
FROM raw.customers;