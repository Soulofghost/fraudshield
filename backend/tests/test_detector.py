import time
import pytest
from app.engine.detector import (
    haversine_distance_km,
    calculate_travel_velocity_kmh,
    evaluate_transaction_risk
)

def test_haversine_distance_math():
    # San Francisco (37.7749, -122.4194) to New York (40.7128, -74.0060) ~ 4,129 km
    dist = haversine_distance_km(37.7749, -122.4194, 40.7128, -74.0060)
    assert 4100.0 <= dist <= 4200.0

    # Same location distance is 0.0
    zero_dist = haversine_distance_km(37.7749, -122.4194, 37.7749, -122.4194)
    assert abs(zero_dist) < 1e-4

def test_impossible_travel_velocity():
    # 4,129 km traversed in 15 minutes (0.25 hours) = 16,516 km/h (impossible commercial air speed)
    dist, speed = calculate_travel_velocity_kmh(
        37.7749, -122.4194, 1000.0,
        40.7128, -74.0060, 1900.0
    )
    assert dist > 4000.0
    assert speed > 10000.0

def test_nominal_legitimate_transaction():
    tx = {
        "amount": 25.00,
        "timestamp_epoch": time.time(),
        "latitude": 37.7749,
        "longitude": -122.4194,
        "merchant_category": "coffee_shop",
        "device_id": "phone_alpha"
    }
    history = [
        {"amount": 20.0, "timestamp_epoch": time.time() - 86400, "latitude": 37.7740, "longitude": -122.4180, "device_id": "phone_alpha"},
        {"amount": 35.0, "timestamp_epoch": time.time() - 172800, "latitude": 37.7750, "longitude": -122.4200, "device_id": "phone_alpha"}
    ]
    res = evaluate_transaction_risk(tx, history)
    assert res["decision"] == "APPROVED"
    assert res["risk_score"] < 40
    assert len(res["risk_factors"]) == 0

def test_impossible_travel_anomaly_trigger():
    now = time.time()
    prev_tx = {
        "amount": 45.0,
        "timestamp_epoch": now - 900,  # 15 minutes ago
        "latitude": 37.7749,           # San Francisco
        "longitude": -122.4194,
        "device_id": "phone_alpha"
    }
    curr_tx = {
        "amount": 450.0,
        "timestamp_epoch": now,
        "latitude": 35.6762,           # Tokyo
        "longitude": 139.6503,
        "merchant_category": "electronics_retail",
        "device_id": "phone_beta"
    }

    res = evaluate_transaction_risk(curr_tx, [prev_tx])
    factor_codes = [f["factor_code"] for f in res["risk_factors"]]
    assert "IMPOSSIBLE_TRAVEL" in factor_codes
    assert res["risk_score"] >= 45

def test_velocity_burst_carding_pattern():
    now = time.time()
    history = [
        {"amount": 5.0, "timestamp_epoch": now - 120, "latitude": 40.71, "longitude": -74.00, "device_id": "laptop"},
        {"amount": 10.0, "timestamp_epoch": now - 240, "latitude": 40.71, "longitude": -74.00, "device_id": "laptop"}
    ]
    curr_tx = {
        "amount": 12.0,
        "timestamp_epoch": now,
        "latitude": 40.71,
        "longitude": -74.00,
        "merchant_category": "digital_gift_card",
        "device_id": "laptop"
    }
    res = evaluate_transaction_risk(curr_tx, history)
    factor_codes = [f["factor_code"] for f in res["risk_factors"]]
    assert "VELOCITY_SPIKE" in factor_codes

def test_statistical_amount_outlier():
    now = time.time()
    history = [
        {"amount": 15.0, "timestamp_epoch": now - 100000, "latitude": 40.71, "longitude": -74.00, "device_id": "d1"},
        {"amount": 22.0, "timestamp_epoch": now - 200000, "latitude": 40.71, "longitude": -74.00, "device_id": "d1"},
        {"amount": 18.0, "timestamp_epoch": now - 300000, "latitude": 40.71, "longitude": -74.00, "device_id": "d1"}
    ]
    curr_tx = {
        "amount": 3500.0,  # ~175x historical mean
        "timestamp_epoch": now,
        "latitude": 40.71,
        "longitude": -74.00,
        "merchant_category": "luxury_goods",
        "device_id": "d1"
    }
    res = evaluate_transaction_risk(curr_tx, history)
    factor_codes = [f["factor_code"] for f in res["risk_factors"]]
    assert "STATISTICAL_AMOUNT_ANOMALY" in factor_codes
    assert res["decision"] in ("REVIEW", "BLOCKED")
