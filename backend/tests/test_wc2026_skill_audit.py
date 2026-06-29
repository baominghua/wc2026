import sys
import unittest
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from services.wc2026_skill_audit import build_skill_audit


def prediction_payload(**overrides):
    payload = {
        "home_win_probability": 0.55,
        "draw_probability": 0.24,
        "away_win_probability": 0.21,
        "predicted_score": "2-1",
        "possible_scores": [
            {"score": "2-1", "probability": 11.2},
            {"score": "2-0", "probability": 9.8},
            {"score": "1-0", "probability": 8.6},
        ],
        "xg_home": 1.95,
        "xg_away": 1.12,
        "confidence": 0.56,
        "market_calibration": {"applied": False},
        "factors": ["model factor"],
    }
    payload.update(overrides)
    return payload


class WC2026SkillAuditTests(unittest.TestCase):
    def test_partial_group_favorite_adds_draw_protection_and_rich_analysis(self):
        audit = build_skill_audit(
            prediction_payload(),
            match={
                "home_team": "美国",
                "away_team": "澳大利亚",
                "round": 1,
                "group": "D",
                "status": "upcoming",
            },
        )

        self.assertEqual(audit["evidence_status"], "partial")
        self.assertEqual(audit["match_type"]["primary"], "C")
        self.assertEqual(audit["score_pool_top3"][-1], "1-1")
        self.assertEqual(audit["score_adjustment"]["action"], "draw_protection")
        self.assertTrue(any("平局保护" in item for item in audit["risk_flags"]))
        self.assertIn("单场简析", audit["single_match_brief"]["title"])
        self.assertIn("Top3", "\n".join(audit["single_match_brief"]["paragraphs"]))

    def test_strong_favorite_keeps_first_score_and_adds_overflow_note(self):
        audit = build_skill_audit(
            prediction_payload(
                home_win_probability=0.82,
                draw_probability=0.12,
                away_win_probability=0.06,
                predicted_score="3-0",
                possible_scores=[
                    {"score": "3-0", "probability": 13.2},
                    {"score": "2-0", "probability": 11.1},
                    {"score": "4-0", "probability": 8.4},
                ],
                xg_home=3.02,
                xg_away=0.62,
                confidence=0.79,
            ),
            match={
                "home_team": "巴西",
                "away_team": "海地",
                "round": 2,
                "group": "C",
                "status": "upcoming",
            },
        )

        self.assertEqual(audit["first_score_pick"], "3-0")
        self.assertEqual(audit["score_pool_top3"], ["3-0", "2-0", "4-0"])
        self.assertEqual(audit["score_adjustment"]["action"], "overflow_watch")
        self.assertIn("3-1", audit["secondary_scores"])
        self.assertTrue(any("大胜溢出" in item for item in audit["risk_flags"]))
        self.assertIn("强队突破", audit["match_type"]["label"])

    def test_third_round_group_context_surfaces_motivation_view(self):
        audit = build_skill_audit(
            prediction_payload(draw_probability=0.29, xg_home=1.45, xg_away=1.22),
            match={
                "home_team": "加拿大",
                "away_team": "瑞士",
                "round": 3,
                "group": "B",
                "status": "upcoming",
            },
            group_context={
                "home": {"points": 3, "goal_diff": 0},
                "away": {"points": 4, "goal_diff": 1},
            },
        )

        self.assertEqual(audit["group_motivation"]["round"], 3)
        self.assertTrue(audit["group_motivation"]["draw_value"])
        self.assertTrue(any("第三轮" in item for item in audit["macro_takeaways"]))
        self.assertTrue(any("平局" in paragraph for paragraph in audit["single_match_brief"]["paragraphs"]))

    def test_third_round_brief_prioritizes_group_strategy_and_knockout_path(self):
        audit = build_skill_audit(
            prediction_payload(
                review_adjustment={
                    "applied": True,
                    "home_attack_delta": 0.018,
                    "away_attack_delta": 0.012,
                    "draw_probability_delta": 0.04,
                    "reasons": ["瑞士 小组前两轮状态校准 +0.018", "加拿大 小组前两轮状态校准 +0.012"],
                    "review_context": {
                        "mode": "third_round_group_strategy",
                        "summary": "第三轮观点优先读取小组前两轮表现、出线路径和潜在淘汰赛对手。",
                        "team_review_notes": [
                            "瑞士小组前2轮累计4分，进失球3-1；最近一场1-1波兰打平，第三轮重点转向出线安全线、名次路径和轮换风险",
                            "加拿大小组前2轮累计4分，进失球3-2；最近一场2-1卡塔尔赢球，第三轮重点转向出线安全线、名次路径和轮换风险",
                        ],
                        "strategy_notes": [
                            "瑞士4分排名第1，已接近出线但第一/第二路径未定；优先稳住不败，再根据同组实时比分和潜在淘汰赛对手调整进取心。",
                            "加拿大4分排名第2，已接近出线但第一/第二路径未定；优先稳住不败，再根据同组实时比分和潜在淘汰赛对手调整进取心。",
                        ],
                        "knockout_path_notes": [
                            "潜在淘汰赛路径尚未完全锁定，默认不假设主动挑对手；只有第一/第二对应强弱差清晰时，才把路径选择作为低权重变量。"
                        ],
                        "red_card_notes": [],
                        "fallback_notes": [],
                    },
                },
            ),
            match={
                "home_team": "瑞士",
                "away_team": "加拿大",
                "round": 3,
                "group": "B",
                "status": "upcoming",
            },
            group_context={
                "home": {"points": 4, "goal_diff": 2, "rank": 1},
                "away": {"points": 4, "goal_diff": 1, "rank": 2},
            },
        )

        rendered = "\n".join(audit["single_match_brief"]["paragraphs"] + audit["single_match_brief"]["bullets"])
        self.assertEqual(audit["review_layer"]["source"], "第三轮战意与路径复核")
        self.assertIn("第三轮单场简析", rendered)
        self.assertIn("潜在淘汰赛", rendered)
        self.assertIn("低权重变量", rendered)
        self.assertNotIn("上一轮真实复盘", rendered)
        self.assertNotIn("所以第二轮", rendered)

    def test_second_round_brief_uses_actual_first_round_review_context(self):
        audit = build_skill_audit(
            prediction_payload(
                review_adjustment={
                    "applied": True,
                    "home_attack_delta": 0.018,
                    "away_attack_delta": -0.018,
                    "draw_probability_delta": 0.04,
                    "reasons": ["双方首轮都有积分，平局对小组形势都有价值，因此保守提高平局权重。"],
                    "review_context": {
                        "mode": "actual_first_round_review",
                        "summary": "已匹配到两队上一轮真实赛果，第二轮观点优先读取真实复盘。",
                        "completed_sample_count": 24,
                        "same_group_completed_count": 2,
                        "team_review_notes": [
                            "墨西哥上一轮2-0南非赢球，拿到3分，第二轮可以更主动地管理节奏",
                            "韩国上一轮2-1捷克赢球，拿到3分，第二轮可以更主动地管理节奏",
                        ],
                        "red_card_notes": [],
                        "fallback_notes": [],
                    },
                }
            ),
            match={
                "home_team": "墨西哥",
                "away_team": "韩国",
                "round": 2,
                "group": "A",
                "status": "upcoming",
            },
        )

        rendered = "\n".join(audit["single_match_brief"]["paragraphs"] + audit["single_match_brief"]["bullets"])
        self.assertEqual(audit["review_layer"]["source"], "上一轮真实复盘")
        self.assertIn("上一轮真实复盘", rendered)
        self.assertIn("墨西哥上一轮2-0南非", rendered)
        self.assertIn("第二轮不只看纸面实力", rendered)

    def test_second_round_brief_falls_back_to_simulated_backtest_review(self):
        audit = build_skill_audit(
            prediction_payload(
                review_adjustment={
                    "applied": False,
                    "home_attack_delta": 0.0,
                    "away_attack_delta": 0.0,
                    "draw_probability_delta": 0.0,
                    "reasons": [],
                    "review_context": {
                        "mode": "simulated_backtest_review",
                        "summary": "暂无两队完整上一轮复盘样本，使用当前模型回测纪律兜底。",
                        "completed_sample_count": 4,
                        "same_group_completed_count": 0,
                        "team_review_notes": [],
                        "red_card_notes": [],
                        "fallback_notes": [
                            "回测兜底先看五项：赛果方向、首选比分、Top3比分池、总进球区间、双方进球。"
                        ],
                    },
                }
            ),
            match={
                "home_team": "巴西",
                "away_team": "海地",
                "round": 2,
                "group": "C",
                "status": "upcoming",
            },
        )

        rendered = "\n".join(audit["single_match_brief"]["paragraphs"] + audit["single_match_brief"]["bullets"])
        self.assertEqual(audit["review_layer"]["source"], "模拟回测复盘兜底")
        self.assertIn("模拟回测复盘兜底", rendered)
        self.assertIn("Top3比分池", rendered)
        self.assertNotIn("首轮结果未知", rendered)
        self.assertNotIn("结果未知", rendered)

    def test_knockout_brief_uses_full_group_stage_review_and_decision_layer(self):
        audit = build_skill_audit(
            prediction_payload(
                is_knockout=True,
                draw_probability=0.0,
                penalty_probability=0.18,
                extra_time_probability=0.27,
                knockout_decision={
                    "regular_time_draw_probability": 0.27,
                    "extra_time_decisive_probability": 0.09,
                    "penalty_probability": 0.18,
                    "advancement_home_probability": 0.58,
                    "advancement_away_probability": 0.42,
                },
                review_adjustment={
                    "applied": True,
                    "home_attack_delta": 0.018,
                    "away_attack_delta": -0.006,
                    "draw_probability_delta": 0.0,
                    "reasons": ["阿根廷 小组赛全阶段状态校准 +0.018"],
                    "review_context": {
                        "mode": "knockout_group_stage_review",
                        "summary": "淘汰赛观点读取两队小组赛全阶段表现，并单独处理90分钟、加时和点球决胜层。",
                        "team_review_notes": [
                            "阿根廷小组赛全阶段累计7分，进失球6-1；淘汰赛重点转向90分钟控制、加时体能和点球风险",
                        ],
                        "strategy_notes": [],
                        "knockout_path_notes": [],
                        "red_card_notes": [],
                        "fallback_notes": [],
                    },
                },
            ),
            match={
                "home_team": "阿根廷",
                "away_team": "葡萄牙",
                "stage": "Round of 32",
                "status": "upcoming",
            },
        )

        rendered = "\n".join(audit["single_match_brief"]["paragraphs"] + audit["single_match_brief"]["bullets"])
        self.assertEqual(audit["review_layer"]["source"], "淘汰赛全小组赛复盘")
        self.assertIn("小组赛全阶段", rendered)
        self.assertIn("90分钟", rendered)
        self.assertIn("加时", rendered)
        self.assertIn("点球", rendered)
        self.assertNotIn("第三轮单场简析", rendered)
        self.assertNotIn("上一轮真实复盘", rendered)

    def test_historical_market_prior_is_described_as_config_gap_not_missing_match(self):
        audit = build_skill_audit(
            prediction_payload(
                market_odds={
                    "available": True,
                    "status": "historical_prior",
                    "source": "football_data_historical_prior",
                    "h2h": {"home": 0.51, "draw": 0.27, "away": 0.22},
                },
                market_calibration={
                    "applied": False,
                    "level": "historical_prior",
                    "source": "football_data_historical_prior",
                },
            ),
            match={
                "home_team": "阿根廷",
                "away_team": "奥地利",
                "round": 2,
                "group": "J",
                "status": "upcoming",
            },
        )

        text = "\n".join(audit["missing_information"])
        self.assertIn("Football-Data 历史赔率样本", text)
        self.assertNotIn("未匹配到本场", text)


if __name__ == "__main__":
    unittest.main()
