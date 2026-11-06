"""REST API (FastAPI). Every analytic/indicator response carries the educational disclaimer."""
import re
from datetime import date, datetime

from fastapi import APIRouter, Body, Depends, Query, Request
from sqlalchemy import insert, select
from sqlalchemy.exc import IntegrityError

from . import analytics
from .auth import require_role
from .constants import (AGE_BANDS, ALLOWED_PATIENT_FIELDS, DISCLAIMER, LIMITATIONS,
                        SEX_VALUES, VISIT_TYPES)
from .db import departments, measurements, patients, risk_indicators, visits
from .errors import ApiError
from .indicator_service import compute_indicators
from .rules import describe_rules
from .validation import MEASURE_SPECS, validate_measurement

router = APIRouter(prefix="/api")
ANALYST = [Depends(require_role("analyst"))]
ADMIN = [Depends(require_role("admin"))]


# ----------------------------------------------------------------------------- helpers
def engine(request: Request):
    return request.app.state.engine


def ok(data, **extra):
    return {"data": data, "disclaimer": DISCLAIMER, **extra}


def serialize(row) -> dict:
    return {k: (v.isoformat() if isinstance(v, (date, datetime)) else v)
            for k, v in dict(row._mapping).items()}


def parse_date(value, field):
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        raise ApiError(400, f"'{field}' must be an ISO date (YYYY-MM-DD)")


def require_existing(conn, column, value, label):
    if conn.execute(select(column).where(column == value)).first() is None:
        raise ApiError(404, f"{label} {value} does not exist")


# ----------------------------------------------------------------------------- public info
@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/whoami")
def whoami(role: str = Depends(require_role("analyst"))):
    return ok({"role": role})


@router.get("/limitations")
def limitations():
    return ok({"limitations": LIMITATIONS})


@router.get("/rules")
def rules():
    return ok({"rules": describe_rules(), "validation_ranges": MEASURE_SPECS,
               "note": "Thresholds are arbitrary teaching assumptions, not clinical criteria."})


# ----------------------------------------------------------------------------- patients
@router.post("/patients", status_code=201, dependencies=ADMIN)
def create_patient(request: Request, payload: dict = Body(...)):
    unknown = set(payload) - ALLOWED_PATIENT_FIELDS
    if unknown:
        raise ApiError(400, "Unsupported field(s): %s. Only de-identified fields are accepted: %s"
                       % (", ".join(sorted(unknown)), ", ".join(sorted(ALLOWED_PATIENT_FIELDS))))
    if payload.get("age_band") not in AGE_BANDS:
        raise ApiError(422, f"age_band must be one of {AGE_BANDS}")
    if payload.get("sex") is not None and payload["sex"] not in SEX_VALUES:
        raise ApiError(422, f"sex must be one of {SEX_VALUES}")
    region = payload.get("region_code")
    if region is not None and not re.fullmatch(r"[A-Z0-9_-]{1,16}", str(region)):
        raise ApiError(422, "region_code must be 1-16 characters: A-Z, 0-9, _ or -")
    with engine(request).begin() as conn:
        result = conn.execute(insert(patients).values(
            age_band=payload["age_band"], sex=payload.get("sex"), region_code=region))
    return ok({"patient_id": result.inserted_primary_key[0]})


@router.get("/patients", dependencies=ANALYST)
def list_patients(request: Request, limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)):
    with engine(request).connect() as conn:
        rows = conn.execute(select(patients).order_by(patients.c.patient_id).limit(limit).offset(offset))
        return ok([serialize(r) for r in rows], limit=limit, offset=offset)


@router.get("/patients/{patient_id}", dependencies=ANALYST)
def get_patient(request: Request, patient_id: int):
    with engine(request).connect() as conn:
        row = conn.execute(select(patients).where(patients.c.patient_id == patient_id)).first()
    if row is None:
        raise ApiError(404, f"patient {patient_id} does not exist")
    return ok(serialize(row))


@router.get("/patients/{patient_id}/measurements", dependencies=ANALYST)
def patient_measurements(request: Request, patient_id: int,
                         limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)):
    with engine(request).connect() as conn:
        require_existing(conn, patients.c.patient_id, patient_id, "patient")
        q = (select(measurements).where(measurements.c.patient_id == patient_id)
             .order_by(measurements.c.measurement_date, measurements.c.measurement_id)
             .limit(limit).offset(offset))
        return ok([serialize(r) for r in conn.execute(q)], limit=limit, offset=offset)


@router.get("/patients/{patient_id}/indicators", dependencies=ANALYST)
def patient_indicators(request: Request, patient_id: int):
    with engine(request).connect() as conn:
        require_existing(conn, patients.c.patient_id, patient_id, "patient")
        rows = conn.execute(select(risk_indicators).where(risk_indicators.c.patient_id == patient_id))
        return ok([serialize(r) for r in rows])


# ----------------------------------------------------------------------------- visits
@router.get("/departments", dependencies=ANALYST)
def list_departments(request: Request):
    with engine(request).connect() as conn:
        return ok([serialize(r) for r in conn.execute(select(departments))])


