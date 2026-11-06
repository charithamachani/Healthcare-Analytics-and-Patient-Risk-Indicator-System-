# Indicator rules (illustrative, NOT clinical)

> Educational analytics on synthetic data only. These rules are **not** diagnoses, are **not**
> clinically validated, and must **never** drive real patient-care decisions.

Each rule inspects the **most recent valid reading** of one measurement for a patient. If the
reading is missing, the rule is skipped (it does not fire). Thresholds are arbitrary sample
assumptions chosen so the synthetic data produces a spread of results.

| Rule code | Measurement | Fires when (sample threshold) |
|---|---|---|
| `SYS_BP_HIGH_V1` | systolic_bp | latest value >= 140 mmHg |
| `DIA_BP_HIGH_V1` | diastolic_bp | latest value >= 90 mmHg |
| `HR_OUT_OF_BAND_V1` | heart_rate | latest value < 50 or > 110 bpm |
| `TEMP_HIGH_V1` | body_temp_c | latest value >= 38.0 C |
| `SPO2_LOW_V1` | spo2 | latest value < 92 % |
| `GLUCOSE_HIGH_V1` | blood_glucose | latest value >= 180 mg/dL |
| `FLAG_COUNT_V1` | (all) | the number of the rules above that fired (0-6) |

## How results are stored
`risk_indicators` holds one row per fired rule (`indicator_value = 1`) plus one `FLAG_COUNT_V1`
row per evaluated patient (`indicator_value = count`). Re-running replaces all earlier rows.

## What the numbers mean
"Flag count = 2" only means "two sample rules fired for this synthetic record". It is **not** a
probability, a severity grade or a recommendation.

## Versioning
Change a threshold -> create a new code (e.g. `SYS_BP_HIGH_V2`) and update this file, so past
results stay interpretable. A test fails if a rule exists in code but not in this file.

## Measurement validation ranges (plausibility only)
| Measurement | Unit | Accepted range |
|---|---|---|
| systolic_bp | mmHg | 50-300 |
| diastolic_bp | mmHg | 30-200 |
| heart_rate | bpm | 20-250 |
| body_temp_c | C | 30-43 |
| spo2 | % | 50-100 |
| blood_glucose | mg/dL | 20-800 |
