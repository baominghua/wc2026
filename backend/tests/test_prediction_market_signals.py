import unittest
from unittest.mock import patch
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from services.prediction_model import predict_match


class PredictionMarketSignalTests(unittest.TestCase):
    def test_prediction_includes_market_and_upset_fields_without_odds_key(self):
        with patch.dict("os.environ", {"ODDS_MARKET_ENABLED": "false"}, clear=False):
            result = predict_match("USA", "Paraguay")

        self.assertIn("market_odds", result)
        self.assertIn("market_calibration", result)
        self.assertIn("upset_prediction", result)
        self.assertFalse(result["market_calibration"]["applied"])
        self.assertEqual(result["market_calibration"]["weight"], 0)
        self.assertGreaterEqual(result["upset_prediction"]["probability"], 0)
        self.assertLessEqual(result["upset_prediction"]["probability"], 1)
        self.assertTrue(result["upset_prediction"]["score"])
        self.assertTrue(result["upset_prediction"]["reasons"])

    def test_unconfigured_market_signal_uses_clear_user_facing_factor(self):
        with patch.dict("os.environ", {"ODDS_MARKET_ENABLED": "false"}, clear=False):
            result = predict_match("USA", "Paraguay")

        factor_text = "\n".join(result["factors"])
        self.assertIn("市场信号校准", factor_text)
        self.assertNotIn("disabled", factor_text)
        self.assertNotIn("not_configured", factor_text)
        self.assertIn("暂不做硬校准", factor_text)

    def test_missing_realtime_key_uses_historical_market_prior(self):
        with patch.dict("os.environ", {"ODDS_MARKET_ENABLED": "true", "THE_ODDS_API_KEY": ""}, clear=False):
            result = predict_match("Netherlands", "Sweden", match_round=2)

        self.assertEqual(result["market_odds"]["status"], "historical_prior")
        self.assertEqual(result["market_odds"]["source"], "football_data_historical_prior")
        self.assertIsNotNone(result["market_odds"]["h2h"])
        self.assertLessEqual(result["market_calibration"]["weight"], 0.04)
        factor_text = "\n".join(result["factors"])
        self.assertIn("公开历史赔率样本", factor_text)

    def test_prediction_exposes_public_data_source_contract(self):
        with patch.dict("os.environ", {"ODDS_MARKET_ENABLED": "true", "THE_ODDS_API_KEY": ""}, clear=False):
            result = predict_match("Argentina", "Austria", match_round=2)

        source_by_id = {item["id"]: item for item in result["public_data_sources"]}
        self.assertEqual(source_by_id["realtime_market_odds"]["status"], "not_configured")
        self.assertEqual(source_by_id["football_data_historical_odds"]["status"], "connected")
        self.assertEqual(source_by_id["espn_public_results_events"]["status"], "connected")
        self.assertEqual(source_by_id["openfootball_schedule"]["status"], "reference")
        self.assertEqual(source_by_id["transfermarkt_public_injuries"]["status"], "connected")
        self.assertEqual(source_by_id["espn_worldcup_injury_tracker"]["status"], "reference")
        self.assertEqual(source_by_id["sports_mole_team_news"]["status"], "reference")
        self.assertEqual(source_by_id["transfermarkt_historical_injury_csv"]["status"], "reference")
        self.assertEqual(source_by_id["sportmonks_sidelined"]["status"], "standby")
        self.assertEqual(source_by_id["statsbomb_open_data"]["status"], "reference")
        self.assertIn("低权重", source_by_id["football_data_historical_odds"]["message"])
        all_messages = "\n".join(item.get("message", "") + item.get("scope", "") for item in result["public_data_sources"])
        self.assertNotIn("SPORTMONKS_TOKEN", all_messages)
        self.assertNotIn("API_FOOTBALL_KEY", all_messages)

    def test_large_market_disagreement_calibrates_probabilities_toward_market(self):
        market = {
            "available": True,
            "status": "connected",
            "source": "the_odds_api",
            "last_updated": "2026-06-17T12:00:00+08:00",
            "message": "connected",
            "h2h": {"home": 0.24, "draw": 0.24, "away": 0.52},
            "totals": {"line": 2.5, "over_probability": 0.61, "under_probability": 0.39},
            "spread": {"favorite": "away", "line": -0.5, "price": 1.95},
            "bookmaker_count": 8,
        }

        with patch.dict("os.environ", {"ODDS_MARKET_ENABLED": "false"}, clear=False):
            baseline = predict_match("USA", "Paraguay")

        with patch("services.prediction_model.fetch_market_odds", return_value=market):
            calibrated = predict_match("USA", "Paraguay")

        self.assertTrue(calibrated["market_calibration"]["applied"])
        self.assertGreater(calibrated["market_calibration"]["weight"], 0)
        self.assertLess(
            calibrated["away_win_probability"] - baseline["away_win_probability"],
            0.35,
        )
        self.assertGreater(calibrated["away_win_probability"], baseline["away_win_probability"])
        self.assertIn("market", calibrated["market_calibration"])

    def test_small_market_disagreement_keeps_model_probabilities(self):
        with patch.dict("os.environ", {"ODDS_MARKET_ENABLED": "false"}, clear=False):
            no_market = predict_match("Brazil", "Morocco")
        market = {
            "available": True,
            "status": "connected",
            "source": "the_odds_api",
            "last_updated": "2026-06-17T12:00:00+08:00",
            "message": "connected",
            "h2h": {
                "home": no_market["home_win_probability"] + 0.01,
                "draw": no_market["draw_probability"],
                "away": max(0.01, no_market["away_win_probability"] - 0.01),
            },
            "totals": None,
            "spread": None,
            "bookmaker_count": 4,
        }

        with patch("services.prediction_model.fetch_market_odds", return_value=market):
            result = predict_match("Brazil", "Morocco")

        self.assertFalse(result["market_calibration"]["applied"])
        self.assertEqual(result["market_calibration"]["level"], "aligned")
        self.assertAlmostEqual(result["home_win_probability"], no_market["home_win_probability"], places=3)


if __name__ == "__main__":
    unittest.main()
