import pytest
from fastapi.testclient import TestClient
from sqlalchemy import insert

from app import create_app
from app.db import departments, metadata

ANALYST = {"X-API-Key": "read-key"}
ADMIN = {"X-API-Key": "write-key"}


@pytest.fixture
def client(tmp_path):
    app = create_app({"DATABASE_URL": f"sqlite:///{tmp_path / 't.db'}",
                      "API_KEYS": {"read-key": "analyst", "write-key": "admin"}})
    engine = app.state.engine
    metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(insert(departments), [{"department_name": "Emergency"}])
    return TestClient(app)


def test_public_endpoints_show_limitations_and_rules(client):
    assert client.get("/api/limitations").status_code == 200
    body = client.get("/api/rules").json()
    assert "disclaimer" in body and any(r["rule_code"] == "SPO2_LOW_V1" for r in body["data"]["rules"])


def test_dashboard_page_is_served_with_disclaimer(client):
    page = client.get("/dashboard")
    assert page.status_code == 200 and "SYNTHETIC DATA ONLY" in page.text


def test_access_is_restricted(client):
    assert client.get("/api/patients").status_code == 401
    assert client.get("/api/patients", headers={"X-API-Key": "nope"}).status_code == 401
    assert client.get("/api/patients", headers=ANALYST).status_code == 200
    r = client.post("/api/patients", json={"age_band": "18-34"}, headers=ANALYST)
    assert r.status_code == 403


def test_identifying_fields_are_rejected(client):
    r = client.post("/api/patients", json={"age_band": "18-34", "name": "Jane Doe"}, headers=ADMIN)
    assert r.status_code == 400 and "name" in r.json()["error"]


def test_full_flow_validation_duplicates_and_indicators(client):
    pid = client.post("/api/patients", json={"age_band": "65+", "sex": "female"},
                      headers=ADMIN).json()["data"]["patient_id"]

    bad = client.post("/api/measurements", headers=ADMIN, json={
        "patient_id": pid, "measurement_date": "2025-03-01",
        "measure_type": "body_temp_c", "value": 98.6, "unit": "C"})
    assert bad.status_code == 422 and bad.json()["details"]

    good = {"patient_id": pid, "measurement_date": "2025-03-01",
            "measure_type": "systolic_bp", "value": 155, "unit": "mmHg"}
    assert client.post("/api/measurements", headers=ADMIN, json=good).status_code == 201
    assert client.post("/api/measurements", headers=ADMIN, json=good).status_code == 409

    assert client.post("/api/visits", headers=ADMIN, json={
        "patient_id": pid, "department_id": 1, "visit_date": "2025-03-01",
        "visit_type": "admission"}).status_code == 201

    assert client.get("/api/analytics/indicator-summary", headers=ANALYST).status_code == 404
    run = client.post("/api/indicators/run", headers=ADMIN).json()["data"]
    assert run["patients_evaluated"] == 1

    summary = client.get("/api/analytics/indicator-summary", headers=ANALYST).json()
    assert summary["data"]["patients_per_rule"] == {"SYS_BP_HIGH_V1": 1}
    assert "limitations" in summary and "disclaimer" in summary

    dept = client.get("/api/analytics/visits-by-department", headers=ANALYST).json()["data"]
    assert dept[0]["admissions"] == 1
    assert client.get("/api/analytics/overview", headers=ANALYST).json()["data"]["patients"] == 1
    trends = client.get("/api/analytics/measurement-trends", headers=ANALYST).json()["data"]
    assert trends[0]["measure_type"] == "systolic_bp" and trends[0]["month"] == "2025-03"


def test_whoami_reports_role_and_requires_key(client):
    assert client.get("/api/whoami").status_code == 401
    assert client.get("/api/whoami", headers=ANALYST).json()["data"]["role"] == "analyst"
    assert client.get("/api/whoami", headers=ADMIN).json()["data"]["role"] == "admin"
