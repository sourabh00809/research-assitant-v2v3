from __future__ import annotations

from .config import settings
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
    "free": {"agent_runs": settings.limit_free_agent_runs, "projects": settings.limit_free_projects, "storage_mb": settings.limit_free_storage_mb},
    "pro": {"agent_runs": settings.limit_pro_agent_runs, "projects": settings.limit_pro_projects, "storage_mb": settings.limit_pro_storage_mb},
    "team": {"agent_runs": settings.limit_team_agent_runs, "projects": settings.limit_team_projects, "storage_mb": settings.limit_team_storage_mb},
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


def apply_webhook_event(event: dict, subscription: SubscriptionRecord) -> SubscriptionRecord:
    data = event.get("data", {}).get("object", {}) if isinstance(event.get("data"), dict) else {}
    if data.get("customer"):
        subscription.stripe_customer_id = str(data["customer"])
    if data.get("id") and "subscription" in event.get("type", ""):
        subscription.stripe_subscription_id = str(data["id"])
    metadata = data.get("metadata", {}) or {}
    tier = metadata.get("tier", "")
    if tier in {"free", "pro", "team"}:
        subscription.tier = tier
    event_type = event.get("type", "")
    if event_type.endswith("deleted"):
        subscription.status = "cancelled"
    elif event_type.endswith("payment_failed"):
        subscription.status = "past_due"
    elif event_type:
        subscription.status = "active"
    return subscription


def can_edit(role: str) -> bool:
    return role in {"owner", "admin", "member"}
