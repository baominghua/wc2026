from __future__ import annotations

import base64
import hashlib
import hmac
import os
import time
from http.cookies import SimpleCookie

from fastapi.responses import JSONResponse


DEFAULT_COOKIE_NAME = "wc2026_session"
DEFAULT_SESSION_MAX_AGE_SECONDS = 7 * 24 * 60 * 60


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off", ""}


def auth_cookie_name() -> str:
    return os.getenv("AUTH_COOKIE_NAME", DEFAULT_COOKIE_NAME).strip() or DEFAULT_COOKIE_NAME


def session_max_age_seconds() -> int:
    raw_value = os.getenv("AUTH_SESSION_MAX_AGE_SECONDS", str(DEFAULT_SESSION_MAX_AGE_SECONDS))
    try:
        return max(60, int(raw_value))
    except ValueError:
        return DEFAULT_SESSION_MAX_AGE_SECONDS


def is_auth_enabled() -> bool:
    if not env_bool("AUTH_ENABLED", True):
        return False
    return bool(os.getenv("ADMIN_PASSWORD"))


def verify_admin_password(password: str) -> bool:
    expected = os.getenv("ADMIN_PASSWORD", "")
    return bool(expected) and hmac.compare_digest(password or "", expected)


def _session_secret() -> str:
    return os.getenv("AUTH_SESSION_SECRET") or os.getenv("ADMIN_PASSWORD") or "wc2026-local-dev-secret"


def _sign(payload: str) -> str:
    return hmac.new(_session_secret().encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()


def create_session_token(now: int | None = None) -> str:
    issued_at = int(now or time.time())
    expires_at = issued_at + session_max_age_seconds()
    payload = f"admin:{expires_at}"
    signature = _sign(payload)
    token = f"{payload}:{signature}".encode("utf-8")
    return base64.urlsafe_b64encode(token).decode("ascii")


def verify_session_token(token: str | None, now: int | None = None) -> bool:
    if not token:
        return False
    try:
        decoded = base64.urlsafe_b64decode(token.encode("ascii")).decode("utf-8")
        user, expires_at_raw, signature = decoded.rsplit(":", 2)
        expires_at = int(expires_at_raw)
    except (ValueError, UnicodeDecodeError):
        return False

    payload = f"{user}:{expires_at}"
    if not hmac.compare_digest(signature, _sign(payload)):
        return False
    return user == "admin" and expires_at > int(now or time.time())


def cookie_secure() -> bool:
    return env_bool("AUTH_COOKIE_SECURE", False)


def _cookie_from_scope(scope, name: str) -> str | None:
    for key, value in scope.get("headers", []):
        if key.lower() == b"cookie":
            cookies = SimpleCookie()
            cookies.load(value.decode("latin-1"))
            morsel = cookies.get(name)
            return morsel.value if morsel else None
    return None


class AuthMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        method = scope.get("method", "")
        if (
            method != "OPTIONS"
            and is_auth_enabled()
            and path.startswith("/api/v1/")
            and not path.startswith("/api/v1/auth")
        ):
            token = _cookie_from_scope(scope, auth_cookie_name())
            if not verify_session_token(token):
                response = JSONResponse({"detail": "Authentication required"}, status_code=401)
                await response(scope, receive, send)
                return

        await self.app(scope, receive, send)
