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
    payload = json.loads(response_body.decode("utf-8")) if response_body else None
    return status, response_headers, payload


class TournamentApiTests(unittest.TestCase):
    def setUp(self):
        self._old_env = {
            "AUTH_ENABLED": os.environ.get("AUTH_ENABLED"),
            "ESPN_SCOREBOARD_ENABLED": os.environ.get("ESPN_SCOREBOARD_ENABLED"),
            "API_FOOTBALL_ENABLED": os.environ.get("API_FOOTBALL_ENABLED"),
            "ODDS_MARKET_ENABLED": os.environ.get("ODDS_MARKET_ENABLED"),
            "LIVE_SYNC_ENABLED": os.environ.get("LIVE_SYNC_ENABLED"),
        }
        os.environ["AUTH_ENABLED"] = "false"
        os.environ["ESPN_SCOREBOARD_ENABLED"] = "false"
        os.environ["API_FOOTBALL_ENABLED"] = "false"
        os.environ["ODDS_MARKET_ENABLED"] = "false"
        os.environ["LIVE_SYNC_ENABLED"] = "false"

    def tearDown(self):
        for key, value in self._old_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_projection_endpoint_returns_dynamic_qualification_payload(self):
        status, _, payload = asyncio.run(
            asgi_request("GET", "/api/v1/tournament/projection?simulate=true")
        )

        self.assertEqual(status, 200)
        self.assertIn("generated_at", payload)
        self.assertEqual(payload["summary"]["qualified_count"], 32)
        self.assertEqual(len(payload["groups"]), 12)
        self.assertEqual(len(payload["best_thirds"]), 12)
        self.assertEqual(len(payload["round_of_32"]), 16)
        self.assertEqual(payload["round_of_32"][0]["id"], 73)
        self.assertEqual(payload["round_of_32"][0]["home_slot"], "A2")
        self.assertEqual(payload["round_of_32"][0]["away_slot"], "B2")
        self.assertIn("rounds", payload["knockout"])
        self.assertEqual(len(payload["knockout"]["rounds"]["Final"]), 1)
        self.assertTrue(payload["knockout"]["champion"])
        model_group_match = next(match for match in payload["group_matches"] if match.get("score_source") == "model")
        self.assertIn("skill_audit", model_group_match["prediction"])
        self.assertIn("single_match_brief", model_group_match["prediction"]["skill_audit"])
        final_match = payload["knockout"]["rounds"]["Final"][0]
        self.assertIn("skill_audit", final_match["prediction"])


if __name__ == "__main__":
    unittest.main()
