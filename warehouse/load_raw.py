
import duckdb
from pathlib import Path

# Project paths
ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
DB = ROOT / "warehouse" / "retail.duckdb"

# Connect to DuckDB
con = duckdb.connect(str(DB))
con.execute("CREATE SCHEMA IF NOT EXISTS raw;")

# Load all Olist CSV files
olist_folder = RAW / "olist"

for f in sorted(olist_folder.glob("*.csv")):
    name = f.stem.replace("olist_", "").replace("_dataset", "")

    print(f"Loading {f.name}...")

    con.execute(f"""
        CREATE OR REPLACE TABLE raw.{name} AS
        SELECT * FROM read_csv_auto('{f.as_posix()}', header=true)
    """)

    n = con.execute(
        f"SELECT COUNT(*) FROM raw.{name}"
    ).fetchone()[0]

    print(f"raw.{name}: {n:,} rows")

# Load Marketing A/B dataset
ab_files = list((RAW / "marketing_ab").glob("*.csv"))

if not ab_files:
    raise FileNotFoundError("Marketing A/B CSV not found!")

ab = ab_files[0]

print(f"Loading {ab.name}...")

con.execute(f"""
    CREATE OR REPLACE TABLE raw.marketing_ab AS
    SELECT * FROM read_csv_auto('{ab.as_posix()}', header=true)
""")

n = con.execute(
    "SELECT COUNT(*) FROM raw.marketing_ab"
).fetchone()[0]

print(f"raw.marketing_ab: {n:,} rows")

con.close()

print("\nRaw data loading completed successfully!")
