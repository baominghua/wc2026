import sys
import unittest
from pathlib import Path
from unittest.mock import patch


BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from services.prediction_model import predict_match


class PredictionUpsetPropsRankingTests(unittest.TestCase):
    def test_heavy_favorite_upset_stays_near_main_distribution(self):
        with patch.dict("os.environ", {"ODDS_MARKET_ENABLED": "false"}, clear=False):
            result = predict_match("Portugal", "DR Congo")

        upset = result["upset_prediction"]
        self.assertEqual(upset["outcome"], "draw")
        self.assertEqual(upset["team"], "平局")
        top_scores = {item["score"] for item in result["possible_scores"]}
        self.assertNotIn(upset["score"], top_scores)
        self.assertNotEqual(upset["score"], result["predicted_score"])
        home_goals, away_goals = [int(part) for part in upset["score"].split("-")]
        self.assertEqual(home_goals, away_goals)

        self.assertEqual(upset["score"], "0-0")
        self.assertTrue(
            any("进球下修" in reason or "0-0" in reason for reason in upset["reasons"]),
            upset["reasons"],
        )

    def test_moderate_high_total_draw_upset_uses_two_two(self):
        with patch.dict("os.environ", {"ODDS_MARKET_ENABLED": "false"}, clear=False):
            result = predict_match("Canada", "Bosnia and Herzegovina", model_type="form_weighted")

        upset = result["upset_prediction"]
        self.assertEqual(upset["outcome"], "draw")
        self.assertEqual(upset["score"], "2-2")

    def test_set_piece_and_card_prediction_has_numbers_and_basis(self):
        with patch.dict("os.environ", {"ODDS_MARKET_ENABLED": "false"}, clear=False):
            result = predict_match("Sweden", "Tunisia")

        props = result["set_piece_card_prediction"]
        self.assertIn("corners", props)
        self.assertIn("yellow_cards", props)
        self.assertGreater(props["corners"]["total"], 0)
        self.assertGreater(props["yellow_cards"]["total"], 0)
        self.assertGreaterEqual(len(props["basis"]), 3)
        self.assertTrue(any("角球" in item for item in props["basis"]))
        self.assertTrue(any("黄牌" in item for item in props["basis"]))

    def test_nearby_favorites_do_not_all_collapse_to_two_one(self):
        fixtures = [
            ("Czech Republic", "South Africa"),
            ("Switzerland", "Bosnia and Herzegovina"),
            ("Canada", "Qatar"),
            ("Mexico", "Korea Republic"),
        ]

        with patch.dict("os.environ", {"ODDS_MARKET_ENABLED": "false"}, clear=False):
            scores = [
                predict_match(home, away, model_type="form_weighted", match_round=2)["predicted_score"]
                for home, away in fixtures
            ]

        self.assertGreater(len(set(scores)), 1)
        self.assertLess(scores.count("2-1"), len(scores))

    def test_win_edge_does_not_default_to_draw_score_mode(self):
        fixtures = [
            ("Czech Republic", "South Africa"),
            ("Canada", "Qatar"),
            ("Brazil", "Morocco"),
        ]

        with patch.dict("os.environ", {"ODDS_MARKET_ENABLED": "false"}, clear=False):
            scores = [
                predict_match(home, away, model_type="form_weighted", match_round=2)["predicted_score"]
                for home, away in fixtures
            ]

        self.assertNotIn("1-1", scores)

    def test_moderate_favorite_upsets_are_not_default_draws(self):
        fixtures = [
            ("Czech Republic", "South Africa"),
            ("Canada", "Qatar"),
            ("Brazil", "Morocco"),
        ]

        with patch.dict("os.environ", {"ODDS_MARKET_ENABLED": "false"}, clear=False):
            outcomes = [
                predict_match(home, away, model_type="form_weighted", match_round=2)["upset_prediction"]["outcome"]
                for home, away in fixtures
            ]

        self.assertIn("away", outcomes)
        self.assertLess(outcomes.count("draw"), len(outcomes))

    def test_prediction_uses_latest_fifa_ranking_snapshot(self):
        with patch.dict("os.environ", {"ODDS_MARKET_ENABLED": "false"}, clear=False):
            result = predict_match("Portugal", "DR Congo")

        self.assertEqual(result["ranking_snapshot"]["source"], "FIFA/Coca-Cola Men's World Ranking")
        self.assertEqual(result["ranking_snapshot"]["last_updated"], "2026-06-11")
        self.assertIn("2026-06-11", result["ranking_snapshot"]["message"])
        self.assertTrue(any("#5 vs #46" in factor for factor in result["factors"]))

    def test_primary_score_probability_is_explicit(self):
        with patch.dict("os.environ", {"ODDS_MARKET_ENABLED": "false"}, clear=False):
            result = predict_match("Argentina", "France")

        self.assertIn("predicted_score_probability", result)
        self.assertEqual(result["predicted_score"], result["possible_scores"][0]["score"])
        self.assertEqual(result["predicted_score_probability"], result["possible_scores"][0]["probability"])

    def test_primary_score_uses_highest_probability_even_with_high_tempo_candidate(self):
        with patch.dict("os.environ", {"ODDS_MARKET_ENABLED": "false"}, clear=False):
            result = predict_match("USA", "Paraguay", model_type="form_weighted")

        probabilities = [item["probability"] for item in result["possible_scores"]]
        self.assertEqual(result["predicted_score"], result["possible_scores"][0]["score"])
        self.assertEqual(result["predicted_score_probability"], result["possible_scores"][0]["probability"])
        self.assertEqual(probabilities, sorted(probabilities, reverse=True))

    def test_upset_score_does_not_duplicate_top_score_candidates(self):
        with patch.dict("os.environ", {"ODDS_MARKET_ENABLED": "false"}, clear=False):
            result = predict_match("Brazil", "Morocco", model_type="form_weighted")

        top_scores = {item["score"] for item in result["possible_scores"]}
        upset = result["upset_prediction"]
        self.assertNotIn(upset["score"], top_scores)
        predicted_total = sum(int(part) for part in result["predicted_score"].split("-"))
        upset_total = sum(int(part) for part in upset["score"].split("-"))
        self.assertLessEqual(abs(upset_total - predicted_total), 2)


if __name__ == "__main__":
    unittest.main()
