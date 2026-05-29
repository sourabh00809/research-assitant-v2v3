from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from ..billing import list_plans
from ..models import BillingCheckoutRequest, BootstrapTenantRequest, RecordUsageRequest, UsageEvent, new_id, utc_now
from ..rate_limit import check_rate_limit
from ..saas import create_single_user_tenant, create_team_membership, usage_summary
from ._state import state

router = APIRouter(tags=["billing"])


@router.post("/api/v1/tenancy/bootstrap")
def bootstrap_tenant(request: BootstrapTenantRequest) -> dict:
    user, team, subscription = create_single_user_tenant(
        email=request.email,
        team_name=request.team_name,
        tier=request.tier,
    )
    membership = create_team_membership(user, team)
    state.store.save_tenant_bundle(user, team, membership, subscription)
    return {
        "user": user.model_dump(mode="json"),
        "team": team.model_dump(mode="json"),
        "membership": membership.model_dump(mode="json"),
        "subscription": subscription.model_dump(mode="json"),
    }


@router.post("/api/v1/usage")
def record_usage(body: RecordUsageRequest, request: Request) -> dict:
    event = state.store.record_usage_event(
        UsageEvent(
            id=new_id("usage"),
            subject_id=body.subject_id,
            kind=body.kind,
            quantity=body.quantity,
            metadata=body.metadata,
            created_at=utc_now(),
        )
    )
    return event.model_dump(mode="json")


@router.get("/api/v1/usage/limits")
def get_usage_limits(subject_id: str, team_id: str | None = None) -> dict:
    events = state.store.list_usage_events(subject_id)
    subscriptions = state.store.list_subscriptions(team_id)
    subscription = subscriptions[0] if subscriptions else None
    if not subscription:
        _, team, subscription = create_single_user_tenant(team_name="Local Workspace")
    return usage_summary(subscription, events)


@router.get("/api/v1/rate-limit")
def rate_limit_status(key: str = "default") -> dict:
    result = check_rate_limit(key)
    if not result["allowed"]:
        raise HTTPException(status_code=429, detail=result)
    return result


@router.get("/api/v1/billing/plans")
def list_billing_plans() -> list[dict]:
    return list_plans()


@router.post("/api/v1/billing/upgrade")
def billing_upgrade(request: BillingCheckoutRequest, http_request: Request) -> dict:
    return {"subscription": {"tier": request.tier, "status": "active"}, "message": f"Upgraded to {request.tier} tier"}
