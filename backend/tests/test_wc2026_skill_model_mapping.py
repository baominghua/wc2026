import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from services.prediction_model import predict_match


class WC2026SkillModelMappingTests(unittest.TestCase):
    def test_score_discipline_draw_protection_changes_model_score_pool(self):
        with patch.dict(os.environ, {"ODDS_MARKET_ENABLED": "false"}, clear=False):
            result = predict_match("United States", "Australia", match_round=1, model_type="form_weighted")

        scores = [item["score"] for item in result["possible_scores"]]
        self.assertEqual(result["predicted_score"], "2-1")
        self.assertIn("1-1", scores)
        self.assertTrue(any("比分纪律" in factor and "防平" in factor for factor in result["factors"]))

    def test_score_discipline_overflow_changes_strong_favorite_score_pool(self):
        with patch.dict(os.environ, {"ODDS_MARKET_ENABLED": "false"}, clear=False):
            result = predict_match("France", "Sweden", match_round=1, model_type="form_weighted")

        scores = [item["score"] for item in result["possible_scores"]]
        top_by_probability = max(result["possible_scores"], key=lambda item: item["probability"])
        self.assertEqual(result["predicted_score"], top_by_probability["score"])
        self.assertIn("4-0", scores)
        self.assertTrue(any("比分纪律" in factor and "大胜溢出" in factor for factor in result["factors"]))

    def test_primary_score_uses_highest_probability_score_pool_entry(self):
        with patch.dict(os.environ, {"ODDS_MARKET_ENABLED": "false"}, clear=False):
            result = predict_match("Morocco", "Haiti", match_round=3, model_type="form_weighted")

        top_by_probability = max(result["possible_scores"], key=lambda item: item["probability"])
        self.assertEqual(result["predicted_score"], top_by_probability["score"])
        self.assertEqual(result["predicted_score_probability"], top_by_probability["probability"])
        self.assertIn("4-0", [item["score"] for item in result["possible_scores"]])


if __name__ == "__main__":
    unittest.main()
