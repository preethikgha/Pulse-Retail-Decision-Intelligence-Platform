CREATE OR REPLACE TABLE staging.stg_marketing_ab AS
SELECT
    "user id"       AS user_id,
    "test group"    AS test_group,
    CAST(converted AS BOOLEAN) AS converted,
    "total ads"     AS total_ads,
    "most ads day"  AS most_ads_day,
    "most ads hour" AS most_ads_hour
FROM raw.marketing_ab;