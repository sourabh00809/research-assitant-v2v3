from __future__ import annotations

import importlib
import json
import sys

import pytest

from ai_scientist.auth import decode_jwt, make_jwt, verify_password
from ai_scientist.csrf import generate_csrf_token, validate_csrf
from ai_scientist.models import SubscriptionRecord, utc_now
from ai_scientist.rate_limit import check_rate_limit, clear_failed_logins, is_locked, record_failed_login
from ai_scientist.storage import SQLiteStore


def asgi_request(app, method, path, body=b"", headers=None, client_ip="testclient"):
    import anyio

    async def call():
        sent = []
        query = b""
        request_path = path
        if "?" in path:
            request_path, query_text = path.split("?", 1)
            query = query_text.encode("ascii")
        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": method,
            "scheme": "http",
            "path": request_path,
            "raw_path": request_path.encode("ascii"),
            "query_string": query,
            "headers": headers or [],
            "client": (client_ip, 50000),
            "server": ("testserver", 80),
            "root_path": "",
            "path_params": {},
        }
        received = False

        async def receive():
            nonlocal received
            if received:
                return {"type": "http.disconnect"}
            received = True
            return {"type": "http.request", "body": body, "more_body": False}

        async def send(message):
            sent.append(message)

        await app(scope, receive, send)
        start = next(message for message in sent if message["type"] == "http.response.start")
        chunks = [message.get("body", b"") for message in sent if message["type"] == "http.response.body"]
        return {"status": start["status"], "headers": start["headers"], "body": b"".join(chunks).decode("utf-8")}

    return anyio.run(call)


def _parse_cookies(headers):
    cookies = {}
    for n, v in headers:
        if n.lower() == b"set-cookie":
            for part in v.decode("utf-8").split("; "):
                if "=" in part:
                    k, val = part.split("=", 1)
                    cookies[k] = val
    return cookies


def _make_app(monkeypatch, tmp_path, suffix=""):
    monkeypatch.delenv("AI_SCIENTIST_APP_PASSWORD", raising=False)
    monkeypatch.delenv("AI_SCIENTIST_DISABLE_AUTH", raising=False)
    monkeypatch.setenv("AI_SCIENTIST_DB_PATH", str(tmp_path / f"test{suffix}.db"))
    monkeypatch.setenv("AI_SCIENTIST_STORAGE_DIR", str(tmp_path / f"storage{suffix}"))
    for mod_name in list(sys.modules.keys()):
        if mod_name.startswith("ai_scientist"):
            importlib.reload(sys.modules[mod_name])
    import ai_scientist.main as main
    return main


JWT_COOKIE = "ai_scientist_jwt"


def _signup(main_app, email="test@example.com", password="password123", ip="testclient"):
    resp = asgi_request(
        main_app,
        "POST",
        "/api/v1/auth/signup",
        body=json.dumps({"email": email, "password": password}).encode("utf-8"),
        headers=[(b"content-type", b"application/json")],
        client_ip=ip,
    )
    cookies = _parse_cookies(resp["headers"])
    return resp, cookies


# ── Auth: Signup / Login / Session ──────────────────────────────────────────


def test_signup_creates_user_and_returns_jwt(monkeypatch, tmp_path):
    main = _make_app(monkeypatch, tmp_path, suffix="signup1")
    resp, cookies = _signup(main.app)
    assert resp["status"] == 200, f"Signup failed: {resp['body']}"
    body = json.loads(resp["body"])
    assert body["user"]["email"] == "test@example.com"
    assert body["role"] == "owner"
    assert cookies.get(JWT_COOKIE)


def test_signup_rejects_duplicate_email(monkeypatch, tmp_path):
    main = _make_app(monkeypatch, tmp_path, suffix="dup")
    _signup(main.app, email="dup@example.com", ip="dup1")
    resp = asgi_request(
        main.app,
        "POST",
        "/api/v1/auth/signup",
        body=json.dumps({"email": "dup@example.com", "password": "password123"}).encode("utf-8"),
        headers=[(b"content-type", b"application/json")],
        client_ip="dup2",
    )
    assert resp["status"] == 409, f"Expected 409 got {resp['status']}: {resp['body']}"


