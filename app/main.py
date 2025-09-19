from __future__ import annotations

from fastapi import FastAPI, HTTPException

from . import services
from .models import (
    DashboardSummary,
    DecisionIn,
    EmailIn,
    Subscription,
    TransactionIn,
)

app = FastAPI(title="AI Subscription Assistant")


def get_manager() -> services.SubscriptionManager:  # type: ignore[attr-defined]
    return services.manager


@app.post("/transactions", response_model=Subscription | None)
def register_transaction(payload: TransactionIn) -> Subscription | None:
    return get_manager().register_transaction(payload)


@app.post("/emails")
def ingest_email(payload: EmailIn) -> dict:
    record = get_manager().ingest_email(payload)
    return record.model_dump()


@app.get("/subscriptions", response_model=list[Subscription])
def list_subscriptions() -> list[Subscription]:
    return list(get_manager().subscriptions)


@app.post("/subscriptions/{subscription_id}/decision", response_model=Subscription)
def apply_decision(subscription_id: int, payload: DecisionIn) -> Subscription:
    ids = {sub.id for sub in get_manager().subscriptions}
    if subscription_id not in ids:
        raise HTTPException(status_code=404, detail="Subscription not found")
    return get_manager().apply_decision(subscription_id, payload.decision)


@app.get("/dashboard", response_model=DashboardSummary)
def dashboard() -> DashboardSummary:
    return get_manager().dashboard()
