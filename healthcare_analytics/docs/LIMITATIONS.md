# Limitations statement

**Educational analytics on synthetic data only. Not medical advice. Not for patient care.**

1. All data is synthetic, produced by a seeded random generator. Patterns in it (including
   the winter peak in visits and the higher blood pressure in older bands) were put there by
   the generator and say nothing about real populations.
2. Indicators are simple rules with arbitrary thresholds. They have not been clinically
   validated, are not diagnoses, and carry no treatment or triage recommendation.
3. Rules use only the latest value of each measurement; they ignore history, symptoms,
   medications, age-specific norms and clinical context.
4. Reported counts and distributions describe this dataset only. No sensitivity, specificity,
   or predictive value is claimed.
5. Validation ranges detect implausible entries (data-entry/unit errors); they are not
   clinical "normal" ranges.
6. Access control (API keys with analyst/admin roles) is a learning-level mechanism. A real
   system would require TLS, audit logs, key rotation, consent management, regulatory review
   (e.g. HIPAA/GDPR/local law) and clinical governance.
7. Do not load real patient data into this project.

## Optional machine-learning extension
If you add scikit-learn, treat it as a *separate, clearly labelled experiment*: split data
into train/test sets, report metrics on the test set only, and state that the labels come
from the synthetic rules themselves, so the model merely re-learns the rules and shows
nothing about real-world prediction.