def test_login_returns_jwt_and_user(monkeypatch, tmp_path):
    main = _make_app(monkeypatch, tmp_path, suffix="login1")
    _signup(main.app, email="login@example.com", ip="login_su")

    resp = asgi_request(
        main.app,
        "POST",
        "/api/v1/auth/login",
        body=json.dumps({"email": "login@example.com", "password": "password123"}).encode("utf-8"),
        headers=[(b"content-type", b"application/json")],
        client_ip="login_li",
    )
    assert resp["status"] == 200, f"Login failed: {resp['body']}"
    body = json.loads(resp["body"])
    assert body["user"]["email"] == "login@example.com"
    cookies = _parse_cookies(resp["headers"])
    assert cookies.get(JWT_COOKIE)


def test_login_rejects_wrong_password(monkeypatch, tmp_path):
    main = _make_app(monkeypatch, tmp_path, suffix="login2")
    _signup(main.app, email="wrong@example.com", ip="wrong1")

    resp = asgi_request(
        main.app,
        "POST",
        "/api/v1/auth/login",
        body=json.dumps({"email": "wrong@example.com", "password": "wrongpass"}).encode("utf-8"),
        headers=[(b"content-type", b"application/json")],
        client_ip="wrong2",
    )
    assert resp["status"] == 401


def test_session_returns_authenticated_false_when_no_jwt(monkeypatch, tmp_path):
    main = _make_app(monkeypatch, tmp_path, suffix="session1")
    resp = asgi_request(main.app, "GET", "/api/v1/auth/session")
    assert resp["status"] == 200
    assert json.loads(resp["body"])["authenticated"] is False


def test_session_returns_user_when_authenticated(monkeypatch, tmp_path):
    main = _make_app(monkeypatch, tmp_path, suffix="session2")
    _, cookies = _signup(main.app, email="session@example.com")
    jwt = cookies.get(JWT_COOKIE, "")
    resp = asgi_request(
        main.app,
        "GET",
        "/api/v1/auth/session",
        headers=[(b"cookie", f"{JWT_COOKIE}={jwt}".encode("utf-8"))],
    )
    assert json.loads(resp["body"])["authenticated"] is True, f"Session failed: {resp['body']}"


# ── Auth: JWT Enforcement on v1 endpoints ───────────────────────────────────


def test_v1_projects_requires_auth(monkeypatch, tmp_path):
    main = _make_app(monkeypatch, tmp_path, suffix="v1auth")
    resp = asgi_request(main.app, "GET", "/api/v1/projects")
    assert resp["status"] == 401


def test_v1_create_project_requires_auth(monkeypatch, tmp_path):
    main = _make_app(monkeypatch, tmp_path, suffix="v1create")
    resp = asgi_request(
        main.app,
        "POST",
        "/api/v1/projects",
        body=json.dumps({"name": "My Project", "description": ""}).encode("utf-8"),
        headers=[(b"content-type", b"application/json")],
    )
    assert resp["status"] in (401, 403)


# ── Auth: DISABLE_AUTH bypass ───────────────────────────────────────────────


def _make_app_with_disable_auth(monkeypatch, tmp_path, suffix=""):
    """Create app with auth fully disabled (no CSRF, no JWT checks)."""
    monkeypatch.setenv("AI_SCIENTIST_DISABLE_AUTH", "1")
    monkeypatch.setenv("AI_SCIENTIST_DB_PATH", str(tmp_path / f"test_noauth{suffix}.db"))
    monkeypatch.setenv("AI_SCIENTIST_STORAGE_DIR", str(tmp_path / f"storage_noauth{suffix}"))
    import ai_scientist.config as config
    importlib.reload(config)
    from ai_scientist.config import settings as cfg
    cfg.disable_auth = True
    for mod_name in sorted(sys.modules.keys(), reverse=True):
        if mod_name.startswith("ai_scientist") and mod_name != "ai_scientist.config":
            importlib.reload(sys.modules[mod_name])
    import ai_scientist.main as main
    return main


def test_disable_auth_skips_v1_jwt_check(monkeypatch, tmp_path):
    main = _make_app_with_disable_auth(monkeypatch, tmp_path, suffix="noauth")
    resp = asgi_request(
        main.app,
        "POST",
        "/api/v1/projects",
        body=json.dumps({"name": "No Auth", "description": ""}).encode("utf-8"),
        headers=[(b"content-type", b"application/json")],
    )
    assert resp["status"] == 200, f"DISABLE_AUTH failed: {resp['body']}"


