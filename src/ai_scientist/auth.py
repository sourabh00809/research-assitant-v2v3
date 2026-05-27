from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from dataclasses import dataclass

from fastapi import Request
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware

COOKIE_NAME = "ai_scientist_session"
JWT_COOKIE_NAME = "ai_scientist_jwt"


class PasswordGateMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, password: str):
        super().__init__(app)
        self.password = password
        self.secret = hashlib.sha256(password.encode("utf-8")).hexdigest()

    async def dispatch(self, request: Request, call_next):
        if not self.password or is_public_path(request.url.path):
            return await call_next(request)
        if valid_session(request.cookies.get(COOKIE_NAME, ""), self.secret):
            return await call_next(request)
        if request.url.path.startswith("/api/"):
            return HTMLResponse("Unauthorized", status_code=401)
        return RedirectResponse("/login")


def is_public_path(path: str) -> bool:
    return path in {
        "/login",
        "/api/login",
        "/api/health",
    } or path.startswith("/static/") or path.startswith("/app") or path.startswith("/api/v1/") or path.startswith("/api/projects/")


def make_session(secret: str) -> str:
    nonce = secrets.token_hex(16)
    signature = hmac.new(secret.encode("utf-8"), nonce.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{nonce}.{signature}"


def valid_session(value: str, secret: str) -> bool:
    if "." not in value:
        return False
    nonce, signature = value.split(".", 1)
    expected = hmac.new(secret.encode("utf-8"), nonce.encode("utf-8"), hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature, expected)


@dataclass
class SessionClaims:
    user_id: str
    team_id: str
    role: str
    exp: int


def password_hash(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000)
    return f"pbkdf2_sha256${salt}${base64.urlsafe_b64encode(digest).decode('ascii')}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, salt, encoded = stored.split("$", 2)
    except ValueError:
        return False
    if algo != "pbkdf2_sha256":
        return False
    return hmac.compare_digest(password_hash(password, salt), f"{algo}${salt}${encoded}")


def make_jwt(claims: dict, secret: str, ttl_seconds: int) -> str:
    payload = {**claims, "exp": int(time.time()) + ttl_seconds}
    header = {"alg": "HS256", "typ": "JWT"}
    signing_input = ".".join([_b64_json(header), _b64_json(payload)])
    signature = hmac.new(secret.encode("utf-8"), signing_input.encode("ascii"), hashlib.sha256).digest()
    return f"{signing_input}.{_b64(signature)}"


def decode_jwt(token: str, secret: str) -> SessionClaims | None:
    parts = token.split(".")
    if len(parts) != 3:
        return None
    signing_input = ".".join(parts[:2])
    expected = _b64(hmac.new(secret.encode("utf-8"), signing_input.encode("ascii"), hashlib.sha256).digest())
    if not hmac.compare_digest(expected, parts[2]):
        return None
    try:
        payload = json.loads(base64.urlsafe_b64decode(_pad(parts[1])).decode("utf-8"))
        claims = SessionClaims(
            user_id=str(payload["sub"]),
            team_id=str(payload.get("team_id", "")),
            role=str(payload.get("role", "viewer")),
            exp=int(payload["exp"]),
        )
    except Exception:
        return None
    return claims if claims.exp >= int(time.time()) else None


def _b64_json(value: dict) -> str:
    return _b64(json.dumps(value, separators=(",", ":")).encode("utf-8"))


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _pad(value: str) -> bytes:
    return (value + "=" * (-len(value) % 4)).encode("ascii")


def login_page(error: str = "") -> HTMLResponse:
    message = f"<p class='error'>{error}</p>" if error else ""
    return HTMLResponse(
        f"""<!doctype html>
<html><head><title>Research Assistant Login</title><style>
body{{font-family:system-ui;background:#f6f4ef;color:#18211f;display:grid;place-items:center;height:100vh;margin:0}}
form{{background:white;border:1px solid #d8d6cd;border-radius:8px;padding:28px;display:grid;gap:12px;min-width:320px}}
input,button{{font:inherit;padding:12px;border-radius:6px;border:1px solid #d8d6cd}}
button{{background:#1f7a68;color:white;font-weight:800;cursor:pointer}}
.error{{color:#a8452c;margin:0}}
</style></head><body><form method="post" action="/api/login">
<h1>Research Assistant</h1>{message}
<input name="password" type="password" placeholder="Password" autofocus />
<button type="submit">Enter workspace</button>
</form></body></html>"""
    )
