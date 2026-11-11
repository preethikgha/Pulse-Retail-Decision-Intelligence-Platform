CREATE OR REPLACE TABLE staging.stg_payments AS
SELECT
    order_id,
    payment_sequential,
    payment_type,
    payment_installments,
    CAST(payment_value AS DOUBLE) AS payment_value
FROM raw.order_payments;