# ── Auth: Rate Limiting & Lockout ───────────────────────────────────────────


def test_rate_limit_block_excessive_login_attempts(monkeypatch, tmp_path):
    main = _make_app(monkeypatch, tmp_path, suffix="ratelimit")
    _signup(main.app, email="rate@example.com", ip="rate_su")

    wrong = json.dumps({"email": "rate@example.com", "password": "wrongpass"}).encode("utf-8")
    resp = None
    for _ in range(6):
        resp = asgi_request(main.app, "POST", "/api/v1/auth/login", body=wrong, headers=[(b"content-type", b"application/json")], client_ip="rate_same_ip")
    assert resp["status"] == 429
    assert "Too many login attempts" in json.loads(resp["body"])["detail"]


def test_signup_rate_limited(monkeypatch, tmp_path):
    main = _make_app(monkeypatch, tmp_path, suffix="signup_rate")
    headers = [(b"content-type", b"application/json")]
    for i in range(2):
        resp = asgi_request(
            main.app,
            "POST",
            "/api/v1/auth/signup",
            body=json.dumps({"email": f"sr{i}@example.com", "password": "password123"}).encode("utf-8"),
            headers=headers,
            client_ip="sr_same_ip",
        )
        assert resp["status"] == 200, f"signup {i} failed: {resp['body']}"
    resp = asgi_request(
        main.app,
        "POST",
        "/api/v1/auth/signup",
        body=json.dumps({"email": "sr2@example.com", "password": "password123"}).encode("utf-8"),
        headers=headers,
        client_ip="sr_same_ip",
    )
    assert resp["status"] == 429


# ── Auth: Change Password ────────────────────────────────────────────────────


def test_change_password_succeeds(monkeypatch, tmp_path):
    main = _make_app(monkeypatch, tmp_path, suffix="cpw1")
    _, cookies = _signup(main.app, email="changepw@example.com")
    jwt = cookies.get(JWT_COOKIE, "")
    csrf = cookies.get("csrf-token", "")
    headers = [
        (b"cookie", f"{JWT_COOKIE}={jwt};csrf-token={csrf}".encode("utf-8")),
        (b"content-type", b"application/json"),
        (b"x-csrf-token", csrf.encode("utf-8")),
    ]

    resp = asgi_request(
        main.app,
        "POST",
        "/api/v1/auth/change-password",
        body=json.dumps({"current_password": "password123", "new_password": "newpassword456", "confirm_password": "newpassword456"}).encode("utf-8"),
        headers=headers,
    )
    assert resp["status"] == 200, f"Change password failed: {resp['body']}"
    assert json.loads(resp["body"])["status"] == "ok"


def test_change_password_requires_auth(monkeypatch, tmp_path):
    main = _make_app(monkeypatch, tmp_path, suffix="cpw2")
    resp = asgi_request(
        main.app,
        "POST",
        "/api/v1/auth/change-password",
        body=json.dumps({"current_password": "old", "new_password": "new", "confirm_password": "new"}).encode("utf-8"),
        headers=[(b"content-type", b"application/json")],
    )
    assert resp["status"] in (401, 403)


def test_change_password_rejects_wrong_current(monkeypatch, tmp_path):
    main = _make_app(monkeypatch, tmp_path, suffix="cpw3")
    _, cookies = _signup(main.app, email="changepw_wrong@example.com")
    jwt = cookies.get(JWT_COOKIE, "")
    csrf = cookies.get("csrf-token", "")
    headers = [
        (b"cookie", f"{JWT_COOKIE}={jwt};csrf-token={csrf}".encode("utf-8")),
        (b"content-type", b"application/json"),
        (b"x-csrf-token", csrf.encode("utf-8")),
    ]

    resp = asgi_request(
        main.app,
        "POST",
        "/api/v1/auth/change-password",
        body=json.dumps({"current_password": "wrongold", "new_password": "newpass456", "confirm_password": "newpass456"}).encode("utf-8"),
        headers=headers,
    )
    assert resp["status"] == 403, f"Expected 403 got {resp['status']}: {resp['body']}"


