"""ILLUSTRATIVE rule-based indicators.

Each rule looks at the MOST RECENT value of one measurement type and returns True/False.
The thresholds are arbitrary sample assumptions chosen for teaching. They are NOT clinical
criteria. A patient's composite value (FLAG_COUNT_V1) is simply "how many rules fired",
meaning "worth a human looking at the record" in this teaching scenario, nothing more.
"""
from dataclasses import dataclass
from typing import Callable, Mapping


@dataclass(frozen=True)
class Rule:
    code: str
    measure_type: str
    description: str
    test: Callable[[float], bool]


RULES = (
    Rule("SYS_BP_HIGH_V1", "systolic_bp", "Latest systolic BP >= 140 mmHg (sample threshold)", lambda v: v >= 140),
    Rule("DIA_BP_HIGH_V1", "diastolic_bp", "Latest diastolic BP >= 90 mmHg (sample threshold)", lambda v: v >= 90),
    Rule("HR_OUT_OF_BAND_V1", "heart_rate", "Latest heart rate < 50 or > 110 bpm (sample thresholds)", lambda v: v < 50 or v > 110),
    Rule("TEMP_HIGH_V1", "body_temp_c", "Latest body temperature >= 38.0 C (sample threshold)", lambda v: v >= 38.0),
    Rule("SPO2_LOW_V1", "spo2", "Latest oxygen saturation < 92 % (sample threshold)", lambda v: v < 92),
    Rule("GLUCOSE_HIGH_V1", "blood_glucose", "Latest blood glucose >= 180 mg/dL (sample threshold)", lambda v: v >= 180),
)

COMPOSITE_CODE = "FLAG_COUNT_V1"
COMPOSITE_DESCRIPTION = "Number of rules above that fired for the patient (0 to %d)." % len(RULES)


def evaluate(latest_values: Mapping[str, float]) -> dict:
    """Apply every rule to a patient's latest values.

    Returns {rule_code: 1.0} for each rule that fired, plus the composite count.
    Rules whose measurement is missing are skipped (not counted as fired).
    """
    results = {}
    for rule in RULES:
        value = latest_values.get(rule.measure_type)
        if value is not None and rule.test(float(value)):
            results[rule.code] = 1.0
    results[COMPOSITE_CODE] = float(len(results))
    return results


def describe_rules() -> list:
    rules = [
        {"rule_code": r.code, "measure_type": r.measure_type, "description": r.description}
        for r in RULES
    ]
    rules.append({"rule_code": COMPOSITE_CODE, "measure_type": "(all)", "description": COMPOSITE_DESCRIPTION})
    return rules
