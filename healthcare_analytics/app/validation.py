"""Validation of health measurements against DOCUMENTED SAMPLE ASSUMPTIONS.

The ranges below are *plausibility* limits: values outside them are almost certainly
data-entry or unit errors (e.g. 986 instead of 98.6). They are NOT clinical normal ranges.
"""
import math

MEASURE_SPECS = {
    # measure_type:   unit, plausible minimum, plausible maximum
    "systolic_bp":   {"unit": "mmHg",  "min": 50.0, "max": 300.0, "label": "Systolic blood pressure"},
    "diastolic_bp":  {"unit": "mmHg",  "min": 30.0, "max": 200.0, "label": "Diastolic blood pressure"},
    "heart_rate":    {"unit": "bpm",   "min": 20.0, "max": 250.0, "label": "Heart rate"},
    "body_temp_c":   {"unit": "C",     "min": 30.0, "max": 43.0,  "label": "Body temperature"},
    "spo2":          {"unit": "%",     "min": 50.0, "max": 100.0, "label": "Oxygen saturation"},
    "blood_glucose": {"unit": "mg/dL", "min": 20.0, "max": 800.0, "label": "Blood glucose"},
}


def validate_measurement(measure_type, value, unit) -> list:
    """Return a list of human-readable problems. An empty list means the reading is valid."""
    spec = MEASURE_SPECS.get(measure_type)
    if spec is None:
        return [f"unknown measure_type '{measure_type}'"]

    errors = []
    if unit != spec["unit"]:
        errors.append(f"unit must be '{spec['unit']}', got '{unit}'")

    try:
        number = float(value)
    except (TypeError, ValueError):
        errors.append("value is not a number")
        return errors
    if math.isnan(number) or math.isinf(number):
        errors.append("value is missing or not finite")
        return errors

    if not spec["min"] <= number <= spec["max"]:
        errors.append(
            f"value {number:g} outside plausible range {spec['min']:g}-{spec['max']:g} {spec['unit']}"
        )
    return errors
