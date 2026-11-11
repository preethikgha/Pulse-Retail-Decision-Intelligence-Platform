import sys
import duckdb
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "warehouse" / "retail.duckdb"

folder = sys.argv[1]  # staging or marts
con = duckdb.connect(str(DB))
con.execute(f"CREATE SCHEMA IF NOT EXISTS {folder};")

for f in sorted((ROOT / "warehouse" / folder).glob("*.sql")):
    con.execute(f.read_text(encoding="utf-8"))
    n = con.execute(f"SELECT COUNT(*) FROM {folder}.{f.stem}").fetchone()[0]
    print(f"{folder}.{f.stem}: {n:,} rows")

con.close()