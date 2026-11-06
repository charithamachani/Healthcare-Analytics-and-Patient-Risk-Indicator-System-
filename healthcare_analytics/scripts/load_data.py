"""Clean the synthetic CSVs and load them into the database.

Run:  python -m scripts.load_data --reset
--reset drops and re-creates all tables first (safe: synthetic data only).
Rejected measurement rows are written to data/rejected_measurements.csv with a reason.
"""
import argparse
from pathlib import Path

import pandas as pd

from app.analytics import clean_measurements
from app.config import default_database_url
from app.db import departments, get_engine, measurements, metadata, patients, visits

DATA = Path("data")


def bulk_insert(conn, table, df, chunk=2000):
    df = df.astype(object).where(df.notna(), None)
    records = df.to_dict("records")
    for i in range(0, len(records), chunk):
        conn.execute(table.insert(), records[i:i + chunk])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="drop and recreate all tables first")
    args = parser.parse_args()

    engine = get_engine(default_database_url())
    if args.reset:
        metadata.drop_all(engine)
    metadata.create_all(engine)

    raw = pd.read_csv(DATA / "measurements_raw.csv")
    raw["measurement_date"] = pd.to_datetime(raw["measurement_date"])
    clean, rejected = clean_measurements(raw)
    rejected.to_csv(DATA / "rejected_measurements.csv", index=False)
    clean["measurement_date"] = clean["measurement_date"].dt.date

    visits_df = pd.read_csv(DATA / "visits.csv", parse_dates=["visit_date"])
    visits_df["visit_date"] = visits_df["visit_date"].dt.date

    with engine.begin() as conn:                       # one transaction: all or nothing
        bulk_insert(conn, departments, pd.read_csv(DATA / "departments.csv"))
        bulk_insert(conn, patients, pd.read_csv(DATA / "patients.csv"))
        bulk_insert(conn, visits, visits_df)
        bulk_insert(conn, measurements, clean)

    print(f"Loaded {len(clean)} valid measurements; rejected {len(rejected)} "
          f"(see data/rejected_measurements.csv)")
    print(rejected["reject_reason"].str.replace(r"[\d.]+", "#", regex=True).value_counts().to_string())


if __name__ == "__main__":
    main()
