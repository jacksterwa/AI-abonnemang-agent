from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, Iterable, List, Optional

from .models import (
    DashboardSummary,
    EmailIn,
    EmailRecord,
    Subscription,
    SubscriptionDecision,
    SubscriptionStatus,
    TransactionIn,
    TransactionRecord,
)


class SubscriptionManager:
    """In-memory orchestrator for subscription intelligence."""

    def __init__(self) -> None:
        self._transactions: List[TransactionRecord] = []
        self._emails: List[EmailRecord] = []
        self._subscriptions: Dict[int, Subscription] = {}
        self._saved_total: float = 0.0
        self._sequence: int = 0

    # ------------------------------------------------------------------
    # Public accessors
    # ------------------------------------------------------------------
    @property
    def subscriptions(self) -> Iterable[Subscription]:
        return self._subscriptions.values()

    @property
    def saved_total(self) -> float:
        return round(self._saved_total, 2)

    # ------------------------------------------------------------------
    # Command handlers
    # ------------------------------------------------------------------
    def register_transaction(self, tx: TransactionIn) -> Optional[Subscription]:
        description_key = self._normalize_description(tx.description)
        record = TransactionRecord(
            description_key=description_key,
            description=tx.description,
            amount=tx.amount,
            timestamp=tx.timestamp,
        )
        self._transactions.append(record)
        return self._link_transaction(record)

    def ingest_email(self, email: EmailIn) -> EmailRecord:
        tags = self._classify_email(email)
        record = EmailRecord(
            subject=email.subject,
            body=email.body,
            timestamp=email.timestamp,
            tags=tags,
        )
        self._emails.append(record)
        self._maybe_update_subscription_from_email(record)
        return record

    def apply_decision(self, subscription_id: int, decision: SubscriptionDecision) -> Subscription:
        subscription = self._subscriptions[subscription_id]
        if decision is SubscriptionDecision.CANCEL:
            if subscription.status is not SubscriptionStatus.CANCELLED:
                self._saved_total += subscription.monthly_cost
            subscription = subscription.model_copy(update={
                "status": SubscriptionStatus.CANCELLED,
                "notes": "Cancelled via assistant",
            })
        else:
            next_renewal = subscription.next_renewal_date + timedelta(days=30)
            subscription = subscription.model_copy(update={
                "status": SubscriptionStatus.ACTIVE,
                "next_renewal_date": next_renewal,
                "notes": "Renewed via assistant",
            })
        self._subscriptions[subscription_id] = subscription
        return subscription

    def dashboard(self, horizon_days: int = 14) -> DashboardSummary:
        active = [s for s in self._subscriptions.values() if s.status is SubscriptionStatus.ACTIVE]
        cancelled = [s for s in self._subscriptions.values() if s.status is SubscriptionStatus.CANCELLED]
        upcoming_cutoff = datetime.utcnow().date() + timedelta(days=horizon_days)
        upcoming = [
            s for s in active
            if s.next_renewal_date <= upcoming_cutoff
        ]
        monthly_commitment = round(sum(s.monthly_cost for s in active), 2)
        return DashboardSummary(
            active_subscriptions=len(active),
            cancelled_subscriptions=len(cancelled),
            monthly_commitment=monthly_commitment,
            total_savings=self.saved_total,
            upcoming_renewals=sorted(upcoming, key=lambda s: s.next_renewal_date),
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _link_transaction(self, record: TransactionRecord) -> Optional[Subscription]:
        similar = [tx for tx in self._transactions if tx.description_key == record.description_key]
        similar.sort(key=lambda tx: tx.timestamp)
        if len(similar) < 2:
            return None

        latest, previous = similar[-1], similar[-2]
        interval = (latest.timestamp - previous.timestamp).days
        if 27 <= interval <= 33:
            subscription_id = previous.subscription_id or self._create_subscription_from_transaction(similar)
            record.subscription_id = subscription_id
            self._transactions[-1] = record
            self._update_subscription_from_transactions(subscription_id)
            return self._subscriptions[subscription_id]
        return None

    def _create_subscription_from_transaction(self, transactions: List[TransactionRecord]) -> int:
        latest = transactions[-1]
        provider = self._derive_provider_name(latest.description)
        amount = self._average_amount(transactions)
        next_renewal = (latest.timestamp + timedelta(days=30)).date()
        self._sequence += 1
        subscription = Subscription(
            id=self._sequence,
            provider=provider,
            reference=latest.description,
            monthly_cost=round(abs(amount), 2),
            next_renewal_date=next_renewal,
            status=SubscriptionStatus.ACTIVE,
            last_transaction_at=latest.timestamp,
        )
        self._subscriptions[subscription.id] = subscription
        for tx in transactions:
            tx.subscription_id = subscription.id
        return subscription.id

    def _update_subscription_from_transactions(self, subscription_id: int) -> None:
        subscription_transactions = [
            tx for tx in self._transactions if tx.subscription_id == subscription_id
        ]
        latest = max(subscription_transactions, key=lambda tx: tx.timestamp)
        avg_amount = self._average_amount(subscription_transactions)
        next_renewal = (latest.timestamp + timedelta(days=30)).date()
        subscription = self._subscriptions[subscription_id].model_copy(update={
            "monthly_cost": round(abs(avg_amount), 2),
            "next_renewal_date": next_renewal,
            "last_transaction_at": latest.timestamp,
        })
        self._subscriptions[subscription_id] = subscription

    def _maybe_update_subscription_from_email(self, email: EmailRecord) -> None:
        if "price_increase" in email.tags:
            for subscription in self._subscriptions.values():
                note = f"Price increase detected on {email.timestamp.date()}"
                self._subscriptions[subscription.id] = subscription.model_copy(update={"notes": note})
        if "renewal_notice" in email.tags:
            grouped: Dict[str, List[Subscription]] = defaultdict(list)
            for subscription in self._subscriptions.values():
                grouped[subscription.provider.lower()].append(subscription)
            provider = self._derive_provider_name(email.subject)
            matches = grouped.get(provider.lower())
            if matches:
                for subscription in matches:
                    next_date = (email.timestamp + timedelta(days=7)).date()
                    self._subscriptions[subscription.id] = subscription.model_copy(update={
                        "next_renewal_date": next_date,
                        "notes": "Renewal reminder synced from email",
                    })

    @staticmethod
    def _derive_provider_name(reference: str) -> str:
        cleaned = "".join(ch if ch.isalpha() or ch.isspace() else " " for ch in reference)
        tokens = [token for token in cleaned.split() if token]
        return tokens[0].capitalize() if tokens else reference.strip().title()

    @staticmethod
    def _average_amount(records: List[TransactionRecord]) -> float:
        return sum(record.amount for record in records) / len(records)

    @staticmethod
    def _normalize_description(description: str) -> str:
        return "".join(ch.lower() for ch in description if ch.isalnum())

    @staticmethod
    def _classify_email(email: EmailIn) -> List[str]:
        text = f"{email.subject} {email.body}".lower()
        tags: List[str] = []
        if any(keyword in text for keyword in ["renew", "förnya", "fornyelse", "renewal"]):
            tags.append("renewal_notice")
        if any(keyword in text for keyword in ["price increase", "höjs", "higher rate"]):
            tags.append("price_increase")
        return tags


manager = SubscriptionManager()
