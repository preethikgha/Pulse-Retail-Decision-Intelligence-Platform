import duckdb
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
con = duckdb.connect(str(ROOT / "warehouse" / "retail.duckdb"), read_only=True)
OUT = ROOT / "analysis" / "causal_outputs"
OUT.mkdir(exist_ok=True)
pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 30)

df = con.execute("""
    SELECT f.order_id, f.review_score, f.is_late, f.delivery_days, f.estimated_days,
           f.freight_value, f.items_value, f.n_items, f.n_sellers,
           f.customer_state, f.purchase_month,
           date_diff('hour', f.estimated_delivery_at, f.delivered_at) / 24.0 AS days_late,
           fi.category, fi.seller_state
    FROM marts.fct_orders f
    LEFT JOIN (
        SELECT order_id, any_value(category) AS category, any_value(seller_state) AS seller_state
        FROM marts.fct_order_items GROUP BY order_id
    ) fi USING (order_id)
    WHERE f.is_late IS NOT NULL AND f.review_score IS NOT NULL
      AND f.purchase_month BETWEEN '2017-01-01' AND '2018-08-01'
""").df()

df["is_late"] = df["is_late"].astype(int)
df["low_review"] = (df["review_score"] <= 2).astype(int)
df["log_price"] = np.log1p(df["items_value"].fillna(0))
df["log_freight"] = np.log1p(df["freight_value"].fillna(0))
df["purchase_month"] = df["purchase_month"].astype(str).str[:7]
df["category"] = df["category"].fillna("unknown")
df["seller_state"] = df["seller_state"].fillna("unknown")

print(f"Orders analysed: {len(df):,}  |  late share: {df.is_late.mean():.3f}")

g = df.groupby("is_late")["review_score"].agg(["count", "mean"]).round(3)
print("\n--- 1. Naive gap ---")
print(g)
print(f"Naive gap in avg review (late - on time): {g.loc[1, 'mean'] - g.loc[0, 'mean']:.3f}")


def fit(formula, data, label):
    r = smf.ols(formula, data=data).fit(cov_type="HC1")
    lo, hi = r.conf_int().loc["is_late"]
    return {"model": label, "n": int(r.nobs), "late_effect": round(r.params["is_late"], 3),
            "std_err": round(r.bse["is_late"], 3), "ci_low": round(lo, 3), "ci_high": round(hi, 3)}


order_controls = "log_price + log_freight + n_items + n_sellers + estimated_days"
fixed = "C(customer_state) + C(purchase_month)"
single = df[(df.n_items == 1)]

rows = [
    fit("review_score ~ is_late", df, "M1 naive"),
    fit(f"review_score ~ is_late + {order_controls}", df, "M2 + order controls"),
    fit(f"review_score ~ is_late + {order_controls} + {fixed}", df, "M3 + state and month FE"),
    fit(f"review_score ~ is_late + log_price + log_freight + estimated_days + {fixed} "
        f"+ C(category) + C(seller_state)", single, "M4 single-item orders + category, seller state"),
    fit(f"low_review ~ is_late + {order_controls} + {fixed}", df, "M5 outcome: review <= 2 (prob. change)"),
]
res = pd.DataFrame(rows)
print("\n--- 2. Effect of late delivery (coefficient on is_late) ---")
print(res.to_string(index=False))
res.to_csv(OUT / "regression_results.csv", index=False)

bins = [-1e9, -7, 0, 3, 7, 1e9]
labels = ["early > 7d", "early 0-7d", "late 0-3d", "late 3-7d", "late > 7d"]
df["lateness_bucket"] = pd.cut(df["days_late"], bins=bins, labels=labels)
dose = df.groupby("lateness_bucket", observed=True).agg(
    orders=("order_id", "count"),
    avg_review=("review_score", "mean"),
    low_review_share=("low_review", "mean")).round(3)
print("\n--- 3. Dose-response (review vs days late) ---")
print(dose)
dose.to_csv(OUT / "dose_response.csv")

chk = smf.ols(f"log_price ~ is_late + {fixed}", data=df).fit(cov_type="HC1")
print("\n--- 4. Balance check (log price on is_late, with state and month FE) ---")
print(f"coef = {chk.params['is_late']:.3f}  (p = {chk.pvalues['is_late']:.3f})  "
      f"-> late orders are about {100 * (np.exp(chk.params['is_late']) - 1):.1f}% different in price")