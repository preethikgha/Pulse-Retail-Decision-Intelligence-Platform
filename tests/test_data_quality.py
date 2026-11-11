import duckdb
import pytest
from pathlib import Path

DB = Path(__file__).resolve().parent.parent / "warehouse" / "retail.duckdb"


@pytest.fixture(scope="module")
def con():
    c = duckdb.connect(str(DB), read_only=True)
    yield c
    c.close()


def scalar(con, sql):
    return con.execute(sql).fetchone()[0]


def test_order_id_unique(con):
    assert scalar(con, "SELECT COUNT(*) - COUNT(DISTINCT order_id) FROM marts.fct_orders") == 0


def test_order_id_not_null(con):
    assert scalar(con, "SELECT COUNT(*) FROM marts.fct_orders WHERE order_id IS NULL") == 0


def test_every_order_has_customer(con):
    assert scalar(con, "SELECT COUNT(*) FROM marts.fct_orders WHERE customer_state IS NULL") == 0


def test_items_reference_valid_orders(con):
    assert scalar(con, """
        SELECT COUNT(*) FROM staging.stg_order_items i
        LEFT JOIN staging.stg_orders o USING (order_id)
        WHERE o.order_id IS NULL""") == 0


def test_items_reference_valid_sellers(con):
    assert scalar(con, """
        SELECT COUNT(*) FROM staging.stg_order_items i
        LEFT JOIN staging.stg_sellers s USING (seller_id)
        WHERE s.seller_id IS NULL""") == 0


def test_review_score_range(con):
    assert scalar(con, "SELECT COUNT(*) FROM marts.fct_orders WHERE review_score NOT BETWEEN 1 AND 5") == 0


def test_delivery_not_before_purchase(con):
    assert scalar(con, "SELECT COUNT(*) FROM marts.fct_orders WHERE delivered_at < purchased_at") == 0


def test_late_flag_only_for_delivered(con):
    assert scalar(con, "SELECT COUNT(*) FROM marts.fct_orders WHERE is_late IS NOT NULL AND delivered_at IS NULL") == 0


def test_fct_order_items_row_count_matches_staging(con):
    a = scalar(con, "SELECT COUNT(*) FROM marts.fct_order_items")
    b = scalar(con, "SELECT COUNT(*) FROM staging.stg_order_items")
    assert a == b


def test_ab_groups_valid(con):
    assert scalar(con, "SELECT COUNT(*) FROM staging.stg_marketing_ab WHERE test_group NOT IN ('ad','psa')") == 0


def test_ab_user_id_unique(con):
    assert scalar(con, "SELECT COUNT(*) - COUNT(DISTINCT user_id) FROM staging.stg_marketing_ab") == 0