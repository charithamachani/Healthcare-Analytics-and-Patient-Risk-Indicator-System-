"""Compute rule-based indicators for every patient and store them in risk_indicators."""
from datetime import datetime, timezone

from sqlalchemy import delete, insert

from .analytics import clean_measurements, latest_measurements, load_frames
from .db import risk_indicators
from .rules import evaluate


def compute_indicators(engine) -> dict:
    frames = load_frames(engine)
    clean, _ = clean_measurements(frames["measurements"])   # defence in depth
    if clean.empty:
        latest = None
    else:
        latest = latest_measurements(clean)

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    rows = []
    if latest is not None:
        for patient_id, series in latest.iterrows():
            values = {k: float(v) for k, v in series.items() if v == v}  # v == v drops NaN
            for code, value in evaluate(values).items():
                rows.append({"patient_id": int(patient_id), "rule_code": code,
                             "indicator_value": value, "created_at": now})

    with engine.begin() as conn:                 # one transaction: replace old results atomically
        conn.execute(delete(risk_indicators))
        if rows:
            conn.execute(insert(risk_indicators), rows)
    return {"patients_evaluated": 0 if latest is None else int(len(latest)), "rows_written": len(rows)}
