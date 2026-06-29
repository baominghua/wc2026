import sys
import unittest
from pathlib import Path
from unittest.mock import patch


BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from services.prediction_model import predict_match


class PredictionTeamFeatureTests(unittest.TestCase):
    def test_predict_match_applies_team_feature_adjustment_as_bounded_calibration(self):
        feature_adjustment = {
            "applied": True,
            "home_attack_delta": -0.03,
            "away_attack_delta": 0.04,
            "draw_probability_delta": 0.025,
            "reasons": [
                "球队特征库: 荷兰破防效率一般，瑞典进攻热度较高",
                "球队特征库: 双方小组形势允许保守提高平局保护",
            ],
            "team_profiles": {
                "home": {"team": "荷兰", "sample_matches": 1, "tactical_tags": ["discipline_watch"]},
                "away": {"team": "瑞典", "sample_matches": 1, "tactical_tags": ["attack_hot"]},
            },
        }

        with patch.dict("os.environ", {"ODDS_MARKET_ENABLED": "false"}, clear=False):
            baseline = predict_match("Netherlands", "Sweden", match_round=2)
            adjusted = predict_match(
                "Netherlands",
                "Sweden",
                match_round=2,
                team_feature_adjustment=feature_adjustment,
            )

        self.assertLess(adjusted["xg_home"], baseline["xg_home"])
        self.assertGreater(adjusted["xg_away"], baseline["xg_away"])
        self.assertGreater(adjusted["draw_probability"], baseline["draw_probability"])
        self.assertEqual(adjusted["team_feature_adjustment"]["team_profiles"]["away"]["team"], "瑞典")
        self.assertTrue(any("球队特征库" in item for item in adjusted["factors"]))


if __name__ == "__main__":
    unittest.main()
