from pydantic import BaseModel, Field
from typing import List, Optional

class RiskFactorItem(BaseModel):
    factor_code: str
    impact: int
    description: str

class TransactionEvaluateRequest(BaseModel):
    user_id: str = Field(..., min_length=2, max_length=64)
    card_last4: str = Field(..., pattern=r'^\d{4}$')
    amount: float = Field(..., gt=0.0)
    currency: Optional[str] = "USD"
    merchant_name: str = Field(..., min_length=2, max_length=120)
    merchant_category: str = Field(..., min_length=2, max_length=80)
    ip_address: Optional[str] = "127.0.0.1"
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    device_id: Optional[str] = "dev_default"
    timestamp_epoch: Optional[float] = None

class TransactionEvaluateResponse(BaseModel):
    transaction_id: str
    user_id: str
    amount: float
    currency: str
    merchant_name: str
    risk_score: int
    decision: str
    risk_factors: List[RiskFactorItem]
    alert_created: bool
    created_at: str

class TransactionDetailOut(BaseModel):
    id: str
    user_id: str
    card_last4: str
    amount: float
    currency: str
    merchant_name: str
    merchant_category: str
    ip_address: Optional[str]
    latitude: float
    longitude: float
    device_id: Optional[str]
    timestamp_epoch: float
    risk_score: int
    decision: str
    risk_factors: List[RiskFactorItem]
    created_at: str

class AlertOut(BaseModel):
    id: str
    transaction_id: str
    user_id: str
    severity: str
    alert_reason: str
    status: str
    created_at: str

class AlertUpdate(BaseModel):
    status: str = Field(..., pattern=r'^(OPEN|RESOLVED|DISMISSED)$')

class RiskSummaryOut(BaseModel):
    total_transactions: int
    approved_count: int
    review_count: int
    blocked_count: int
    block_rate_percentage: float
    total_flagged_volume: float
    open_alerts_count: int
