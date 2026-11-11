import duckdb
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
con = duckdb.connect(str(ROOT / "warehouse" / "retail.duckdb"), read_only=True)
OUT = ROOT / "analysis" / "rca_outputs"
OUT.mkdir(exist_ok=True)
pd.set_option("display.width", 220)
pd.set_option("display.max_columns", 30)

# "Normal" months used as the baseline for comparison
BASE = ("(purchase_month BETWEEN '2017-05-01' AND '2017-10-01' "
        "OR purchase_month BETWEEN '2018-04-01' AND '2018-07-01')")
WINDOWS = {
    "nov2017": ("2017-11-01", "2017-11-01"),
    "febmar2018": ("2018-02-01", "2018-03-01"),
}


def excess(table, dim, a, b, min_base=30, top=8):
    q = f"""
    WITH t AS (
        SELECT {dim} AS seg, purchase_month, is_late
        FROM {table} WHERE is_late IS NOT NULL
    ),
    base AS (
        SELECT seg, COUNT(*) AS n, AVG(is_late) AS r FROM t WHERE {BASE} GROUP BY seg
    ),
    spike AS (
        SELECT seg, COUNT(*) AS n, SUM(is_late) AS late, AVG(is_late) AS r
        FROM t WHERE purchase_month BETWEEN '{a}' AND '{b}' GROUP BY seg
    )
    SELECT s.seg,
           s.n AS spike_rows,
           CAST(s.late AS INT) AS spike_late,
           ROUND(b.r, 3) AS base_rate,
           ROUND(s.r, 3) AS spike_rate,
           ROUND(s.late - s.n * b.r, 0) AS excess_late,
           ROUND(100 * (s.late - s.n * b.r) / SUM(s.late - s.n * b.r) OVER (), 1) AS pct_of_excess
    FROM spike s JOIN base b USING (seg)
    WHERE b.n >= {min_base}
    ORDER BY excess_late DESC
    LIMIT {top}
    """
    return con.execute(q).df()


CUTS = [
    ("customer_state", "marts.fct_orders", "customer_state"),
    ("category", "marts.fct_order_items", "category"),
    ("seller_state", "marts.fct_order_items", "seller_state"),
    ("seller_id", "marts.fct_order_items", "seller_id"),
    ("seller_in_customer_state", "marts.fct_order_items", "seller_state = customer_state"),
]

base_rate = con.execute(
    f"SELECT ROUND(AVG(is_late), 3) FROM marts.fct_orders WHERE {BASE}"
).fetchone()[0]
print(f"Baseline late rate (normal months): {base_rate}")

for wname, (a, b) in WINDOWS.items():
    print("\n" + "=" * 90)
    print(f"WINDOW: {wname}  ({a[:7]} to {b[:7]})   [item-level tables count items, not orders]")
    print("=" * 90)
    for name, table, dim in CUTS:
        df = excess(table, dim, a, b)
        print(f"\n--- by {name} ---")
        print(df.to_string(index=False))
        df.to_csv(OUT / f"{wname}_{name}.csv", index=False)

print("\n" + "=" * 90)
print("DELIVERY STAGES BY MONTH (avg days)")
print("=" * 90)
stages = con.execute("""
    SELECT strftime(purchased_at, '%Y-%m') AS month,
           COUNT(*) AS delivered,
           ROUND(AVG(date_diff('hour', purchased_at, approved_at)) / 24.0, 2)  AS approval_days,
           ROUND(AVG(date_diff('hour', approved_at, shipped_at)) / 24.0, 2)    AS seller_handling_days,
           ROUND(AVG(date_diff('hour', shipped_at, delivered_at)) / 24.0, 2)   AS carrier_days,
           ROUND(AVG(date_diff('day', purchased_at, estimated_delivery_at)), 1) AS promised_days
    FROM staging.stg_orders
    WHERE delivered_at IS NOT NULL
      AND purchased_at BETWEEN '2017-01-01' AND '2018-08-31'
    GROUP BY 1 ORDER BY 1
""").df()
print(stages.to_string(index=False))
stages.to_csv(OUT / "stages_by_month.csv", index=False)