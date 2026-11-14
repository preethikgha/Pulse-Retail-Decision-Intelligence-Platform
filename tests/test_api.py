import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

GOOD = {
    "estimated_days": 20, "items_value": 120, "freight_value": 25,
    "purchase_hour": 14, "purchase_dow": 2, "purchase_month_num": 5,
    "customer_state": "RJ", "seller_state": "SP", "category": "bed_bath_table",
    "distance_km": 430, "weight_g": 800, "volume_cm3": 6000,
}


def test_health():
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_predict_returns_probability():
    r = client.post("/predict", json=GOOD)
    assert r.status_code == 200
    assert 0.0 <= r.json()["late_probability"] <= 1.0


def test_predict_works_with_missing_optional_fields():
    body = {k: v for k, v in GOOD.items() if k not in ("distance_km", "weight_g", "volume_cm3")}
    assert client.post("/predict", json=body).status_code == 200


def test_predict_rejects_bad_input():
    assert client.post("/predict", json={**GOOD, "purchase_hour": 99}).status_code == 422