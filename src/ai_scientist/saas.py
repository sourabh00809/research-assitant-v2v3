from __future__ import annotations

import hashlib

from .models import (
    ProjectMembership,
    SubscriptionRecord,
    Team,
    TeamMembership,
    TenantUser,
    UsageEvent,
    new_id,
    utc_now,
)


DEFAULT_LIMITS = {
    "free": {"agent_runs": 50, "projects": 3, "storage_mb": 250},
    "pro": {"agent_runs": 1000, "projects": 100, "storage_mb": 10000},
    "team": {"agent_runs": 5000, "projects": 1000, "storage_mb": 100000},
}


def create_single_user_tenant(
    email: str = "local@example.com",
    team_name: str = "Local Workspace",
    tier: str = "free",
) -> tuple[TenantUser, Team, SubscriptionRecord]:
    user = TenantUser(
        id=new_id("user"),
        email=email,
        name=email.split("@", 1)[0] or "Local Owner",
        role="owner",
        provider="local",
        created_at=utc_now(),
    )
    team = Team(id=new_id("team"), name=team_name, owner_user_id=user.id, created_at=utc_now())
    subscription = SubscriptionRecord(
        id=new_id("sub"),
        team_id=team.id,
        tier=tier,  # type: ignore[arg-type]
        status="active",
        created_at=utc_now(),
    )
    return user, team, subscription


def create_team_membership(user: TenantUser, team: Team) -> TeamMembership:
    return TeamMembership(id=new_id("tm"), user_id=user.id, team_id=team.id, role="owner", created_at=utc_now())


def create_project_membership(user: TenantUser, project_id: str, team: Team, role: str = "owner") -> ProjectMembership:
    return ProjectMembership(
        id=new_id("pm"),
        project_id=project_id,
        user_id=user.id,
        team_id=team.id,
        role=role,  # type: ignore[arg-type]
        created_at=utc_now(),
    )


def usage_allowed(subscription: SubscriptionRecord, events: list[UsageEvent], kind: str) -> bool:
    limit = DEFAULT_LIMITS[subscription.tier].get(kind)
    if limit is None:
        return True
    used = sum(event.quantity for event in events if event.kind == kind)
    return used < limit


def usage_summary(subscription: SubscriptionRecord, events: list[UsageEvent]) -> dict:
    limits = DEFAULT_LIMITS[subscription.tier]
    usage = {kind: sum(event.quantity for event in events if event.kind == kind) for kind in limits}
    return {
        "team_id": subscription.team_id,
        "tier": subscription.tier,
        "status": subscription.status,
        "limits": limits,
        "usage": usage,
        "allowed": {kind: usage[kind] < limit for kind, limit in limits.items()},
    }


def stripe_webhook_stub(event: dict, subscription: SubscriptionRecord) -> SubscriptionRecord:
    data = event.get("data", {}).get("object", {}) if isinstance(event.get("data"), dict) else {}
    if data.get("customer"):
        subscription.stripe_customer_id = str(data["customer"])
    if data.get("id") and "subscription" in event.get("type", ""):
        subscription.stripe_subscription_id = str(data["id"])
    event_type = event.get("type", "")
    if event_type.endswith("deleted"):
        subscription.status = "cancelled"
    elif event_type.endswith("payment_failed"):
        subscription.status = "past_due"
    elif event_type:
        subscription.status = "active"
    return subscription


def password_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def can_edit(role: str) -> bool:
    return role in {"owner", "admin", "member"}
