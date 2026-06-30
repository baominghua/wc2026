import asyncio
import json
import os
import sys
import unittest
from pathlib import Path


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

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("utf-8"),
        "query_string": b"",
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
    payload = json.loads(response_body.decode("utf-8")) if response_body else None
    return status, response_headers, payload


class MatchesApiTests(unittest.TestCase):
    def setUp(self):
        self._old_env = {
            "ADMIN_PASSWORD": os.environ.get("ADMIN_PASSWORD"),
            "AUTH_SESSION_SECRET": os.environ.get("AUTH_SESSION_SECRET"),
            "AUTH_SESSION_MAX_AGE_SECONDS": os.environ.get("AUTH_SESSION_MAX_AGE_SECONDS"),
            "ESPN_SCOREBOARD_ENABLED": os.environ.get("ESPN_SCOREBOARD_ENABLED"),
            "API_FOOTBALL_ENABLED": os.environ.get("API_FOOTBALL_ENABLED"),
            "API_FOOTBALL_KEY": os.environ.get("API_FOOTBALL_KEY"),
            "LOCAL_MATCH_FEED_ENABLED": os.environ.get("LOCAL_MATCH_FEED_ENABLED"),
            "MATCH_FEED_URL": os.environ.get("MATCH_FEED_URL"),
            "MATCH_RESULTS_BACKFILL_URL": os.environ.get("MATCH_RESULTS_BACKFILL_URL"),
        }
        os.environ["ADMIN_PASSWORD"] = "correct-password"
        os.environ["AUTH_SESSION_SECRET"] = "unit-test-secret"
        os.environ["AUTH_SESSION_MAX_AGE_SECONDS"] = "3600"
        os.environ["ESPN_SCOREBOARD_ENABLED"] = "false"
        os.environ["API_FOOTBALL_ENABLED"] = "false"
        os.environ.pop("API_FOOTBALL_KEY", None)
        os.environ.pop("LOCAL_MATCH_FEED_ENABLED", None)
        os.environ.pop("MATCH_FEED_URL", None)
        os.environ.pop("MATCH_RESULTS_BACKFILL_URL", None)

    def tearDown(self):
        for key, value in self._old_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_matches_endpoint_returns_full_schedule_with_knockouts(self):
        login_status, login_headers, _ = asyncio.run(
            asgi_request("POST", "/api/v1/auth/login", json_body={"password": "correct-password"})
        )
        self.assertEqual(login_status, 200)

        cookie = login_headers["set-cookie"].split(";", 1)[0]
        status, _, payload = asyncio.run(
            asgi_request("GET", "/api/v1/matches/", headers={"cookie": cookie})
        )

        self.assertEqual(status, 200)
        self.assertEqual(len(payload), 104)
        knockout_matches = [match for match in payload if match.get("stage")]
        self.assertEqual(len(knockout_matches), 32)
        self.assertTrue(all("group" in match for match in knockout_matches))

    def test_knockout_schedule_templates_are_marked_as_placeholders(self):
        login_status, login_headers, _ = asyncio.run(
            asgi_request("POST", "/api/v1/auth/login", json_body={"password": "correct-password"})
        )
        self.assertEqual(login_status, 200)

        cookie = login_headers["set-cookie"].split(";", 1)[0]
        status, _, payload = asyncio.run(
            asgi_request("GET", "/api/v1/matches/", headers={"cookie": cookie})
        )

        self.assertEqual(status, 200)
        by_id = {match["id"]: match for match in payload}
        self.assertEqual(by_id[73]["home_team"], "A2")
        self.assertEqual(by_id[73]["away_team"], "B2")
        self.assertEqual(by_id[73]["fixture_status"], "placeholder")
        self.assertEqual(by_id[89]["home_team"], "W73")
        self.assertEqual(by_id[89]["away_team"], "W74")
        self.assertEqual(by_id[89]["fixture_status"], "placeholder")

    def test_team_detail_endpoint_uses_backend_team_catalog_and_official_squad(self):
        login_status, login_headers, _ = asyncio.run(
            asgi_request("POST", "/api/v1/auth/login", json_body={"password": "correct-password"})
        )
        self.assertEqual(login_status, 200)

        cookie = login_headers["set-cookie"].split(";", 1)[0]
        status, _, payload = asyncio.run(
            asgi_request("GET", "/api/v1/teams/33", headers={"cookie": cookie})
        )

        self.assertEqual(status, 200)
        self.assertEqual(payload["name"], "法国")
        players = payload["squad"]["players"]
        names = {player["name"] for player in players}
        self.assertEqual(len(players), 26)
        self.assertFalse(names & {"Antoine Griezmann", "Olivier Giroud", "Griezmann", "Giroud"})
        self.assertIn("feature_profile", payload)
        self.assertIsInstance(payload["feature_profile"], dict)
        self.assertEqual(payload["feature_profile"]["team"], payload["name"])
        self.assertIn("form_state", payload["feature_profile"])
        self.assertIn("next_prediction_notes", payload["feature_profile"])


if __name__ == "__main__":
    unittest.main()
