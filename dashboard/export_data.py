import shutil
import duckdb
import pandas as pd
from pathlib import Path
from statsmodels.stats.proportion import confint_proportions_2indep

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "dashboard" / "data"
DATA.mkdir(parents=True, exist_ok=True)

for src in ["analysis/monthly_metrics.csv",
            "analysis/rca_outputs/stages_by_month.csv",
            "analysis/causal_outputs/dose_response.csv",
            "analysis/causal_outputs/regression_results.csv",
            "experiments/outputs/segment_lifts.csv",
            "ml/backtest_results.csv",
            "api/model/model_info.json"]:
    shutil.copy(ROOT / src, DATA / Path(src).name)

con = duckdb.connect(str(ROOT / "warehouse" / "retail.duckdb"), read_only=True)
d = con.execute("""
    SELECT test_group, COUNT(*) AS n, SUM(converted::INT) AS x
    FROM staging.stg_marketing_ab GROUP BY 1
""").df().set_index("test_group")
n1, x1 = int(d.loc["ad", "n"]), int(d.loc["ad", "x"])
n0, x0 = int(d.loc["psa", "n"]), int(d.loc["psa", "x"])
lo, hi = confint_proportions_2indep(x1, n1, x0, n0, method="newcomb", compare="diff")
pd.DataFrame([{
    "n_ad": n1, "x_ad": x1, "n_psa": n0, "x_psa": x0,
    "rate_ad": x1 / n1, "rate_psa": x0 / n0,
    "lift_pp": (x1 / n1 - x0 / n0) * 100, "ci_low_pp": lo * 100, "ci_high_pp": hi * 100,
}]).to_csv(DATA / "ab_topline.csv", index=False)
print("Exported dashboard data to", DATA)