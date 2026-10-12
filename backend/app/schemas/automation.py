import uuid
from decimal import Decimal
from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class AutomationRuleCreate(BaseModel):
    rule_type: str = Field(..., description="e.g. attendance_alert, fee_overdue, late_fee")
    is_active: bool = True
    config: Dict[str, Any] = Field(default_factory=dict)


class AutomationRuleOut(BaseModel):
    id: uuid.UUID
    rule_type: str
    is_active: bool
    config: Dict[str, Any]
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class LateFeeWaiverRequest(BaseModel):
    installment_id: uuid.UUID
    waiver_amount: Decimal = Field(..., gt=0, description="Amount to waive in INR")
    reason: str = Field(..., min_length=3, description="Administrative reason for fee waiver")


class WebPushSubscribeRequest(BaseModel):
    endpoint: str
    p256dh_key: str
    auth_key: str
