import asyncio
import json
import os
import sys
import unittest
from pathlib import Path
from urllib.parse import urlencode


BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from main import app


async def asgi_request(method, path, *, json_body=None, headers=None):
    body = b""
    request_headers = [(b"host", b"testserver")]
    if json_body is not None:
        body = json.dumps(json_body).encode("utf-8")
        request_headers.append((b"content-type", b"application/json"))
    for key, value in (headers or {}).items():
        request_headers.append((key.lower().encode("latin-1"), value.encode("latin-1")))

    if "?" in path:
        clean_path, query = path.split("?", 1)
    else:
        clean_path, query = path, ""

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": clean_path,
        "raw_path": clean_path.encode("utf-8"),
        "query_string": query.encode("utf-8"),
        "headers": request_headers,
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
    }

    sent = []
    received = False

    async def receive():
        nonlocal received
        if received:
            return {"type": "http.request", "body": b"", "more_body": False}
        received = True
        return {"type": "http.request", "body": body, "more_body": False}

    async def send(message):
        sent.append(message)

    await app(scope, receive, send)

    status = next(message["status"] for message in sent if message["type"] == "http.response.start")
    response_headers = {
        key.decode("latin-1").lower(): value.decode("latin-1")
        for message in sent
        if message["type"] == "http.response.start"
        for key, value in message.get("headers", [])
    }
    response_body = b"".join(
        message.get("body", b"")
        for message in sent
        if message["type"] == "http.response.body"
    )
    try:
        payload = json.loads(response_body.decode("utf-8")) if response_body else None
    except json.JSONDecodeError:
        payload = response_body.decode("utf-8")
    return status, response_headers, payload


class AuthGateTests(unittest.TestCase):
    def setUp(self):
        self._old_env = {
            "ADMIN_PASSWORD": os.environ.get("ADMIN_PASSWORD"),
            "AUTH_SESSION_SECRET": os.environ.get("AUTH_SESSION_SECRET"),
            "AUTH_SESSION_MAX_AGE_SECONDS": os.environ.get("AUTH_SESSION_MAX_AGE_SECONDS"),
        }
        os.environ["ADMIN_PASSWORD"] = "correct-password"
        os.environ["AUTH_SESSION_SECRET"] = "unit-test-secret"
        os.environ["AUTH_SESSION_MAX_AGE_SECONDS"] = "3600"

    def tearDown(self):
        for key, value in self._old_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_status_reports_enabled_and_current_session(self):
        status, _, payload = asyncio.run(asgi_request("GET", "/api/v1/auth/status"))

        self.assertEqual(status, 200)
        self.assertEqual(payload["enabled"], True)
        self.assertEqual(payload["authenticated"], False)

    def test_protected_api_requires_login_then_accepts_session_cookie(self):
        blocked_status, _, blocked_payload = asyncio.run(asgi_request("GET", "/api/v1/teams/"))
        self.assertEqual(blocked_status, 401)
        self.assertEqual(blocked_payload["detail"], "Authentication required")

        bad_status, _, _ = asyncio.run(
            asgi_request("POST", "/api/v1/auth/login", json_body={"password": "wrong-password"})
        )
        self.assertEqual(bad_status, 401)

        login_status, login_headers, login_payload = asyncio.run(
            asgi_request("POST", "/api/v1/auth/login", json_body={"password": "correct-password"})
        )
        self.assertEqual(login_status, 200)
        self.assertEqual(login_payload["authenticated"], True)
        cookie = login_headers.get("set-cookie", "")
        self.assertIn("wc2026_session=", cookie)
        self.assertIn("HttpOnly", cookie)

        session_cookie = cookie.split(";", 1)[0]
        allowed_status, _, allowed_payload = asyncio.run(
            asgi_request("GET", "/api/v1/teams/", headers={"cookie": session_cookie})
        )
        self.assertEqual(allowed_status, 200)
        self.assertIsInstance(allowed_payload, list)

    def test_auth_can_be_disabled_for_local_development(self):
        os.environ.pop("ADMIN_PASSWORD", None)

        status, _, payload = asyncio.run(asgi_request("GET", "/api/v1/auth/status"))
        self.assertEqual(status, 200)
        self.assertEqual(payload["enabled"], False)
        self.assertEqual(payload["authenticated"], True)

        teams_status, _, teams_payload = asyncio.run(asgi_request("GET", "/api/v1/teams/"))
        self.assertEqual(teams_status, 200)
        self.assertIsInstance(teams_payload, list)


if __name__ == "__main__":
    unittest.main()
