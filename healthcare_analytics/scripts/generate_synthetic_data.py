"""Generate a SYNTHETIC dataset (no real people) as CSV files in data/.

Run:  python -m scripts.generate_synthetic_data
Everything is driven by a fixed random seed so results are reproducible.
A small share of measurement rows is deliberately corrupted (impossible values, wrong
units, missing values, duplicates) so you can practise data cleaning.
"""
from pathlib import Path

import numpy as np
import pandas as pd

from app.constants import AGE_BANDS
from app.validation import MEASURE_SPECS

SEED, N_PATIENTS, N_VISITS, YEAR = 42, 500, 3000, 2025
OUT = Path("data")

DEPARTMENTS = ["Emergency", "General Medicine", "Cardiology", "Orthopedics", "Pediatrics"]
# probability of each department (same order as DEPARTMENTS) for each age band
DEPT_WEIGHTS = {
    "0-17":  [0.30, 0.20, 0.02, 0.08, 0.40],
    "18-34": [0.35, 0.35, 0.05, 0.25, 0.00],
    "35-49": [0.30, 0.35, 0.12, 0.23, 0.00],
    "50-64": [0.25, 0.30, 0.25, 0.20, 0.00],
    "65+":   [0.25, 0.25, 0.35, 0.15, 0.00],
}
ADMISSION_PROB = {"Emergency": 0.35, "Cardiology": 0.25, "General Medicine": 0.12,
                  "Orthopedics": 0.12, "Pediatrics": 0.08}
BAD_VALUES = {"systolic_bp": [0, 999], "diastolic_bp": [0, 450], "heart_rate": [0, 400],
              "body_temp_c": [98.6, 0], "spo2": [150, 0], "blood_glucose": [-1, 5000]}


def make_patients(rng):
    bands = rng.choice(AGE_BANDS, N_PATIENTS, p=[0.12, 0.25, 0.22, 0.22, 0.19])
    return pd.DataFrame({
        "patient_id": np.arange(1, N_PATIENTS + 1),
        "age_band": bands,
        "sex": rng.choice(["female", "male", "other", "unknown"], N_PATIENTS, p=[0.49, 0.49, 0.01, 0.01]),
        "region_code": rng.choice(["R1", "R2", "R3", "R4"], N_PATIENTS),
    })


def make_visits(rng, patients):
    band_of = dict(zip(patients["patient_id"], patients["age_band"]))
    pids = rng.choice(patients["patient_id"], N_VISITS)
    dept_idx = np.array([rng.choice(len(DEPARTMENTS), p=DEPT_WEIGHTS[band_of[p]]) for p in pids])

    month_w = 1 + 0.25 * np.cos(2 * np.pi * np.arange(12) / 12)      # winter peak
    months = rng.choice(12, N_VISITS, p=month_w / month_w.sum()) + 1
    dates = pd.to_datetime(pd.DataFrame({"year": YEAR, "month": months,
                                         "day": rng.integers(1, 29, N_VISITS)}))
    names = np.array(DEPARTMENTS)[dept_idx]
    admitted = rng.random(N_VISITS) < np.array([ADMISSION_PROB[n] for n in names])
    visits = pd.DataFrame({
        "patient_id": pids, "department_id": dept_idx + 1,
        "visit_date": dates.dt.date,
        "visit_type": np.where(admitted, "admission", "outpatient"),
    }).sort_values("visit_date").reset_index(drop=True)
    visits.insert(0, "visit_id", np.arange(1, len(visits) + 1))
    return visits


def make_measurements(rng, patients):
    rows = []
    start = pd.Timestamp(f"{YEAR}-01-01")
    for pid, band in zip(patients["patient_id"], patients["age_band"]):
        k = AGE_BANDS.index(band)                     # older band -> slightly higher BP/glucose
        for day in np.sort(rng.choice(365, rng.integers(3, 9), replace=False)):
            d = (start + pd.Timedelta(days=int(day))).date()
            temp = rng.normal(36.8, 0.35) + (rng.random() < 0.04) * rng.uniform(1.0, 2.2)
            spo2 = min(100.0, rng.normal(97, 1.6)) - (rng.random() < 0.03) * rng.uniform(4, 9)
            gluc = rng.normal(98 + 4 * k, 16) + (rng.random() < 0.06) * rng.uniform(70, 140)
            vals = {
                "systolic_bp": round(rng.normal(112 + 5 * k, 14)),
                "diastolic_bp": round(rng.normal(72 + 2 * k, 9)),
                "heart_rate": round(max(35, rng.normal(74, 11))),
                "body_temp_c": round(temp, 1),
                "spo2": round(spo2),
                "blood_glucose": round(max(40, gluc)),
            }
            for mtype, v in vals.items():
                rows.append({"patient_id": pid, "measurement_date": d, "measure_type": mtype,
                             "value": float(v), "unit": MEASURE_SPECS[mtype]["unit"]})
    m = pd.DataFrame(rows)

    # ---- deliberately corrupt ~2.5 % of rows so cleaning has something to do
    n = len(m)
    for i in rng.choice(n, int(0.015 * n), replace=False):          # impossible values
        m.loc[i, "value"] = float(rng.choice(BAD_VALUES[m.loc[i, "measure_type"]]))
    for i in rng.choice(n, int(0.005 * n), replace=False):          # wrong unit
        m.loc[i, "unit"] = "unknown"
    for i in rng.choice(n, int(0.005 * n), replace=False):          # missing value
        m.loc[i, "value"] = np.nan
    dupes = m.sample(int(0.005 * n), random_state=SEED)             # duplicated readings
    m = pd.concat([m, dupes], ignore_index=True)
    m.insert(0, "measurement_id", np.arange(1, len(m) + 1))
    return m


def main():
    rng = np.random.default_rng(SEED)
    OUT.mkdir(exist_ok=True)
    patients = make_patients(rng)
    visits = make_visits(rng, patients)
    meas = make_measurements(rng, patients)
    pd.DataFrame({"department_id": range(1, len(DEPARTMENTS) + 1),
                  "department_name": DEPARTMENTS}).to_csv(OUT / "departments.csv", index=False)
    patients.to_csv(OUT / "patients.csv", index=False)
    visits.to_csv(OUT / "visits.csv", index=False)
    meas.to_csv(OUT / "measurements_raw.csv", index=False)
    print(f"Wrote {len(patients)} patients, {len(visits)} visits, {len(meas)} raw measurements to {OUT}/")


if __name__ == "__main__":
    main()
