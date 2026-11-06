# Healthcare Analytics and Patient Risk Indicator System

**Educational analytics on synthetic data only. Indicators are not diagnoses and must never
be used for real patient-care decisions.**

Python + FastAPI REST API + MySQL + Pandas/NumPy/Matplotlib + a browser dashboard.

```
generate_synthetic_data -> CSV -> load_data (validate + clean) -> MySQL
                                                                   |
  FastAPI REST API (API-key access) <------------------------------+--> Dashboard (/dashboard)
  run_indicators (rules.py) -> risk_indicators table
  analytics_report (Pandas/NumPy/Matplotlib) -> reports/ (charts + Markdown)
```

## Run it (from the project folder, with the venv active)
```
pip install -r requirements.txt
copy .env.example .env          # then edit .env (see below)
python -m scripts.generate_synthetic_data
python -m scripts.load_data --reset
python -m scripts.run_indicators
python -m scripts.analytics_report
python run.py
```
Then open:
- Dashboard: http://127.0.0.1:8000/dashboard  (enter your API key, click Load dashboard)
- Interactive API docs: http://127.0.0.1:8000/docs  (click Authorize, enter a key)
- Public pages: /api/rules and /api/limitations

## .env examples
SQLite (quick start):
```
DATABASE_URL=sqlite:///health.db
API_KEYS=analyst=analyst-key-12345,admin=admin-key-12345
```
MySQL (run sql/schema.sql in Workbench and create the user first):
```
DATABASE_URL=mysql+pymysql://health_user:YourPassword@localhost:3306/health_analytics
API_KEYS=analyst=analyst-key-12345,admin=admin-key-12345
```
Use long random keys for anything beyond local practice.

## API summary
| Method & path | Role |
|---|---|
| GET `/api/health`, `/api/limitations`, `/api/rules` | none |
| GET `/api/patients`, `/api/patients/{id}`, `/api/patients/{id}/measurements`, `/api/patients/{id}/indicators`, `/api/departments`, `/api/visits` | analyst |
| GET `/api/analytics/overview`, `/visits-by-department`, `/visits-monthly`, `/measurements-summary`, `/measurement-trends`, `/indicator-summary` | analyst |
| POST `/api/patients`, `/api/visits`, `/api/measurements`, `/api/indicators/run` | admin |

Keys go in the `X-API-Key` header. No key or a wrong key gives 401; an analyst trying to write gives 403;
patient fields such as `name` are rejected with 400.

## Files
| Path | Purpose |
|---|---|
| `app/db.py`, `sql/schema.sql` | The 5 tables |
| `app/validation.py` | Documented plausibility ranges |
| `app/rules.py`, `docs/RULES.md` | Visible illustrative indicator rules |
| `app/routes.py`, `app/auth.py` | FastAPI endpoints and role-based API keys |
| `app/analytics.py` | Pandas cleaning/grouping, NumPy statistics |
| `app/static/dashboard.html` | Browser dashboard |
| `scripts/` | Data generation, loading, indicators, report |
| `tests/` | 11 automated tests (`python -m pytest -q`) |
| `docs/LIMITATIONS.md` | Limitations statement |

## Acceptance criteria
- Only synthetic data; identifying fields rejected by the API
- No diagnosis or treatment text; disclaimer on the dashboard and in every analytic response
- Rules and limitations visible (dashboard, `/api/rules`, `/api/limitations`, report section 6)
- Access restricted: API keys, two roles, fail-closed
