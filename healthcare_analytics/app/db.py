"""Database schema (SQLAlchemy Core) and engine factory.

The same definitions work on MySQL (real use) and SQLite (fast automated tests).
sql/schema.sql contains the equivalent hand-written MySQL DDL for learning purposes.
"""
from sqlalchemy import (
    Column, Date, DateTime, Float, ForeignKey, Index, Integer, MetaData, String,
    Table, UniqueConstraint, create_engine,
)

metadata = MetaData()

departments = Table(
    "departments", metadata,
    Column("department_id", Integer, primary_key=True, autoincrement=True),
    Column("department_name", String(64), nullable=False, unique=True),
)

patients = Table(
    "patients", metadata,
    Column("patient_id", Integer, primary_key=True, autoincrement=True),
    Column("age_band", String(16), nullable=False),
    Column("sex", String(16)),
    Column("region_code", String(16)),
)

visits = Table(
    "visits", metadata,
    Column("visit_id", Integer, primary_key=True, autoincrement=True),
    Column("patient_id", Integer, ForeignKey("patients.patient_id"), nullable=False),
    Column("department_id", Integer, ForeignKey("departments.department_id"), nullable=False),
    Column("visit_date", Date, nullable=False),
    Column("visit_type", String(16), nullable=False, default="outpatient"),
    Index("ix_visits_dept_date", "department_id", "visit_date"),
)

measurements = Table(
    "measurements", metadata,
    Column("measurement_id", Integer, primary_key=True, autoincrement=True),
    Column("patient_id", Integer, ForeignKey("patients.patient_id"), nullable=False),
    Column("measurement_date", Date, nullable=False),
    Column("measure_type", String(32), nullable=False),
    Column("value", Float, nullable=False),
    Column("unit", String(16), nullable=False),
    UniqueConstraint("patient_id", "measurement_date", "measure_type", name="uq_measurement"),
    Index("ix_meas_patient_type_date", "patient_id", "measure_type", "measurement_date"),
)

risk_indicators = Table(
    "risk_indicators", metadata,
    Column("indicator_id", Integer, primary_key=True, autoincrement=True),
    Column("patient_id", Integer, ForeignKey("patients.patient_id"), nullable=False),
    Column("rule_code", String(48), nullable=False),
    Column("indicator_value", Float, nullable=False),
    Column("created_at", DateTime, nullable=False),
    Index("ix_ind_rule", "rule_code"),
)


def get_engine(url: str):
    return create_engine(url, pool_pre_ping=True)
