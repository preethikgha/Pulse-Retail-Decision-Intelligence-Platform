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
    # files named 01_name.sql run in order; table is called "name"
    table = f.stem.split("_", 1)[1] if f.stem[:2].isdigit() else f.stem
    n = con.execute(f"SELECT COUNT(*) FROM {folder}.{table}").fetchone()[0]
    print(f"{folder}.{table}: {n:,} rows")

con.close()