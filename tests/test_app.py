from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app import services
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_manager_state():
    services.manager = services.SubscriptionManager()
    yield
    services.manager = services.SubscriptionManager()


def test_subscription_detected_from_transactions():
    now = datetime.utcnow()
    payload = {
        "description": "Spotify ABO",
        "amount": -99.0,
        "timestamp": now.isoformat(),
    }
    response = client.post("/transactions", json=payload)
    assert response.status_code == 200
    assert response.json() is None

    second_payload = {
        "description": "Spotify ABO",
        "amount": -99.0,
        "timestamp": (now + timedelta(days=30)).isoformat(),
    }
    response = client.post("/transactions", json=second_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["provider"] == "Spotify"
    assert data["monthly_cost"] == 99.0


def test_cancel_subscription_updates_savings():
    now = datetime.utcnow()
    client.post(
        "/transactions",
        json={
            "description": "Netflix subscription",
            "amount": -129.0,
            "timestamp": (now - timedelta(days=60)).isoformat(),
        },
    )
    client.post(
        "/transactions",
        json={
            "description": "Netflix subscription",
            "amount": -129.0,
            "timestamp": (now - timedelta(days=30)).isoformat(),
        },
    )

    subscriptions = client.get("/subscriptions").json()
    assert subscriptions
    subscription_id = subscriptions[-1]["id"]

    response = client.post(
        f"/subscriptions/{subscription_id}/decision",
        json={"decision": "cancel"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"

    dashboard = client.get("/dashboard").json()
    assert dashboard["total_savings"] >= 129.0


def test_dashboard_upcoming_renewals_from_email_signal():
    now = datetime.utcnow()
    client.post(
        "/transactions",
        json={
            "description": "Disney+ order",
            "amount": -59.0,
            "timestamp": (now - timedelta(days=60)).isoformat(),
        },
    )
    client.post(
        "/transactions",
        json={
            "description": "Disney+ order",
            "amount": -59.0,
            "timestamp": (now - timedelta(days=30)).isoformat(),
        },
    )

    email_response = client.post(
        "/emails",
        json={
            "subject": "Disney+ renewal reminder",
            "body": "Your subscription will renew soon",
            "timestamp": now.isoformat(),
        },
    )
    assert email_response.status_code == 200

    dashboard = client.get("/dashboard").json()
    assert dashboard["upcoming_renewals"]
    renewal = dashboard["upcoming_renewals"][0]
    assert renewal["notes"] == "Renewal reminder synced from email"