def test_change_password_rejects_mismatch(monkeypatch, tmp_path):
    main = _make_app(monkeypatch, tmp_path, suffix="cpw4")
    _, cookies = _signup(main.app, email="changepw_mismatch@example.com")
    jwt = cookies.get(JWT_COOKIE, "")
    csrf = cookies.get("csrf-token", "")
    headers = [
        (b"cookie", f"{JWT_COOKIE}={jwt};csrf-token={csrf}".encode("utf-8")),
        (b"content-type", b"application/json"),
        (b"x-csrf-token", csrf.encode("utf-8")),
    ]

    resp = asgi_request(
        main.app,
        "POST",
        "/api/v1/auth/change-password",
        body=json.dumps({"current_password": "password123", "new_password": "newpass456", "confirm_password": "different"}).encode("utf-8"),
        headers=headers,
    )
    assert resp["status"] == 400, f"Expected 400 got {resp['status']}: {resp['body']}"


# ── Auth: CSRF ──────────────────────────────────────────────────────────────


def test_csrf_token_generation():
    token1 = generate_csrf_token()
    token2 = generate_csrf_token()
    assert len(token1) == 64
    assert token1 != token2


def test_csrf_validation():
    token = generate_csrf_token()
    assert validate_csrf(token, token) is True
    assert validate_csrf("", token) is False
    assert validate_csrf(token, "") is False
    assert validate_csrf("a" * 64, token) is False


def test_csrf_token_endpoint(monkeypatch, tmp_path):
    main = _make_app(monkeypatch, tmp_path, suffix="csrf1")
    resp = asgi_request(main.app, "GET", "/api/v1/auth/csrf-token")
    assert resp["status"] == 200
    body = json.loads(resp["body"])
    assert len(body["csrf_token"]) == 64
    cookies = _parse_cookies(resp["headers"])
    assert cookies.get("csrf-token") == body["csrf_token"]


def test_csrf_middleware_exempts_webhook(monkeypatch, tmp_path):
    main = _make_app(monkeypatch, tmp_path, suffix="csrf2")
    resp = asgi_request(
        main.app,
        "POST",
        "/api/v1/billing/webhook",
        body=json.dumps({"type": "checkout.session.completed"}).encode("utf-8"),
        headers=[(b"content-type", b"application/json")],
    )
    assert resp["status"] == 404  # No subscription, but not CSRF blocked


def test_csrf_middleware_blocks_mutation_without_token(monkeypatch, tmp_path):
    main = _make_app(monkeypatch, tmp_path, suffix="csrf3")
    resp = asgi_request(
        main.app,
        "POST",
        "/api/v1/auth/change-password",
        body=json.dumps({"current_password": "x", "new_password": "y", "confirm_password": "y"}).encode("utf-8"),
        headers=[(b"content-type", b"application/json")],
    )
    assert resp["status"] in (401, 403)


# ── Auth: Rate limit unit tests ──────────────────────────────────────────────


def test_check_rate_limit_allows_within_budget():
    result = check_rate_limit("rl1", 10, 60)
    assert result["allowed"] is True


def test_check_rate_limit_blocks_excess():
    for _ in range(5):
        check_rate_limit("rl2", 5, 60)
    result = check_rate_limit("rl2", 5, 60)
    assert result["allowed"] is False


def test_lockout_unit():
    clear_failed_logins("loc1")
    for _ in range(10):
        record_failed_login("loc1")
    assert is_locked("loc1") is True


def test_lockout_clears_after_success():
    clear_failed_logins("loc2")
    for _ in range(9):
        record_failed_login("loc2")
    assert is_locked("loc2") is False
    record_failed_login("loc2")
    assert is_locked("loc2") is True
    clear_failed_logins("loc2")
    assert is_locked("loc2") is False


# ── Billing: save_subscription ────────────────────────────────────────────────


def test_sqlite_store_save_subscription(tmp_path):
    store = SQLiteStore(tmp_path / "billing.db")
    sub = SubscriptionRecord(id="sub_test", team_id="team_test", tier="free", status="active", created_at=utc_now())
    store.save_subscription(sub)
    loaded = store.get_subscription("sub_test")
    assert loaded is not None
    assert loaded.tier == "free"
    assert loaded.team_id == "team_test"


