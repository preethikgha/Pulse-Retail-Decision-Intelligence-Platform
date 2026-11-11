CREATE OR REPLACE TABLE staging.stg_reviews AS
SELECT
    review_id,
    order_id,
    CAST(review_score AS INTEGER) AS review_score,
    TRY_CAST(review_creation_date    AS TIMESTAMP) AS review_created_at,
    TRY_CAST(review_answer_timestamp AS TIMESTAMP) AS review_answered_at
FROM raw.order_reviews;