from pathlib import Path

import pandas as pd

from app.analytics import clean_measurements
from app.rules import COMPOSITE_CODE, RULES, evaluate
from app.validation import validate_measurement


def test_valid_reading_has_no_errors():
    assert validate_measurement("systolic_bp", 120, "mmHg") == []


def test_out_of_range_and_wrong_unit_and_nan_are_rejected():
    assert validate_measurement("body_temp_c", 98.6, "C")            # Fahrenheit typed as Celsius
    assert validate_measurement("heart_rate", 80, "mmHg")            # wrong unit
    assert validate_measurement("spo2", float("nan"), "%")           # missing
    assert validate_measurement("height", 170, "cm")                 # unknown type


def test_rules_fire_and_composite_counts_them():
    result = evaluate({"systolic_bp": 150, "heart_rate": 60, "spo2": 90})
    assert result["SYS_BP_HIGH_V1"] == 1.0 and result["SPO2_LOW_V1"] == 1.0
    assert "HR_OUT_OF_BAND_V1" not in result
    assert result[COMPOSITE_CODE] == 2.0


def test_missing_measurements_do_not_fire_rules():
    assert evaluate({}) == {COMPOSITE_CODE: 0.0}


def test_every_rule_is_documented():
    docs = Path("docs/RULES.md").read_text(encoding="utf-8")
    for rule in RULES:
        assert rule.code in docs, f"{rule.code} missing from docs/RULES.md"


def test_cleaning_removes_bad_rows_and_keeps_first_valid_duplicate():
    df = pd.DataFrame({
        "measurement_id": [1, 2, 3, 4],
        "patient_id": [1, 1, 1, 2],
        "measurement_date": pd.to_datetime(["2025-01-01"] * 4),
        "measure_type": ["heart_rate", "heart_rate", "spo2", "spo2"],
        "value": [80, 80, 150, 97],
        "unit": ["bpm", "bpm", "%", "%"],
    })
    clean, rejected = clean_measurements(df)
    assert sorted(clean["measurement_id"]) == [1, 4]
    assert len(rejected) == 2 and rejected["reject_reason"].notna().all()
