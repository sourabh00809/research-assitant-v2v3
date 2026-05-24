from __future__ import annotations


ROLE_ORDER = {"viewer": 0, "member": 1, "admin": 2, "owner": 3}


def can_read(role: str) -> bool:
    return ROLE_ORDER.get(role, -1) >= ROLE_ORDER["viewer"]


def can_write(role: str) -> bool:
    return ROLE_ORDER.get(role, -1) >= ROLE_ORDER["member"]


def can_admin(role: str) -> bool:
    return ROLE_ORDER.get(role, -1) >= ROLE_ORDER["admin"]


def require_role(role: str, minimum: str) -> None:
    from fastapi import HTTPException

    if ROLE_ORDER.get(role, -1) < ROLE_ORDER[minimum]:
        raise HTTPException(status_code=403, detail=f"Requires {minimum} role")
