import os
import time
import pytest
from fastapi.testclient import TestClient

TEST_DB = "file:fraudshield_test?mode=memory&cache=shared"
os.environ["FRAUDSHIELD_DB_PATH"] = TEST_DB

from app.database import init_db, get_db_connection
from app.main import app

client = TestClient(app)

holding_conn = None

@pytest.fixture(scope="session", autouse=True)
def setup_database_session():
    global holding_conn
    holding_conn = init_db(TEST_DB)
    yield
    if holding_conn:
        holding_conn.close()

def test_health_check():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"
    assert res.json()["service"] == "FraudShield"

def test_transaction_lifecycle_and_alerts():
    # 1. Evaluate normal transaction
    tx1_payload = {
        "user_id": "usr_alpha_101",
        "card_last4": "4242",
        "amount": 18.50,
        "currency": "USD",
        "merchant_name": "Blue Bottle Coffee",
        "merchant_category": "coffee_shop",
        "ip_address": "192.168.1.10",
        "latitude": 37.7749,
        "longitude": -122.4194,
        "device_id": "iphone_15",
        "timestamp_epoch": time.time() - 3600
    }
    res1 = client.post("/api/transactions/evaluate", json=tx1_payload)
    assert res1.status_code == 201
    d1 = res1.json()
    assert d1["decision"] == "APPROVED"
    assert d1["risk_score"] < 40
    assert d1["alert_created"] is False

    # 2. Evaluate high-risk transaction (crypto merchant + high value)
    tx2_payload = {
        "user_id": "usr_alpha_101",
        "card_last4": "4242",
        "amount": 7500.00,
        "currency": "USD",
        "merchant_name": "Kraken Exchange",
        "merchant_category": "cryptocurrency_exchange",
        "ip_address": "45.33.32.156",
        "latitude": 37.7749,
        "longitude": -122.4194,
        "device_id": "unknown_linux",
        "timestamp_epoch": time.time()
    }
    res2 = client.post("/api/transactions/evaluate", json=tx2_payload)
    assert res2.status_code == 201
    d2 = res2.json()
    assert d2["decision"] in ("REVIEW", "BLOCKED")
    assert d2["risk_score"] >= 40
    assert d2["alert_created"] is True

    # 3. List transactions
    list_res = client.get("/api/transactions?user_id=usr_alpha_101")
    assert list_res.status_code == 200
    txs = list_res.json()
    assert len(txs) == 2

    # 4. Get single transaction detail
    get_res = client.get(f"/api/transactions/{d2['transaction_id']}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == d2["transaction_id"]

    # 5. List alerts
    alerts_res = client.get("/api/alerts?status=OPEN")
    assert alerts_res.status_code == 200
    alerts = alerts_res.json()
    assert len(alerts) >= 1
    alert_id = alerts[0]["id"]

    # 6. Update alert status
    patch_res = client.patch(f"/api/alerts/{alert_id}", json={"status": "RESOLVED"})
    assert patch_res.status_code == 200
    assert patch_res.json()["status"] == "RESOLVED"

    # 7. Verify Risk Summary Analytics
    summary_res = client.get("/api/analytics/risk-summary")
    assert summary_res.status_code == 200
    summary = summary_res.json()
    assert summary["total_transactions"] == 2
    assert summary["approved_count"] == 1
    assert summary["total_flagged_volume"] >= 7500.0

def test_validation_errors():
    # Invalid card number (not 4 digits)
    invalid_payload = {
        "user_id": "usr_bad",
        "card_last4": "12",  # invalid
        "amount": 50.0,
        "merchant_name": "Test",
        "merchant_category": "retail",
        "latitude": 0.0,
        "longitude": 0.0
    }
    res = client.post("/api/transactions/evaluate", json=invalid_payload)
    assert res.status_code == 422
