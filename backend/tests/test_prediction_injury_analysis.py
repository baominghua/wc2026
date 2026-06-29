import asyncio
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from routers.predictions import PredictionRequest, predict_match_result


class PredictionInjuryAnalysisTests(unittest.TestCase):
    def test_prediction_factors_include_specific_injury_names(self):
        injury_feed = {
            "status": "connected",
            "source": "transfermarkt_public",
            "last_updated": "2026-06-24T09:15:00+08:00",
            "message": "public injury feed synced",
            "teams": {
                "home": {
                    "team": "Netherlands",
                    "unavailable_players": ["Test Defender (Knee)"],
                    "doubtful_players": [],
                    "card_risk_players": ["Test Midfielder (Yellow cards)"],
                    "note": "one unavailable and one card risk",
                    "source": "transfermarkt_public",
                },
                "away": {
                    "team": "Sweden",
                    "unavailable_players": [],
                    "doubtful_players": ["Test Striker (Hamstring)"],
                    "card_risk_players": [],
                    "note": "one doubtful",
                    "source": "transfermarkt_public",
                },
            },
            "auto_apply": {"home_key_absence": True, "away_key_absence": False},
        }
        request = PredictionRequest(
            home_team="Netherlands",
            away_team="Sweden",
            model_type="form_weighted",
            match_round=2,
        )

        with patch.dict("os.environ", {"ODDS_MARKET_ENABLED": "false"}, clear=False), patch(
            "routers.predictions.get_match_injury_feed", return_value=injury_feed
        ), patch("routers.predictions.load_pre_world_cup_official_matches", return_value=[]), patch(
            "routers.predictions.merge_live_matches", return_value=[]
        ):
            result = asyncio.run(predict_match_result(request))

        factors = "\n".join(result["factors"])
        self.assertIn("Test Defender", factors)
        self.assertIn("Test Midfielder", factors)
        self.assertIn("Test Striker", factors)
        self.assertIn("伤停", factors)


if __name__ == "__main__":
    unittest.main()
