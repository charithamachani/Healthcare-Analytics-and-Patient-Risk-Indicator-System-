"""Compute the illustrative rule-based indicators.  Run: python -m scripts.run_indicators"""
from app.config import default_database_url
from app.db import get_engine
from app.indicator_service import compute_indicators

if __name__ == "__main__":
    result = compute_indicators(get_engine(default_database_url()))
    print(result)
    print("Reminder: indicators are illustrative, synthetic-data-only, and not clinical.")
