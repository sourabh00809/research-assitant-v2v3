from __future__ import annotations

from .models import SubscriptionRecord

TIER_LABELS = {
    "free": {"name": "Free", "desc": "Basic research briefs and project memory.", "price": "₹0"},
    "pro": {"name": "Pro", "desc": "More runs, PDF uploads, better models.", "price": "₹999/mo"},
    "team": {"name": "Team", "desc": "Shared projects, admin controls, collaboration.", "price": "₹2,499/mo"},
}


def list_plans() -> list[dict]:
    return [
        {"tier": tier, "name": info["name"], "desc": info["desc"], "price": info["price"]}
        for tier, info in TIER_LABELS.items()
    ]


def upgrade_subscription(subscription: SubscriptionRecord, tier: str) -> SubscriptionRecord:
    if tier not in TIER_LABELS:
        raise ValueError(f"Invalid tier: {tier}")
    subscription.tier = tier
    subscription.status = "active"
    return subscription
