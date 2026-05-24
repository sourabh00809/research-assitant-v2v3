from __future__ import annotations

import hmac
import hashlib

from .config import settings
from .models import SubscriptionRecord
from .saas import stripe_webhook_stub


PRICE_BY_TIER = {
    "free": lambda: settings.stripe_price_free,
    "pro": lambda: settings.stripe_price_pro,
    "team": lambda: settings.stripe_price_team,
}


def create_checkout_session(team_id: str, tier: str, success_url: str, cancel_url: str) -> dict:
    price = PRICE_BY_TIER.get(tier, PRICE_BY_TIER["pro"])()
    if settings.stripe_secret_key:
        try:
            import stripe  # type: ignore

            stripe.api_key = settings.stripe_secret_key
            session = stripe.checkout.Session.create(
                mode="subscription",
                line_items=[{"price": price, "quantity": 1}] if price else [],
                success_url=success_url,
                cancel_url=cancel_url,
                client_reference_id=team_id,
                metadata={"team_id": team_id, "tier": tier},
            )
            return {"provider": "stripe", "url": session.url, "id": session.id, "tier": tier}
        except Exception as exc:
            return {"provider": "stripe", "url": "", "id": "", "tier": tier, "error": str(exc)}
    return {
        "provider": "stripe-test-stub",
        "url": f"{success_url}&team_id={team_id}&tier={tier}",
        "id": f"cs_test_{team_id}",
        "tier": tier,
    }


def create_portal_session(team_id: str, return_url: str) -> dict:
    return {"provider": "stripe-test-stub", "url": f"{return_url}?portal=stub&team_id={team_id}"}


def verify_webhook_signature(payload: bytes, signature: str) -> bool:
    if not settings.stripe_webhook_secret:
        return True
    expected = hmac.new(settings.stripe_webhook_secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature, expected)


def apply_webhook(event: dict, subscription: SubscriptionRecord) -> SubscriptionRecord:
    return stripe_webhook_stub(event, subscription)
