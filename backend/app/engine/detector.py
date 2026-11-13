import math
import time
from typing import List, Dict, Any, Tuple, Optional

EARTH_RADIUS_KM = 6371.0

def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculates great-circle distance between two geographic coordinates in kilometers.
    """
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2))
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))
    return EARTH_RADIUS_KM * c

def calculate_travel_velocity_kmh(prev_lat: float, prev_lon: float, prev_time: float,
                                 curr_lat: float, curr_lon: float, curr_time: float) -> Tuple[float, float]:
    """
    Returns (distance_km, speed_kmh) between two timestamped events.
    """
    dist_km = haversine_distance_km(prev_lat, prev_lon, curr_lat, curr_lon)
    time_diff_hours = abs(curr_time - prev_time) / 3600.0
    if time_diff_hours < 0.001:
        # Near instantaneous
        speed_kmh = dist_km / 0.001 if dist_km > 5.0 else 0.0
    else:
        speed_kmh = dist_km / time_diff_hours
    return dist_km, speed_kmh

def evaluate_transaction_risk(
    transaction: Dict[str, Any],
    user_history: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Comprehensive multi-factor anomaly scoring pipeline.
    """
    score = 0
    factors: List[Dict[str, Any]] = []

    curr_amount = float(transaction.get("amount", 0.0))
    curr_time = float(transaction.get("timestamp_epoch", time.time()))
    curr_lat = float(transaction.get("latitude", 0.0))
    curr_lon = float(transaction.get("longitude", 0.0))
    curr_merchant_cat = str(transaction.get("merchant_category", "")).lower()
    curr_device = transaction.get("device_id")

    # 1. High-Risk Merchant Category Check
    high_risk_categories = {"cryptocurrency_exchange", "wire_transfer", "gambling_casino", "luxury_jewelry"}
    if curr_merchant_cat in high_risk_categories:
        score += 25
        factors.append({
            "factor_code": "HIGH_RISK_MERCHANT",
            "impact": 25,
            "description": f"Merchant category '{curr_merchant_cat}' carries elevated chargeback risk."
        })

    # 2. Large Transaction Threshold
    if curr_amount >= 5000.0:
        score += 25
        factors.append({
            "factor_code": "HIGH_VALUE_TRANSACTION",
            "impact": 25,
            "description": f"Transaction amount ${curr_amount:,.2f} exceeds high-value threshold ($5,000)."
        })

    # Analyze against user history if available
    if user_history:
        sorted_history = sorted(user_history, key=lambda x: x["timestamp_epoch"], reverse=True)
        prev_tx = sorted_history[0]

        # 3. Impossible Travel Geo-Velocity
        dist_km, speed_kmh = calculate_travel_velocity_kmh(
            prev_tx["latitude"], prev_tx["longitude"], prev_tx["timestamp_epoch"],
            curr_lat, curr_lon, curr_time
        )

        if dist_km > 150.0 and speed_kmh > 800.0:
            score += 45
            factors.append({
                "factor_code": "IMPOSSIBLE_TRAVEL",
                "impact": 45,
                "description": f"Physical displacement of {dist_km:.1f} km at implied speed of {speed_kmh:.0f} km/h exceeds commercial air travel limit."
            })

        # 4. Velocity Spike (Short Window <= 10 mins)
        ten_mins_ago = curr_time - 600
        recent_txs = [t for t in sorted_history if t["timestamp_epoch"] >= ten_mins_ago]
        if len(recent_txs) >= 2:
            score += 35
            factors.append({
                "factor_code": "VELOCITY_SPIKE",
                "impact": 35,
                "description": f"{len(recent_txs) + 1} transactions recorded within 10-minute window (card testing pattern)."
            })

        # 5. Statistical Amount Outlier (Z-Score)
        past_amounts = [float(t["amount"]) for t in sorted_history]
        mean_amount = sum(past_amounts) / len(past_amounts)
        variance = sum((x - mean_amount) ** 2 for x in past_amounts) / max(len(past_amounts), 1)
        std_dev = math.sqrt(variance)

        z_score = (curr_amount - mean_amount) / max(std_dev, 15.0)
        if z_score >= 3.0 and curr_amount > 200.0:
            score += 40
            factors.append({
                "factor_code": "STATISTICAL_AMOUNT_ANOMALY",
                "impact": 40,
                "description": f"Amount is {z_score:.1f} standard deviations above user historical mean (${mean_amount:.2f})."
            })

        # 6. Unrecognized Device & IP
        known_devices = {t.get("device_id") for t in sorted_history if t.get("device_id")}
        if curr_device and known_devices and curr_device not in known_devices:
            score += 15
            factors.append({
                "factor_code": "NEW_DEVICE_ACCESS",
                "impact": 15,
                "description": f"Transaction initiated from previously unseen device signature '{curr_device}'."
            })

    final_score = min(100, max(0, score))

    # Decision thresholds: >= 70 BLOCKED, >= 35 REVIEW, < 35 APPROVED
    if final_score >= 70:
        decision = "BLOCKED"
    elif final_score >= 35:
        decision = "REVIEW"
    else:
        decision = "APPROVED"

    return {
        "risk_score": final_score,
        "decision": decision,
        "risk_factors": factors
    }