@router.post("/visits", status_code=201, dependencies=ADMIN)
def create_visit(request: Request, payload: dict = Body(...)):
    visit_date = parse_date(payload.get("visit_date"), "visit_date")
    visit_type = payload.get("visit_type", "outpatient")
    if visit_type not in VISIT_TYPES:
        raise ApiError(422, f"visit_type must be one of {VISIT_TYPES}")
    try:
        patient_id, department_id = int(payload["patient_id"]), int(payload["department_id"])
    except (KeyError, TypeError, ValueError):
        raise ApiError(400, "patient_id and department_id are required integers")
    with engine(request).begin() as conn:
        require_existing(conn, patients.c.patient_id, patient_id, "patient")
        require_existing(conn, departments.c.department_id, department_id, "department")
        result = conn.execute(insert(visits).values(
            patient_id=patient_id, department_id=department_id,
            visit_date=visit_date, visit_type=visit_type))
    return ok({"visit_id": result.inserted_primary_key[0]})


@router.get("/visits", dependencies=ANALYST)
def list_visits(request: Request, department_id: int | None = None,
                date_from: str | None = None, date_to: str | None = None,
                limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)):
    q = select(visits).order_by(visits.c.visit_date, visits.c.visit_id)
    if department_id is not None:
        q = q.where(visits.c.department_id == department_id)
    if date_from:
        q = q.where(visits.c.visit_date >= parse_date(date_from, "date_from"))
    if date_to:
        q = q.where(visits.c.visit_date <= parse_date(date_to, "date_to"))
    with engine(request).connect() as conn:
        rows = conn.execute(q.limit(limit).offset(offset))
        return ok([serialize(r) for r in rows], limit=limit, offset=offset)


# ----------------------------------------------------------------------------- measurements
@router.post("/measurements", status_code=201, dependencies=ADMIN)
def create_measurement(request: Request, payload: dict = Body(...)):
    errors = validate_measurement(payload.get("measure_type"), payload.get("value"), payload.get("unit"))
    if errors:
        raise ApiError(422, "Measurement failed validation", errors)
    try:
        patient_id = int(payload["patient_id"])
    except (KeyError, TypeError, ValueError):
        raise ApiError(400, "patient_id is a required integer")
    measurement_date = parse_date(payload.get("measurement_date"), "measurement_date")
    try:
        with engine(request).begin() as conn:
            require_existing(conn, patients.c.patient_id, patient_id, "patient")
            result = conn.execute(insert(measurements).values(
                patient_id=patient_id, measurement_date=measurement_date,
                measure_type=payload["measure_type"], value=float(payload["value"]),
                unit=payload["unit"]))
    except IntegrityError:
        raise ApiError(409, "A reading for this patient, date and measure_type already exists")
    return ok({"measurement_id": result.inserted_primary_key[0]})


# ----------------------------------------------------------------------------- analytics
@router.get("/analytics/overview", dependencies=ANALYST)
def overview(request: Request):
    f = analytics.load_frames(engine(request))
    return ok({"patients": len(f["patients"]), "visits": len(f["visits"]),
               "admissions": int((f["visits"]["visit_type"] == "admission").sum()),
               "valid_measurements": len(f["measurements"]),
               "indicator_rows": len(f["risk_indicators"])})


@router.get("/analytics/visits-by-department", dependencies=ANALYST)
def visits_by_department(request: Request):
    f = analytics.load_frames(engine(request))
    return ok(analytics.visits_by_department(f["visits"], f["departments"]).to_dict("records"))


@router.get("/analytics/visits-monthly", dependencies=ANALYST)
def visits_monthly(request: Request):
    f = analytics.load_frames(engine(request))
    return ok(analytics.monthly_visits(f["visits"]).to_dict("records"))


@router.get("/analytics/measurements-summary", dependencies=ANALYST)
def measurements_summary(request: Request):
    f = analytics.load_frames(engine(request))
    if f["measurements"].empty:
        return ok([])
    return ok(analytics.measurement_summary(f["measurements"]).to_dict("records"))


@router.get("/analytics/measurement-trends", dependencies=ANALYST)
def measurement_trends(request: Request):
    f = analytics.load_frames(engine(request))
    if f["measurements"].empty:
        return ok([])
    t = analytics.monthly_measurement_trend(f["measurements"])
    t["month"] = t["month"].dt.strftime("%Y-%m")
    t[["mean", "std"]] = t[["mean", "std"]].round(2)
    return ok(t.to_dict("records"))


@router.get("/analytics/indicator-summary", dependencies=ANALYST)
def indicator_summary(request: Request):
    f = analytics.load_frames(engine(request))
    if f["risk_indicators"].empty:
        raise ApiError(404, "No indicators computed yet. An admin can POST /api/indicators/run")
    return ok(analytics.indicator_summary(f["risk_indicators"]), limitations=LIMITATIONS)


@router.post("/indicators/run", dependencies=ADMIN)
def run_indicators(request: Request):
    return ok(compute_indicators(engine(request)))
