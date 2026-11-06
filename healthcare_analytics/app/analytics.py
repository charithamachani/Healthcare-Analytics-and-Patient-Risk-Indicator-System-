"""Pandas / NumPy analytics shared by the REST API and the report script."""
import numpy as np
import pandas as pd
from sqlalchemy import select

from .db import departments, measurements, patients, risk_indicators, visits
from .rules import COMPOSITE_CODE
from .validation import validate_measurement

KEY_COLUMNS = ["patient_id", "measurement_date", "measure_type"]


def load_frames(engine) -> dict:
    """Read every table into a DataFrame and make the date columns real datetimes."""
    tables = {
        "departments": departments, "patients": patients, "visits": visits,
        "measurements": measurements, "risk_indicators": risk_indicators,
    }
    with engine.connect() as conn:
        frames = {name: pd.read_sql(select(table), conn) for name, table in tables.items()}
    frames["visits"]["visit_date"] = pd.to_datetime(frames["visits"]["visit_date"])
    frames["measurements"]["measurement_date"] = pd.to_datetime(frames["measurements"]["measurement_date"])
    return frames


# ----------------------------------------------------------------------------- cleaning
def clean_measurements(df: pd.DataFrame):
    """Split raw measurements into (clean, rejected). Rejected rows get a 'reject_reason'.

    Steps: coerce values to numbers -> validate range/unit -> drop duplicate readings.
    """
    df = df.copy()
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    reason = df.apply(
        lambda r: "; ".join(validate_measurement(r["measure_type"], r["value"], r["unit"])), axis=1
    )
    # Duplicates are only judged among otherwise-valid rows, so a bad first reading
    # cannot cause a good second reading to be thrown away.
    valid = reason == ""
    dup = df[valid].duplicated(subset=KEY_COLUMNS, keep="first")
    reason.loc[dup[dup].index] = "duplicate reading for same patient/date/measure"

    clean = df[reason == ""].copy()
    rejected = df[reason != ""].copy()
    rejected["reject_reason"] = reason[reason != ""]
    return clean, rejected


# ----------------------------------------------------------------------------- operations
def visits_by_department(visits_df: pd.DataFrame, departments_df: pd.DataFrame) -> pd.DataFrame:
    merged = visits_df.merge(departments_df, on="department_id", how="left")
    out = (
        merged.groupby("department_name")
        .agg(visits=("visit_id", "count"),
             admissions=("visit_type", lambda s: int((s == "admission").sum())))
        .reset_index()
        .sort_values("visits", ascending=False)
    )
    out["admission_rate"] = (out["admissions"] / out["visits"]).round(3)
    return out.reset_index(drop=True)


def monthly_visits(visits_df: pd.DataFrame) -> pd.DataFrame:
    month = visits_df["visit_date"].dt.to_period("M").astype(str)
    out = (
        visits_df.assign(month=month)
        .groupby("month")
        .agg(visits=("visit_id", "count"),
             admissions=("visit_type", lambda s: int((s == "admission").sum())))
        .reset_index()
    )
    return out


def monthly_visits_by_department(visits_df, departments_df) -> pd.DataFrame:
    merged = visits_df.merge(departments_df, on="department_id", how="left")
    merged["month"] = merged["visit_date"].dt.to_period("M").astype(str)
    return merged.pivot_table(index="month", columns="department_name",
                              values="visit_id", aggfunc="count", fill_value=0)


# ----------------------------------------------------------------------------- measurements
def measurement_summary(meas_df: pd.DataFrame) -> pd.DataFrame:
    """Per measure type statistics computed with NumPy."""
    rows = []
    for measure_type, group in meas_df.groupby("measure_type"):
        v = group["value"].to_numpy(dtype=float)
        p25, p50, p75 = np.percentile(v, [25, 50, 75])
        rows.append({
            "measure_type": measure_type, "n": int(v.size),
            "mean": round(float(np.mean(v)), 2),
            "std": round(float(np.std(v, ddof=1)) if v.size > 1 else 0.0, 2),
            "min": round(float(np.min(v)), 2), "p25": round(float(p25), 2),
            "median": round(float(p50), 2), "p75": round(float(p75), 2),
            "max": round(float(np.max(v)), 2),
        })
    return pd.DataFrame(rows)


def monthly_measurement_trend(meas_df: pd.DataFrame) -> pd.DataFrame:
    month = meas_df["measurement_date"].dt.to_period("M").dt.to_timestamp()
    return (
        meas_df.assign(month=month)
        .groupby(["measure_type", "month"])["value"]
        .agg(mean="mean", std="std", n="count")
        .reset_index()
        .fillna({"std": 0.0})
    )


def latest_measurements(meas_df: pd.DataFrame) -> pd.DataFrame:
    """One row per patient, one column per measure type, holding the MOST RECENT value."""
    ordered = meas_df.sort_values(["measurement_date", "measurement_id"])
    latest = ordered.groupby(["patient_id", "measure_type"]).tail(1)
    return latest.pivot(index="patient_id", columns="measure_type", values="value")


# ----------------------------------------------------------------------------- indicators
def indicator_summary(risk_df: pd.DataFrame) -> dict:
    composite = risk_df[risk_df["rule_code"] == COMPOSITE_CODE]
    counts = composite["indicator_value"].astype(int).value_counts().sort_index()
    total = int(counts.sum())
    distribution = [
        {"flag_count": int(k), "patients": int(v), "share": round(float(v) / total, 3)}
        for k, v in counts.items()
    ]
    fired = risk_df[(risk_df["rule_code"] != COMPOSITE_CODE) & (risk_df["indicator_value"] > 0)]
    rule_counts = fired.groupby("rule_code")["patient_id"].nunique().sort_values(ascending=False)
    return {
        "patients_evaluated": total,
        "flag_count_distribution": distribution,
        "patients_per_rule": {k: int(v) for k, v in rule_counts.items()},
    }
