import asyncio
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from backend.tests.test_matches_api import asgi_request


class ReviewsApiTests(unittest.TestCase):
    def setUp(self):
        self._old_env = {
            "ADMIN_PASSWORD": os.environ.get("ADMIN_PASSWORD"),
            "AUTH_SESSION_SECRET": os.environ.get("AUTH_SESSION_SECRET"),
            "AUTH_SESSION_MAX_AGE_SECONDS": os.environ.get("AUTH_SESSION_MAX_AGE_SECONDS"),
            "ODDS_MARKET_ENABLED": os.environ.get("ODDS_MARKET_ENABLED"),
            "PREDICTION_SNAPSHOT_PATH": os.environ.get("PREDICTION_SNAPSHOT_PATH"),
            "TEAM_PROFILE_STORE_PATH": os.environ.get("TEAM_PROFILE_STORE_PATH"),
        }
        self._tmp = tempfile.TemporaryDirectory()
        self._snapshot_path = Path(self._tmp.name) / "snapshots.json"
        self._profile_path = Path(self._tmp.name) / "team-profiles.json"
        os.environ["ADMIN_PASSWORD"] = "correct-password"
        os.environ["AUTH_SESSION_SECRET"] = "unit-test-secret"
        os.environ["AUTH_SESSION_MAX_AGE_SECONDS"] = "3600"
        os.environ["ODDS_MARKET_ENABLED"] = "false"
        os.environ["PREDICTION_SNAPSHOT_PATH"] = str(self._snapshot_path)
        os.environ["TEAM_PROFILE_STORE_PATH"] = str(self._profile_path)

    def tearDown(self):
        for key, value in self._old_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self._tmp.cleanup()

    def _write_snapshot(self, match_id: int, score: str = "2-0") -> None:
        payload = {
            "version": 1,
            "snapshots": {
                str(match_id): {
                    "match_id": match_id,
                    "saved_at": "2026-06-11T12:00:00+00:00",
                    "prediction": {
                        "home_win_probability": 0.64,
                        "draw_probability": 0.21,
                        "away_win_probability": 0.15,
                        "predicted_score": score,
                        "possible_scores": [
                            {"score": score, "probability": 18.5},
                            {"score": "1-0", "probability": 10.1},
                            {"score": "2-1", "probability": 8.8},
                        ],
                        "upset_prediction": {
                            "outcome": "draw",
                            "score": "1-1",
                            "probability": 0.18,
                            "reasons": ["样本测试"],
                        },
                    },
                }
            },
        }
        self._snapshot_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    def _login_cookie(self) -> str:
        status, headers, _ = asyncio.run(
            asgi_request("POST", "/api/v1/auth/login", json_body={"password": "correct-password"})
        )
        self.assertEqual(status, 200)
        return headers["set-cookie"].split(";", 1)[0]

    def test_reviews_endpoint_returns_accuracy_summary_and_rows(self):
        self._write_snapshot(1)
        cookie = self._login_cookie()

        status, _, payload = asyncio.run(
            asgi_request("GET", "/api/v1/reviews/", headers={"cookie": cookie})
        )

        self.assertEqual(status, 200)
        self.assertIn("summary", payload)
        self.assertIn("rows", payload)
        self.assertIn("team_profiles", payload)
        self.assertGreaterEqual(payload["team_profiles"]["match_count"], 1)
        self.assertTrue(payload["team_profiles"]["profiles"])
        self.assertTrue(self._profile_path.exists())
        self.assertGreaterEqual(payload["summary"]["completed_matches"], 2)
        self.assertEqual(payload["summary"]["total_matches"], 104)
        self.assertEqual(payload["summary"]["reviewed_matches"], 1)
        self.assertGreaterEqual(payload["summary"]["missing_prediction_count"], 1)
        self.assertEqual(len(payload["rows"]), 1)
        self.assertGreaterEqual(len(payload["missing_prediction_matches"]), 1)
        self.assertIn("outcome_top1_accuracy", payload["summary"])
        self.assertIn("wdl_accuracy", payload["summary"])
        self.assertIn("wdl_hit", payload["rows"][0]["accuracy"])
        self.assertIn("score_top3_accuracy", payload["summary"])
        self.assertIn("total_goals_range_accuracy", payload["summary"])
        self.assertIn("btts_accuracy", payload["summary"])
        self.assertIn("赛前预测快照", payload["source_policy"])
        self.assertTrue(
            any(note["type"] == "red_card_turning_point" for note in payload["rows"][0]["variance_notes"])
        )

    def test_current_model_backtest_endpoint_runs_current_model_and_marks_mode(self):
        cookie = self._login_cookie()

        status, _, payload = asyncio.run(
            asgi_request("GET", "/api/v1/reviews/current-model-backtest", headers={"cookie": cookie})
        )

        self.assertEqual(status, 200)
        self.assertEqual(payload["evaluation_mode"], "current_model_backtest")
        self.assertIn("profile_comparison", payload)
        self.assertIn("without_profile", payload["profile_comparison"])
        self.assertIn("with_profile", payload["profile_comparison"])
        self.assertIn("delta", payload["profile_comparison"])
        self.assertIn("wdl_accuracy", payload["profile_comparison"]["with_profile"])
        self.assertIn("score_total_accuracy", payload["profile_comparison"]["delta"])
        self.assertGreaterEqual(payload["summary"]["completed_matches"], 2)
        self.assertEqual(payload["summary"]["total_matches"], 104)
        self.assertEqual(payload["summary"]["reviewed_matches"], payload["summary"]["completed_matches"])
        self.assertEqual(payload["summary"]["missing_prediction_count"], 0)
        self.assertIn("outcome_top2", payload["metric_definitions"])
        self.assertIn("概率前两项", payload["metric_definitions"]["outcome_top2"])
        self.assertIn("wdl_hit", payload["metric_definitions"])
        self.assertIn("胜平负", payload["metric_definitions"]["wdl_hit"])
        self.assertIn("total_goals_range_hit", payload["metric_definitions"])
        self.assertIn("btts_hit", payload["metric_definitions"])
        self.assertIn("当前模型", payload["source_policy"])

    def test_model_performance_uses_real_snapshot_audit_not_hardcoded_totals(self):
        self._write_snapshot(1)
        cookie = self._login_cookie()

        status, _, payload = asyncio.run(
            asgi_request("GET", "/api/v1/predictions/model-performance", headers={"cookie": cookie})
        )

        self.assertEqual(status, 200)
        self.assertEqual(payload["total_predictions"], 1)
        self.assertEqual(payload["correct_predictions"], 1)
        self.assertNotEqual(payload["total_predictions"], 156)

    def test_prediction_with_match_id_includes_review_adjustment(self):
        cookie = self._login_cookie()

        status, _, payload = asyncio.run(
            asgi_request(
                "POST",
                "/api/v1/predictions/predict",
                headers={"cookie": cookie},
                json_body={
                    "match_id": 42,
                    "home_team": "France",
                    "away_team": "Iraq",
                    "match_round": 2,
                    "model_type": "form_weighted",
                },
            )
        )

        self.assertEqual(status, 200)
        self.assertTrue(any("赛后复盘" in factor for factor in payload["factors"]))

        self.assertIn("profile_adjustment", payload)
        self.assertEqual(payload["profile_adjustment"]["source"], "team_profile_store")
        self.assertTrue(payload["profile_adjustment"]["team_profiles"])

    def test_prediction_endpoint_includes_wc2026_skill_audit(self):
        cookie = self._login_cookie()

        status, _, payload = asyncio.run(
            asgi_request(
                "POST",
                "/api/v1/predictions/predict",
                headers={"cookie": cookie},
                json_body={
                    "match_id": 29,
                    "home_team": "United States",
                    "away_team": "Australia",
                    "match_round": 1,
                    "model_type": "form_weighted",
                },
            )
        )

        self.assertEqual(status, 200)
        self.assertIn("skill_audit", payload)
        self.assertIn("single_match_brief", payload["skill_audit"])
        self.assertTrue(payload["skill_audit"]["score_pool_top3"])


if __name__ == "__main__":
    unittest.main()