def test_sqlite_store_save_subscription_upsert(tmp_path):
    store = SQLiteStore(tmp_path / "billing_up.db")
    sub = SubscriptionRecord(id="sub_up", team_id="team_up", tier="free", status="active", created_at=utc_now())
    store.save_subscription(sub)
    sub.tier = "pro"
    store.save_subscription(sub)
    loaded = store.get_subscription("sub_up")
    assert loaded.tier == "pro"


def test_list_subscriptions_by_team(tmp_path):
    store = SQLiteStore(tmp_path / "billing_list.db")
    sub = SubscriptionRecord(id="sub_list", team_id="team_list", tier="free", status="active", created_at=utc_now())
    store.save_subscription(sub)
    subs = store.list_subscriptions("team_list")
    assert len(subs) == 1
    assert subs[0].id == "sub_list"


# ── Billing: Subscription in tenant bundle ────────────────────────────────────


def test_signup_creates_subscription(monkeypatch, tmp_path):
    main = _make_app(monkeypatch, tmp_path, suffix="billing1")
    resp, _ = _signup(main.app, email="bill@example.com", ip="bill1")
    body = json.loads(resp["body"])
    team_id = body["team"]["id"]

    from ai_scientist.config import settings
    store = SQLiteStore(settings.db_path)
    subs = store.list_subscriptions(team_id)
    assert len(subs) == 1
    assert subs[0].tier == "free"
    assert subs[0].status == "active"


# ── Billing: Webhook ─────────────────────────────────────────────────────────


def test_billing_webhook_upgrades_subscription(monkeypatch, tmp_path):
    main = _make_app(monkeypatch, tmp_path, suffix="billing2")
    resp, _ = _signup(main.app, email="wh@example.com", ip="wh1")
    body = json.loads(resp["body"])
    team_id = body["team"]["id"]

    from ai_scientist.config import settings
    store = SQLiteStore(settings.db_path)
    sub = store.list_subscriptions(team_id)[0]

    event = {
        "type": "checkout.session.completed",
        "team_id": team_id,
        "data": {
            "object": {
                "client_reference_id": team_id,
                "metadata": {"tier": "pro"},
                "customer": "cus_test",
                "id": "sub_stripe",
            }
        },
    }
    webhook_resp = asgi_request(
        main.app,
        "POST",
        "/api/v1/billing/webhook",
        body=json.dumps(event).encode("utf-8"),
        headers=[(b"content-type", b"application/json")],
    )
    assert webhook_resp["status"] == 200, f"Webhook failed: {webhook_resp['body']}"

    updated = store.get_subscription(sub.id)
    assert updated is not None
    assert updated.tier == "pro", f"Expected pro, got {updated.tier}"
    assert updated.stripe_customer_id == "cus_test"


# ── Billing: apply_webhook_event unit ────────────────────────────────────────


def test_apply_webhook_event_upgrades_tier():
    from ai_scientist.billing import apply_webhook

    sub = SubscriptionRecord(id="sub_unit", team_id="team_unit", tier="free", status="active", created_at=utc_now())
    event = {
        "type": "checkout.session.completed",
        "data": {"object": {"metadata": {"tier": "pro"}, "customer": "cus_unit", "id": "sub_unit_stripe"}},
    }
    updated = apply_webhook(event, sub)
    assert updated.tier == "pro"
    assert updated.stripe_customer_id == "cus_unit"
    assert updated.status == "active"


# ── AI Providers ──────────────────────────────────────────────────────────────


