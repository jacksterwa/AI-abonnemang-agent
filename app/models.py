from __future__ import annotations

from datetime import datetime, date
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class SubscriptionStatus(str, Enum):
    ACTIVE = "active"
    CANCELLED = "cancelled"


class TransactionIn(BaseModel):
    description: str = Field(..., description="Description as it appears on the bank statement")
    amount: float = Field(..., description="Transaction amount (negative for debit)")
    timestamp: datetime = Field(..., description="When the transaction was posted")


class EmailIn(BaseModel):
    subject: str
    body: str
    timestamp: datetime


class Subscription(BaseModel):
    id: int
    provider: str
    reference: str
    monthly_cost: float
    next_renewal_date: date
    status: SubscriptionStatus = SubscriptionStatus.ACTIVE
    last_transaction_at: datetime
    notes: Optional[str] = None


class SubscriptionDecision(str, Enum):
    CANCEL = "cancel"
    RENEW = "renew"


class DecisionIn(BaseModel):
    decision: SubscriptionDecision


class DashboardSummary(BaseModel):
    active_subscriptions: int
    cancelled_subscriptions: int
    monthly_commitment: float
    total_savings: float
    upcoming_renewals: list[Subscription]


class TransactionRecord(BaseModel):
    description_key: str
    description: str
    amount: float
    timestamp: datetime
    subscription_id: Optional[int] = None


class EmailRecord(BaseModel):
    subject: str
    body: str
    timestamp: datetime
    tags: list[str] = Field(default_factory=list)
