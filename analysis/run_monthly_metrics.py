import duckdb
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
con = duckdb.connect(str(ROOT / "warehouse" / "retail.duckdb"), read_only=True)
df = con.execute((ROOT / "analysis" / "monthly_metrics.sql").read_text(encoding="utf-8")).df()
df.to_csv(ROOT / "analysis" / "monthly_metrics.csv", index=False)
print(df.to_string(index=False))