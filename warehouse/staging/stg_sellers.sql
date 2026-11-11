CREATE OR REPLACE TABLE staging.stg_sellers AS
SELECT
    seller_id,
    seller_zip_code_prefix AS zip_prefix,
    seller_city            AS city,
    seller_state           AS state
FROM raw.sellers;