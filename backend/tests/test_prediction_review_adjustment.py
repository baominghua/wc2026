import sys
import unittest
import re
from pathlib import Path
from unittest.mock import patch


BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from services.prediction_model import predict_match


class PredictionReviewAdjustmentTests(unittest.TestCase):
    def test_review_adjustment_can_raise_draw_probability_without_replacing_model(self):
        with patch.dict("os.environ", {"ODDS_MARKET_ENABLED": "false"}, clear=False):
            baseline = predict_match("Mexico", "Korea Republic", match_round=2)
            adjusted = predict_match(
                "Mexico",
                "Korea Republic",
                match_round=2,
                review_adjustment={
                    "applied": True,
                    "home_attack_delta": 0.0,
                    "away_attack_delta": 0.0,
                    "draw_probability_delta": 0.05,
                    "reasons": ["Draw gives both teams at least four points."],
                },
            )

        self.assertGreater(adjusted["draw_probability"], baseline["draw_probability"])
        self.assertTrue(any("赛后复盘" in factor for factor in adjusted["factors"]))
        self.assertNotEqual(adjusted["predicted_score"], "")

    def test_current_world_cup_form_window_replaces_static_form_score(self):
        review_adjustment = {
            "applied": True,
            "home_attack_delta": 0.0,
            "away_attack_delta": 0.0,
            "draw_probability_delta": 0.0,
            "reasons": ["荷兰首轮2-2日本，瑞典首轮5-1突尼斯"],
            "review_context": {
                "mode": "actual_first_round_review",
                "form_context": {
                    "home": {
                        "team": "荷兰",
                        "sample_matches": 4,
                        "world_cup_sample_matches": 1,
                        "pre_world_cup_sample_matches": 3,
                        "prop_sample_policy": "official_mean",
                        "source_label": "本届世界杯1场 + 世界杯前3场正式赛均值",
                        "score": 6.3,
                        "corners_for": 5,
                        "corners_against": 4,
                        "yellow_cards_for": 0,
                        "yellow_cards_against": 0,
                        "note": "荷兰本届世界杯1场 + 世界杯前3场正式赛均值：场均1.0分，净胜球+0.0，进失球2.0-2.0，射正差+3.0",
                    },
                    "away": {
                        "team": "瑞典",
                        "sample_matches": 4,
                        "world_cup_sample_matches": 1,
                        "pre_world_cup_sample_matches": 3,
                        "prop_sample_policy": "official_mean",
                        "source_label": "本届世界杯1场 + 世界杯前3场正式赛均值",
                        "score": 9.2,
                        "corners_for": 4,
                        "corners_against": 2,
                        "yellow_cards_for": 1,
                        "yellow_cards_against": 1,
                        "note": "瑞典本届世界杯1场 + 世界杯前3场正式赛均值：场均3.0分，净胜球+4.0，进失球5.0-1.0，射正差+5.0",
                    },
                },
            },
        }

        with patch.dict("os.environ", {"ODDS_MARKET_ENABLED": "false"}, clear=False):
            result = predict_match("Netherlands", "Sweden", match_round=2, review_adjustment=review_adjustment)

        factor_text = "\n".join(result["factors"])
        self.assertIn("状态权重", factor_text)
        self.assertIn("本届世界杯1场 + 世界杯前3场正式赛均值", factor_text)
        self.assertNotIn("小组赛首轮", factor_text)
        match = re.search(r"荷兰 ([0-9.]+)/10.*瑞典 ([0-9.]+)/10", factor_text)
        self.assertIsNotNone(match, factor_text)
        self.assertGreater(float(match.group(2)), float(match.group(1)))
        basis = result["set_piece_card_prediction"]["basis"]
        self.assertTrue(any("本届世界杯1场 + 世界杯前3场正式赛均值" in item for item in basis))
        self.assertFalse(any("最近1场" in item for item in basis))
        self.assertTrue(any("0.0 张" in item for item in result["set_piece_card_prediction"]["yellow_cards"]["basis"]))
        self.assertTrue(any("近况窗口" in factor for factor in result["factors"]))

    def test_third_round_near_qualified_context_raises_draw_and_lowers_total_xg(self):
        review_adjustment = {
            "applied": True,
            "home_attack_delta": 0.0,
            "away_attack_delta": 0.0,
            "draw_probability_delta": 0.0,
            "reasons": [],
            "review_context": {
                "mode": "third_round_group_strategy",
                "third_round_strategy": {
                    "home": {"team": "Switzerland", "points": 4, "rank": 2, "status": "near_qualified"},
                    "away": {"team": "Canada", "points": 4, "rank": 1, "status": "near_qualified"},
                    "path_weight": "low",
                },
                "strategy_notes": [
                    "Switzerland已接近出线但第一/第二路径未定；优先稳住不败",
                    "Canada已接近出线但第一/第二路径未定；优先稳住不败",
                ],
            },
        }

        with patch.dict("os.environ", {"ODDS_MARKET_ENABLED": "false"}, clear=False):
            baseline = predict_match("Switzerland", "Canada", match_round=3)
            adjusted = predict_match("Switzerland", "Canada", match_round=3, review_adjustment=review_adjustment)

        baseline_total = baseline["xg_home"] + baseline["xg_away"]
        adjusted_total = adjusted["xg_home"] + adjusted["xg_away"]
        factor_text = "\n".join(adjusted["factors"])

        self.assertGreater(adjusted["draw_probability"], baseline["draw_probability"] + 0.015)
        self.assertLess(adjusted_total, baseline_total)
        self.assertIn("第三轮战意", factor_text)
        self.assertIn("出线形势高权重", factor_text)
        self.assertIn("潜在路径低权重", factor_text)

    def test_third_round_must_win_side_opens_game_without_forcing_draw(self):
        review_adjustment = {
            "applied": True,
            "home_attack_delta": 0.0,
            "away_attack_delta": 0.0,
            "draw_probability_delta": 0.0,
            "reasons": [],
            "review_context": {
                "mode": "third_round_group_strategy",
                "third_round_strategy": {
                    "home": {"team": "Scotland", "points": 1, "rank": 3, "status": "must_win"},
                    "away": {"team": "Brazil", "points": 6, "rank": 1, "status": "locked_first"},
                    "path_weight": "low",
                },
                "strategy_notes": [
                    "Scotland安全线不足，第三轮必须主动争胜或抢净胜球",
                    "Brazil小组第一主动权很高，轮换和保护核心球员权重上升",
                ],
            },
        }

        with patch.dict("os.environ", {"ODDS_MARKET_ENABLED": "false"}, clear=False):
            baseline = predict_match("Scotland", "Brazil", match_round=3)
            adjusted = predict_match("Scotland", "Brazil", match_round=3, review_adjustment=review_adjustment)

        baseline_total = baseline["xg_home"] + baseline["xg_away"]
        adjusted_total = adjusted["xg_home"] + adjusted["xg_away"]
        factor_text = "\n".join(adjusted["factors"])

        self.assertGreater(adjusted["xg_home"], baseline["xg_home"])
        self.assertGreater(adjusted_total, baseline_total)
        self.assertLess(adjusted["draw_probability"], baseline["draw_probability"] + 0.02)
        self.assertIn("必须争胜", factor_text)
        self.assertIn("轮换保护", factor_text)

    def test_knockout_prediction_exposes_regulation_extra_time_and_penalty_layers(self):
        with patch.dict("os.environ", {"ODDS_MARKET_ENABLED": "false"}, clear=False):
            result = predict_match("Argentina", "Portugal", is_knockout=True, stage="Round of 32")

        decision = result.get("knockout_decision")
        self.assertIsInstance(decision, dict)
        self.assertEqual(result["draw_probability"], 0.0)
        self.assertEqual(result["regulation_predicted_score"], result["predicted_score"])
        self.assertGreater(decision["regular_time_draw_probability"], 0.0)
        self.assertAlmostEqual(result["extra_time_probability"], decision["regular_time_draw_probability"], places=3)
        self.assertGreaterEqual(decision["penalty_probability"], 0.0)
        self.assertLessEqual(decision["penalty_probability"], decision["regular_time_draw_probability"])
        self.assertAlmostEqual(
            decision["advancement_home_probability"] + decision["advancement_away_probability"],
            1.0,
            places=3,
        )
        factor_text = "\n".join(result["factors"])
        self.assertIn("90分钟平局", factor_text)
        self.assertIn("加时", factor_text)
        self.assertIn("点球", factor_text)


if __name__ == "__main__":
    unittest.main()
