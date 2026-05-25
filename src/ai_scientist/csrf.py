from __future__ import annotations

import hmac
import secrets

from fastapi import Request
from fastapi.responses import JSONResponse

from .config import settings

CSRF_COOKIE_NAME = "csrf-token"
CSRF_HEADER_NAME = "x-csrf-token"

SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}


def generate_csrf_token() -> str:
    return secrets.token_hex(32)


def validate_csrf(cookie_token: str, header_token: str) -> bool:
    if not cookie_token or not header_token:
        return False
    return hmac.compare_digest(cookie_token, header_token)


async def csrf_middleware(request: Request, call_next):
    if request.method in SAFE_METHODS:
        return await call_next(request)

    if settings.disable_auth:
        return await call_next(request)

    path = request.url.path
    if not path.startswith("/api/v1/"):
        return await call_next(request)
    exempt_prefixes = ("/api/v1/auth/", "/api/v1/billing/webhook")
    if path.startswith(exempt_prefixes):
        return await call_next(request)

    cookie_token = request.cookies.get(CSRF_COOKIE_NAME, "")
    header_token = request.headers.get(CSRF_HEADER_NAME, "")

    if not validate_csrf(cookie_token, header_token):
        return JSONResponse(status_code=403, content={"detail": "CSRF validation failed"})

    return await call_next(request)


def set_csrf_cookie(response, request: Request) -> str:
    existing = request.cookies.get(CSRF_COOKIE_NAME)
    if existing and len(existing) == 64:
        return existing
    token = generate_csrf_token()
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=token,
        httponly=False,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )
    return token