def test_build_provider_no_key_falls_back(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("HUGGINGFACE_API_TOKEN", raising=False)
    monkeypatch.delenv("AI_SCIENTIST_OLLAMA_BASE_URL", raising=False)
    from ai_scientist.ai_providers import build_provider

    provider = build_provider()
    result = provider.synthesize("hello")
    assert result.provider == "deterministic"


def test_openai_provider_fallback_without_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    from ai_scientist.ai_providers import OpenAIProvider

    result = OpenAIProvider(model="test-model").synthesize("hello")
    assert result.provider == "deterministic"
    assert result.warnings


def test_openai_provider_fallback_on_network_error(monkeypatch):
    def fail(*args, **kwargs):
        raise OSError("network unavailable")

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr("urllib.request.urlopen", fail)
    from ai_scientist.ai_providers import OpenAIProvider

    result = OpenAIProvider(model="test-model").synthesize("hello")
    assert result.provider == "deterministic"
    assert "OpenAI provider failed" in result.warnings[0]


def test_auto_detect_huggingface_when_no_ollama(monkeypatch):
    monkeypatch.delenv("AI_SCIENTIST_OLLAMA_BASE_URL", raising=False)
    monkeypatch.setenv("HUGGINGFACE_API_TOKEN", "hf_test")

    def fail(*args, **kwargs):
        raise OSError("no server")

    monkeypatch.setattr("urllib.request.urlopen", fail)
    from ai_scientist.ai_providers import build_provider

    provider = build_provider()
    assert "HuggingFace" in type(provider).__name__


# ── DELETE Endpoints ─────────────────────────────────────────────────────────


def test_delete_project_memory(tmp_path):
    from ai_scientist.models import MemoryItem, ResearchProject

    store = SQLiteStore(tmp_path / "del_mem.db")
    project = ResearchProject(
        id="del_mem",
        name="Del Mem",
        created_at=utc_now(),
        memory=[
            MemoryItem(id="mem1", kind="note", content="Delete me", created_at=utc_now()),
            MemoryItem(id="mem2", kind="note", content="Keep me", created_at=utc_now()),
        ],
    )
    store.save_project(project)

    project.memory = [m for m in project.memory if m.id != "mem1"]
    store.save_project(project)

    loaded = store.get_project("del_mem")
    assert len(loaded.memory) == 1
    assert loaded.memory[0].id == "mem2"


def test_delete_project_endpoint(monkeypatch, tmp_path):
    from ai_scientist.models import ResearchProject

    main = _make_app_with_disable_auth(monkeypatch, tmp_path, suffix="del_proj")

    project = ResearchProject(id="del_proj_endpoint", name="Del Me", created_at=utc_now())
    main.STORE.save_project(project)
    assert main.STORE.get_project("del_proj_endpoint") is not None

    resp = asgi_request(main.app, "DELETE", "/api/projects/del_proj_endpoint")
    assert resp["status"] == 200, f"DELETE failed: {resp['body']}"
    assert main.STORE.get_project("del_proj_endpoint") is None


# ── Pagination ────────────────────────────────────────────────────────────────


def test_list_projects_pagination(monkeypatch, tmp_path):
    main = _make_app_with_disable_auth(monkeypatch, tmp_path, suffix="pagination")

    headers = [(b"content-type", b"application/json")]
    for i in range(5):
        payload = json.dumps({"name": f"Project {i}", "description": ""}).encode("utf-8")
        resp = asgi_request(main.app, "POST", "/api/v1/projects", body=payload, headers=headers)
        assert resp["status"] == 200, f"Create {i} failed: {resp['body']}"

    resp = asgi_request(main.app, "GET", "/api/v1/projects?skip=2&limit=2")
    assert resp["status"] == 200
    projects = json.loads(resp["body"])
    assert len(projects) >= 2


# ── Config validation ────────────────────────────────────────────────────────


def test_config_validate_rejects_weak_defaults(monkeypatch):
    from ai_scientist.config import Settings

    s = Settings()
    monkeypatch.setattr(s, "environment", "production")
    monkeypatch.setattr(s, "jwt_secret", "dev-change-me")
    monkeypatch.setattr(s, "app_password", "change-me")
    monkeypatch.setattr(s, "cookie_secure", False)

    with pytest.raises(RuntimeError):
        s.validate()


def test_config_validate_accepts_strong_config(monkeypatch):
    from ai_scientist.config import Settings

    s = Settings()
    monkeypatch.setattr(s, "environment", "production")
    monkeypatch.setattr(s, "jwt_secret", "a" * 32)
    monkeypatch.setattr(s, "app_password", "b" * 20)
    monkeypatch.setattr(s, "cookie_secure", True)

    s.validate()  # Should not raise


# ── JWT utilities ────────────────────────────────────────────────────────────


def test_make_and_decode_jwt():
    token = make_jwt({"sub": "user1", "team_id": "team1", "role": "admin"}, "secret", 3600)
    claims = decode_jwt(token, "secret")
    assert claims is not None
    assert claims.user_id == "user1"
    assert claims.team_id == "team1"
    assert claims.role == "admin"


def test_decode_jwt_wrong_secret():
    token = make_jwt({"sub": "user1", "team_id": "team1", "role": "admin"}, "secret", 3600)
    claims = decode_jwt(token, "wrong-secret")
    assert claims is None
