import json
import time
import uuid
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query

from app.database import get_db_connection
from app.schemas import (
    TransactionEvaluateRequest,
    TransactionEvaluateResponse,
    TransactionDetailOut,
    RiskFactorItem,
    AlertOut,
    AlertUpdate,
    RiskSummaryOut
)
from app.engine.detector import evaluate_transaction_risk

router = APIRouter(prefix="/api", tags=["transactions-and-fraud"])

@router.post("/transactions/evaluate", response_model=TransactionEvaluateResponse, status_code=201)
def evaluate_transaction(payload: TransactionEvaluateRequest):
    tx_time = payload.timestamp_epoch or time.time()
    conn = get_db_connection()

    # Query historical transactions for user
    history_rows = conn.execute("""
        SELECT * FROM transactions
        WHERE user_id = ?
        ORDER BY timestamp_epoch DESC
        LIMIT 25
    """, (payload.user_id,)).fetchall()

    history = [dict(r) for r in history_rows]

    tx_data = {
        "amount": payload.amount,
        "timestamp_epoch": tx_time,
        "latitude": payload.latitude,
        "longitude": payload.longitude,
        "merchant_category": payload.merchant_category,
        "device_id": payload.device_id
    }

    eval_result = evaluate_transaction_risk(tx_data, history)
    risk_score = eval_result["risk_score"]
    decision = eval_result["decision"]
    factors = eval_result["risk_factors"]

    tx_id = str(uuid.uuid4())
    factors_json = json.dumps(factors)
    alert_created = False

    with conn:
        conn.execute("""
            INSERT INTO transactions (
                id, user_id, card_last4, amount, currency, merchant_name, merchant_category,
                ip_address, latitude, longitude, device_id, timestamp_epoch, risk_score, decision, risk_factors
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            tx_id, payload.user_id, payload.card_last4, payload.amount, payload.currency or "USD",
            payload.merchant_name, payload.merchant_category, payload.ip_address,
            payload.latitude, payload.longitude, payload.device_id, tx_time,
            risk_score, decision, factors_json
        ))

        # Create alert if flagged
        if decision in ("REVIEW", "BLOCKED"):
            alert_id = str(uuid.uuid4())
            severity = "CRITICAL" if decision == "BLOCKED" else "MEDIUM"
            reasons = "; ".join(f["description"] for f in factors) or f"Flagged with risk score {risk_score}"
            conn.execute("""
                INSERT INTO alerts (id, transaction_id, user_id, severity, alert_reason, status)
                VALUES (?, ?, ?, ?, ?, 'OPEN')
            """, (alert_id, tx_id, payload.user_id, severity, reasons))
            alert_created = True

    inserted_tx = conn.execute("SELECT * FROM transactions WHERE id = ?", (tx_id,)).fetchone()

    return TransactionEvaluateResponse(
        transaction_id=tx_id,
        user_id=payload.user_id,
        amount=payload.amount,
        currency=payload.currency or "USD",
        merchant_name=payload.merchant_name,
        risk_score=risk_score,
        decision=decision,
        risk_factors=[RiskFactorItem(**f) for f in factors],
        alert_created=alert_created,
        created_at=str(inserted_tx["created_at"])
    )

@router.get("/transactions", response_model=List[TransactionDetailOut])
def list_transactions(
    user_id: Optional[str] = None,
    decision: Optional[str] = None,
    min_score: Optional[int] = Query(None, ge=0, le=100)
):
    conn = get_db_connection()
    sql = "SELECT * FROM transactions WHERE 1=1"
    params = []

    if user_id:
        sql += " AND user_id = ?"
        params.append(user_id)
    if decision:
        sql += " AND decision = ?"
        params.append(decision)
    if min_score is not None:
        sql += " AND risk_score >= ?"
        params.append(min_score)

    sql += " ORDER BY timestamp_epoch DESC LIMIT 50"
    rows = conn.execute(sql, params).fetchall()

    results = []
    for r in rows:
        factors = json.loads(r["risk_factors"]) if r["risk_factors"] else []
        results.append(TransactionDetailOut(
            id=r["id"],
            user_id=r["user_id"],
            card_last4=r["card_last4"],
            amount=r["amount"],
            currency=r["currency"],
            merchant_name=r["merchant_name"],
            merchant_category=r["merchant_category"],
            ip_address=r["ip_address"],
            latitude=r["latitude"],
            longitude=r["longitude"],
            device_id=r["device_id"],
            timestamp_epoch=r["timestamp_epoch"],
            risk_score=r["risk_score"],
            decision=r["decision"],
            risk_factors=[RiskFactorItem(**f) for f in factors],
            created_at=str(r["created_at"])
        ))
    return results

@router.get("/transactions/{transaction_id}", response_model=TransactionDetailOut)
def get_transaction(transaction_id: str):
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM transactions WHERE id = ?", (transaction_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Transaction not found")

    factors = json.loads(row["risk_factors"]) if row["risk_factors"] else []
    return TransactionDetailOut(
        id=row["id"],
        user_id=row["user_id"],
        card_last4=row["card_last4"],
        amount=row["amount"],
        currency=row["currency"],
        merchant_name=row["merchant_name"],
        merchant_category=row["merchant_category"],
        ip_address=row["ip_address"],
        latitude=row["latitude"],
        longitude=row["longitude"],
        device_id=row["device_id"],
        timestamp_epoch=row["timestamp_epoch"],
        risk_score=row["risk_score"],
        decision=row["decision"],
        risk_factors=[RiskFactorItem(**f) for f in factors],
        created_at=str(row["created_at"])
    )

@router.get("/alerts", response_model=List[AlertOut])
def list_alerts(status: Optional[str] = None):
    conn = get_db_connection()
    sql = "SELECT * FROM alerts"
    params = []
    if status:
        sql += " WHERE status = ?"
        params.append(status)
    sql += " ORDER BY created_at DESC LIMIT 50"

    rows = conn.execute(sql, params).fetchall()
    return [AlertOut(**dict(r)) for r in rows]

@router.patch("/alerts/{alert_id}", response_model=AlertOut)
def update_alert(alert_id: str, payload: AlertUpdate):
    conn = get_db_connection()
    alert = conn.execute("SELECT * FROM alerts WHERE id = ?", (alert_id,)).fetchone()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    with conn:
        conn.execute("UPDATE alerts SET status = ? WHERE id = ?", (payload.status, alert_id))

    updated = conn.execute("SELECT * FROM alerts WHERE id = ?", (alert_id,)).fetchone()
    return AlertOut(**dict(updated))

@router.get("/analytics/risk-summary", response_model=RiskSummaryOut)
def get_risk_summary():
    conn = get_db_connection()
    total_tx = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
    approved_tx = conn.execute("SELECT COUNT(*) FROM transactions WHERE decision = 'APPROVED'").fetchone()[0]
    review_tx = conn.execute("SELECT COUNT(*) FROM transactions WHERE decision = 'REVIEW'").fetchone()[0]
    blocked_tx = conn.execute("SELECT COUNT(*) FROM transactions WHERE decision = 'BLOCKED'").fetchone()[0]

    block_rate = round((blocked_tx / max(total_tx, 1)) * 100, 1)

    flagged_vol = conn.execute("""
        SELECT COALESCE(SUM(amount), 0.0) FROM transactions WHERE decision IN ('REVIEW', 'BLOCKED')
    """).fetchone()[0]

    open_alerts = conn.execute("SELECT COUNT(*) FROM alerts WHERE status = 'OPEN'").fetchone()[0]

    return RiskSummaryOut(
        total_transactions=total_tx,
        approved_count=approved_tx,
        review_count=review_tx,
        blocked_count=blocked_tx,
        block_rate_percentage=block_rate,
        total_flagged_volume=round(flagged_vol, 2),
        open_alerts_count=open_alerts
    )
