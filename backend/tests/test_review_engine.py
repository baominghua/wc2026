import sys
import unittest
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from services.review_engine import (
    build_prediction_audit,
    build_review_adjustment,
    generate_match_review,
)


def has_chinese(text):
    return any("\u4e00" <= char <= "\u9fff" for char in str(text))


def prediction(home=0.5, draw=0.25, away=0.25, score="1-0", scores=None, upset=None):
    return {
        "home_win_probability": home,
        "draw_probability": draw,
        "away_win_probability": away,
        "predicted_score": score,
        "possible_scores": scores or [{"score": score, "probability": 18.5}],
        "upset_prediction": upset or {
            "outcome": "draw",
            "score": "1-1",
            "probability": 0.18,
            "reasons": ["draw pressure"],
        },
        "total_goals_prediction": {
            "main_line": 2.5,
            "recommendation": "over 2.5",
        },
        "xg_home": 1.6,
        "xg_away": 1.0,
        "factors": ["unit test prediction"],
    }


class ReviewEngineTests(unittest.TestCase):
    def test_audit_counts_top_picks_scores_and_upset_hits(self):
        matches = [
            {
                "id": 1,
                "home_team": "Mexico",
                "away_team": "South Africa",
                "group": "A",
                "round": 1,
                "status": "completed",
                "home_score": 2,
                "away_score": 0,
                "match_date": "2026-06-12T03:00:00+08:00",
                "venue": "Azteca",
            },
            {
                "id": 2,
                "home_team": "Korea Republic",
                "away_team": "Czech Republic",
                "group": "A",
                "round": 1,
                "status": "completed",
                "home_score": 2,
                "away_score": 1,
                "match_date": "2026-06-12T10:00:00+08:00",
                "venue": "Akron",
            },
        ]
        predictions = {
            1: prediction(home=0.64, draw=0.21, away=0.15, score="2-0"),
            2: prediction(
                home=0.31,
                draw=0.22,
                away=0.47,
                score="1-2",
                scores=[
                    {"score": "1-2", "probability": 12.1},
                    {"score": "1-1", "probability": 10.4},
                    {"score": "2-1", "probability": 8.2},
                ],
                upset={
                    "outcome": "home",
                    "score": "2-1",
                    "probability": 0.19,
                    "reasons": ["home transition edge"],
                },
            ),
        }

        audit = build_prediction_audit(matches, predictions_by_match=predictions)

        self.assertEqual(audit["summary"]["completed_matches"], 2)
        self.assertEqual(audit["summary"]["outcome_top1_hits"], 1)
        self.assertEqual(audit["summary"]["outcome_top2_hits"], 2)
        self.assertEqual(audit["summary"]["outcome_top3_hits"], 2)
        self.assertEqual(audit["summary"]["wdl_hits"], 1)
        self.assertEqual(audit["summary"]["wdl_accuracy"], 0.5)
        self.assertEqual(audit["summary"]["score_top1_hits"], 1)
        self.assertEqual(audit["summary"]["score_top3_hits"], 2)
        self.assertEqual(audit["summary"]["upset_hits"], 1)
        self.assertEqual(audit["summary"]["score_pick1_hits"], 1)
        self.assertEqual(audit["summary"]["score_pick2_hits"], 0)
        self.assertEqual(audit["summary"]["score_pick3_hits"], 1)
        self.assertEqual(audit["summary"]["upset_score_hits"], 0)
        self.assertEqual(audit["summary"]["score_pool_hits"], 2)
        self.assertEqual(audit["summary"]["score_pool_accuracy"], 1.0)
        self.assertEqual(audit["summary"]["score_total_hits"], 2)
        self.assertEqual(audit["summary"]["score_total_accuracy"], 1.0)
        self.assertEqual(audit["summary"]["total_goals_range_hits"], 2)
        self.assertEqual(audit["summary"]["total_goals_range_accuracy"], 1.0)
        self.assertEqual(audit["summary"]["btts_hits"], 1)
        self.assertEqual(audit["summary"]["btts_accuracy"], 0.5)
        self.assertEqual(len(audit["rows"]), 2)
        self.assertEqual(audit["rows"][0]["prediction"]["total_goals_range"], "2-4")
        self.assertEqual(audit["rows"][0]["prediction"]["btts_view"], "lean-no")
        self.assertTrue(audit["rows"][0]["accuracy"]["total_goals_range_hit"])
        self.assertTrue(audit["rows"][0]["accuracy"]["btts_hit"])
        self.assertTrue(audit["rows"][0]["accuracy"]["wdl_hit"])
        self.assertFalse(audit["rows"][1]["accuracy"]["wdl_hit"])

    def test_score_pool_slots_are_mutually_exclusive(self):
        match = {
            "id": 3,
            "home_team": "Korea Republic",
            "away_team": "Czech Republic",
            "group": "A",
            "round": 1,
            "status": "completed",
            "home_score": 2,
            "away_score": 1,
            "match_date": "2026-06-12T10:00:00+08:00",
            "venue": "Akron",
        }
        pred = prediction(
            home=0.31,
            draw=0.22,
            away=0.47,
            score="1-2",
            scores=[
                {"score": "1-2", "probability": 12.1},
                {"score": "2-1", "probability": 10.4},
                {"score": "1-1", "probability": 8.2},
            ],
            upset={
                "outcome": "home",
                "score": "2-1",
                "probability": 0.19,
                "reasons": ["duplicate upset score"],
            },
        )

        report = generate_match_review(match, pred)
        audit = build_prediction_audit([match], predictions_by_match={3: pred})

        self.assertEqual(report["prediction"]["score_candidates"], ["1-2", "2-1", "1-1"])
        self.assertFalse(report["accuracy"]["score_pick1"])
        self.assertTrue(report["accuracy"]["score_pick2"])
        self.assertFalse(report["accuracy"]["score_pick3"])
        self.assertFalse(report["accuracy"]["upset_score_hit"])
        self.assertTrue(report["accuracy"]["score_pool_hit"])
        self.assertEqual(audit["summary"]["score_pick2_hits"], 1)
        self.assertEqual(audit["summary"]["upset_score_hits"], 0)
        self.assertEqual(audit["summary"]["score_pool_hits"], 1)
        self.assertEqual(audit["summary"]["score_pool_accuracy"], 1.0)

    def test_audit_excludes_completed_matches_without_pre_match_snapshot(self):
        matches = [
            {
                "id": 1,
                "home_team": "Mexico",
                "away_team": "South Africa",
                "group": "A",
                "round": 1,
                "status": "completed",
                "home_score": 2,
                "away_score": 0,
                "match_date": "2026-06-12T03:00:00+08:00",
                "venue": "Azteca",
            },
            {
                "id": 2,
                "home_team": "Korea Republic",
                "away_team": "Czech Republic",
                "group": "A",
                "round": 1,
                "status": "completed",
                "home_score": 2,
                "away_score": 1,
                "match_date": "2026-06-12T10:00:00+08:00",
                "venue": "Akron",
            },
        ]
        predictions = {
            1: prediction(home=0.64, draw=0.21, away=0.15, score="2-0"),
        }

        audit = build_prediction_audit(matches, predictions_by_match=predictions)

        self.assertEqual(audit["summary"]["completed_matches"], 2)
        self.assertEqual(audit["summary"]["reviewed_matches"], 1)
        self.assertEqual(audit["summary"]["missing_prediction_count"], 1)
        self.assertEqual(len(audit["rows"]), 1)
        self.assertEqual(len(audit["missing_prediction_matches"]), 1)
        self.assertEqual(audit["missing_prediction_matches"][0]["match_id"], 2)
        self.assertIn("赛前预测快照", audit["source_policy"])

    def test_audit_ignores_pre_world_cup_official_matches_in_tournament_counts(self):
        matches = [
            {
                "id": 1,
                "home_team": "Mexico",
                "away_team": "South Africa",
                "group": "A",
                "round": 1,
                "status": "completed",
                "home_score": 2,
                "away_score": 0,
                "match_date": "2026-06-12T03:00:00+08:00",
                "venue": "Azteca",
            },
            {
                "id": 9001,
                "home_team": "Mexico",
                "away_team": "Chile",
                "competition": "World Cup Qualifying",
                "is_official": True,
                "status": "completed",
                "home_score": 1,
                "away_score": 1,
                "match_date": "2026-03-25T10:00:00+08:00",
                "venue": "Friendly",
            },
        ]
        predictions = {
            1: prediction(home=0.64, draw=0.21, away=0.15, score="2-0"),
            9001: prediction(home=0.44, draw=0.31, away=0.25, score="1-1"),
        }

        audit = build_prediction_audit(matches, predictions_by_match=predictions)

        self.assertEqual(audit["summary"]["completed_matches"], 1)
        self.assertEqual(audit["summary"]["reviewed_matches"], 1)
        self.assertEqual(audit["summary"]["missing_prediction_count"], 0)
        self.assertEqual([row["match_id"] for row in audit["rows"]], [1])

    def test_match_review_explains_finishing_and_control_variance(self):
        match = {
            "id": 12,
            "home_team": "Sweden",
            "away_team": "Tunisia",
            "group": "F",
            "round": 1,
            "status": "completed",
            "home_score": 5,
            "away_score": 1,
            "match_date": "2026-06-15T10:00:00+08:00",
            "venue": "BBVA Stadium",
            "report": {
                "stats": {
                    "xg_home": 2.4,
                    "xg_away": 0.8,
                    "possession_home": 58,
                    "possession_away": 42,
                    "shots_home": 18,
                    "shots_away": 7,
                    "corners_home": 8,
                    "corners_away": 2,
                    "yellow_cards_home": 1,
                    "yellow_cards_away": 4,
                }
            },
        }
        pred = prediction(home=0.34, draw=0.31, away=0.35, score="1-1")

        report = generate_match_review(match, pred)

        self.assertFalse(report["accuracy"]["outcome_top1"])
        self.assertFalse(report["accuracy"]["score_top1"])
        self.assertGreaterEqual(len(report["variance_notes"]), 2)
        self.assertTrue(any(note["type"] == "finishing_variance" for note in report["variance_notes"]))
        self.assertTrue(any(note["type"] == "match_control" for note in report["variance_notes"]))
        self.assertGreater(report["next_adjustments"]["Sweden"]["attack_delta"], 0)

    def test_match_review_explains_red_card_driven_blowout(self):
        match = {
            "id": 31,
            "home_team": "Argentina",
            "away_team": "Jordan",
            "group": "J",
            "round": 1,
            "status": "completed",
            "home_score": 4,
            "away_score": 0,
            "match_date": "2026-06-17T10:00:00+08:00",
            "venue": "Lumen Field",
            "report": {
                "cards": [
                    {
                        "minute": 38,
                        "team": "Jordan",
                        "player": "Ali Example",
                        "type": "red_card",
                    }
                ],
                "goals": [
                    {"minute": 22, "team": "Argentina", "player": "Forward A", "type": "goal"},
                    {"minute": 51, "team": "Argentina", "player": "Forward B", "type": "goal"},
                    {"minute": 78, "team": "Argentina", "player": "Forward C", "type": "goal"},
                    {"minute": 90, "team": "Argentina", "player": "Forward D", "type": "goal"},
                ],
                "stats": {
                    "xg_home": 2.2,
                    "xg_away": 0.3,
                    "shots_home": 21,
                    "shots_away": 3,
                    "possession_home": 67,
                    "possession_away": 33,
                    "red_cards_away": 1,
                },
            },
        }
        pred = prediction(home=0.62, draw=0.23, away=0.15, score="2-0")

        report = generate_match_review(match, pred)

        self.assertTrue(any(note["type"] == "red_card_turning_point" for note in report["variance_notes"]))
        rendered = "\n".join(
            [note["title"] + "\n" + note["detail"] for note in report["variance_notes"]]
            + report["lessons"]
        )
        self.assertIn("\u7ea2\u724c", rendered)
        self.assertTrue("\u4eba\u6570\u52a3\u52bf" in rendered or "\u5c11\u6253\u4e00\u4eba" in rendered)
        self.assertTrue(any("\u7ea2\u724c" in lesson for lesson in report["lessons"]))

    def test_match_review_outputs_chinese_notes_and_lessons(self):
        match = {
            "id": 23,
            "home_team": "Portugal",
            "away_team": "Ghana",
            "group": "H",
            "round": 1,
            "status": "completed",
            "home_score": 1,
            "away_score": 2,
            "match_date": "2026-06-16T10:00:00+08:00",
            "venue": "Arrowhead Stadium",
            "report": {
                "stats": {
                    "xg_home": 1.9,
                    "xg_away": 0.7,
                    "possession_home": 63,
                    "possession_away": 37,
                    "shots_home": 17,
                    "shots_away": 8,
                    "corners_home": 7,
                    "corners_away": 3,
                    "yellow_cards_home": 4,
                    "yellow_cards_away": 2,
                }
            },
        }
        pred = prediction(home=0.61, draw=0.23, away=0.16, score="2-0")

        report = generate_match_review(match, pred)

        self.assertTrue(all(has_chinese(note["title"]) for note in report["variance_notes"]))
        self.assertTrue(all(has_chinese(note["detail"]) for note in report["variance_notes"]))
        self.assertTrue(all(has_chinese(item) for item in report["lessons"]))
        rendered = "\n".join(
            [note["title"] + "\n" + note["detail"] for note in report["variance_notes"]]
            + report["lessons"]
        )
        for phrase in [
            "Outcome direction missed",
            "Finishing variance",
            "Possession",
            "Future forecasts",
            "Actual result",
            "draw probability",
        ]:
            self.assertNotIn(phrase, rendered)

    def test_review_adjustment_adds_draw_incentive_when_draw_benefits_both(self):
        matches = [
            {
                "id": 1,
                "home_team": "Mexico",
                "away_team": "South Africa",
                "group": "A",
                "round": 1,
                "status": "completed",
                "home_score": 2,
                "away_score": 0,
                "match_date": "2026-06-12T03:00:00+08:00",
                "venue": "Azteca",
            },
            {
                "id": 2,
                "home_team": "Korea Republic",
                "away_team": "Czech Republic",
                "group": "A",
                "round": 1,
                "status": "completed",
                "home_score": 2,
                "away_score": 1,
                "match_date": "2026-06-12T10:00:00+08:00",
                "venue": "Akron",
            },
        ]
        future_match = {
            "id": 17,
            "home_team": "Mexico",
            "away_team": "Korea Republic",
            "group": "A",
            "round": 2,
            "status": "upcoming",
            "match_date": "2026-06-18T09:00:00+08:00",
            "venue": "Azteca",
        }

        adjustment = build_review_adjustment(future_match, matches)

        self.assertGreaterEqual(adjustment["draw_probability_delta"], 0.035)
        self.assertTrue(adjustment["applied"])
        self.assertTrue(any("平局" in reason for reason in adjustment["reasons"]))
        self.assertEqual(adjustment["review_context"]["mode"], "actual_first_round_review")
        self.assertTrue(any("Mexico上一轮2-0South Africa" in note for note in adjustment["review_context"]["team_review_notes"]))

    def test_third_round_review_adjustment_uses_group_strategy_not_first_round_label(self):
        matches = [
            {
                "id": 101,
                "home_team": "Switzerland",
                "away_team": "Qatar",
                "group": "B",
                "round": 1,
                "status": "completed",
                "home_score": 2,
                "away_score": 0,
                "match_date": "2026-06-13T03:00:00+08:00",
            },
            {
                "id": 102,
                "home_team": "Canada",
                "away_team": "Poland",
                "group": "B",
                "round": 1,
                "status": "completed",
                "home_score": 1,
                "away_score": 1,
                "match_date": "2026-06-13T10:00:00+08:00",
            },
            {
                "id": 103,
                "home_team": "Switzerland",
                "away_team": "Poland",
                "group": "B",
                "round": 2,
                "status": "completed",
                "home_score": 1,
                "away_score": 1,
                "match_date": "2026-06-19T03:00:00+08:00",
            },
            {
                "id": 104,
                "home_team": "Canada",
                "away_team": "Qatar",
                "group": "B",
                "round": 2,
                "status": "completed",
                "home_score": 2,
                "away_score": 1,
                "match_date": "2026-06-19T10:00:00+08:00",
            },
        ]
        future_match = {
            "id": 201,
            "home_team": "Switzerland",
            "away_team": "Canada",
            "group": "B",
            "round": 3,
            "status": "upcoming",
            "match_date": "2026-06-25T03:00:00+08:00",
        }

        adjustment = build_review_adjustment(future_match, matches)
        rendered = "\n".join(adjustment["reasons"] + adjustment["review_context"]["team_review_notes"])

        self.assertEqual(adjustment["review_context"]["mode"], "third_round_group_strategy")
        self.assertIn("小组前两轮状态校准", rendered)
        self.assertIn("小组前2轮累计", rendered)
        self.assertIn("潜在淘汰赛", "\n".join(adjustment["review_context"]["knockout_path_notes"]))
        self.assertEqual(adjustment["review_context"]["third_round_strategy"]["home"]["status"], "near_qualified")
        self.assertEqual(adjustment["review_context"]["third_round_strategy"]["away"]["status"], "near_qualified")
        self.assertEqual(adjustment["review_context"]["third_round_strategy"]["path_weight"], "low")
        self.assertNotIn("首轮状态校准", rendered)

    def test_review_adjustment_blends_world_cup_and_pre_world_cup_official_means_before_three_wc_samples(self):
        matches = [
            {
                "id": 101,
                "home_team": "Netherlands",
                "away_team": "Greece",
                "competition": "UEFA Nations League",
                "is_official": True,
                "status": "completed",
                "home_score": 2,
                "away_score": 0,
                "match_date": "2026-03-20T04:00:00+08:00",
                "report": {
                    "stats": {
                        "shots_home": 12,
                        "shots_away": 7,
                        "shots_on_target_home": 5,
                        "shots_on_target_away": 2,
                        "corners_home": 6,
                        "corners_away": 3,
                        "yellow_cards_home": 2,
                        "yellow_cards_away": 1,
                    }
                },
            },
            {
                "id": 102,
                "home_team": "Denmark",
                "away_team": "Netherlands",
                "competition": "UEFA Nations League",
                "is_official": True,
                "status": "completed",
                "home_score": 1,
                "away_score": 1,
                "match_date": "2026-03-24T04:00:00+08:00",
                "report": {
                    "stats": {
                        "shots_home": 11,
                        "shots_away": 10,
                        "shots_on_target_home": 4,
                        "shots_on_target_away": 4,
                        "corners_home": 5,
                        "corners_away": 4,
                        "yellow_cards_home": 3,
                        "yellow_cards_away": 1,
                    }
                },
            },
            {
                "id": 103,
                "home_team": "Netherlands",
                "away_team": "Turkey",
                "competition": "World Cup Qualifying",
                "is_official": True,
                "status": "completed",
                "home_score": 1,
                "away_score": 2,
                "match_date": "2026-06-02T04:00:00+08:00",
                "report": {
                    "stats": {
                        "shots_home": 9,
                        "shots_away": 10,
                        "shots_on_target_home": 3,
                        "shots_on_target_away": 5,
                        "corners_home": 2,
                        "corners_away": 6,
                        "yellow_cards_home": 3,
                        "yellow_cards_away": 2,
                    }
                },
            },
            {
                "id": 111,
                "home_team": "Sweden",
                "away_team": "Norway",
                "competition": "UEFA Nations League",
                "is_official": True,
                "status": "completed",
                "home_score": 1,
                "away_score": 1,
                "match_date": "2026-03-21T04:00:00+08:00",
                "report": {
                    "stats": {
                        "shots_home": 8,
                        "shots_away": 9,
                        "shots_on_target_home": 3,
                        "shots_on_target_away": 4,
                        "corners_home": 3,
                        "corners_away": 5,
                        "yellow_cards_home": 1,
                        "yellow_cards_away": 2,
                    }
                },
            },
            {
                "id": 112,
                "home_team": "Poland",
                "away_team": "Sweden",
                "competition": "UEFA Nations League",
                "is_official": True,
                "status": "completed",
                "home_score": 2,
                "away_score": 1,
                "match_date": "2026-03-25T04:00:00+08:00",
                "report": {
                    "stats": {
                        "shots_home": 10,
                        "shots_away": 8,
                        "shots_on_target_home": 5,
                        "shots_on_target_away": 3,
                        "corners_home": 4,
                        "corners_away": 4,
                        "yellow_cards_home": 2,
                        "yellow_cards_away": 2,
                    }
                },
            },
            {
                "id": 113,
                "home_team": "Sweden",
                "away_team": "Finland",
                "competition": "World Cup Qualifying",
                "is_official": True,
                "status": "completed",
                "home_score": 2,
                "away_score": 0,
                "match_date": "2026-06-03T04:00:00+08:00",
                "report": {
                    "stats": {
                        "shots_home": 12,
                        "shots_away": 6,
                        "shots_on_target_home": 6,
                        "shots_on_target_away": 2,
                        "corners_home": 5,
                        "corners_away": 2,
                        "yellow_cards_home": 3,
                        "yellow_cards_away": 1,
                    }
                },
            },
            {
                "id": 10,
                "home_team": "Netherlands",
                "away_team": "Japan",
                "group": "F",
                "round": 1,
                "status": "completed",
                "home_score": 2,
                "away_score": 2,
                "match_date": "2026-06-15T04:00:00+08:00",
                "report": {
                    "stats": {
                        "shots_home": 10,
                        "shots_away": 10,
                        "shots_on_target_home": 6,
                        "shots_on_target_away": 3,
                        "corners_home": 5,
                        "corners_away": 4,
                        "yellow_cards_home": 0,
                        "yellow_cards_away": 0,
                    }
                },
            },
            {
                "id": 12,
                "home_team": "Sweden",
                "away_team": "Tunisia",
                "group": "F",
                "round": 1,
                "status": "completed",
                "home_score": 5,
                "away_score": 1,
                "match_date": "2026-06-15T10:00:00+08:00",
                "report": {
                    "stats": {
                        "shots_home": 13,
                        "shots_away": 6,
                        "shots_on_target_home": 7,
                        "shots_on_target_away": 2,
                        "corners_home": 4,
                        "corners_away": 2,
                        "yellow_cards_home": 0,
                        "yellow_cards_away": 1,
                    }
                },
            },
        ]
        future_match = {
            "id": 33,
            "home_team": "Netherlands",
            "away_team": "Sweden",
            "group": "F",
            "round": 2,
            "status": "upcoming",
            "match_date": "2026-06-21T01:00:00+08:00",
        }

        adjustment = build_review_adjustment(future_match, matches)
        form_context = adjustment["review_context"]["form_context"]

        self.assertEqual(form_context["home"]["source_label"], "本届世界杯1场 + 世界杯前3场正式赛均值")
        self.assertEqual(form_context["away"]["source_label"], "本届世界杯1场 + 世界杯前3场正式赛均值")
        self.assertEqual(form_context["home"]["sample_matches"], 4)
        self.assertEqual(form_context["home"]["world_cup_sample_matches"], 1)
        self.assertEqual(form_context["home"]["pre_world_cup_sample_matches"], 3)
        self.assertEqual(form_context["home"]["prop_sample_policy"], "official_mean")
        self.assertGreater(form_context["away"]["score"], form_context["home"]["score"])
        self.assertEqual(form_context["home"]["corners_for"], 4.5)
        self.assertEqual(form_context["home"]["yellow_cards_for"], 1.0)

    def test_review_adjustment_uses_only_current_world_cup_after_three_team_matches(self):
        matches = [
            {
                "id": 201,
                "home_team": "Argentina",
                "away_team": "Chile",
                "competition": "World Cup Qualifying",
                "is_official": True,
                "status": "completed",
                "home_score": 3,
                "away_score": 0,
                "match_date": "2026-03-20T04:00:00+08:00",
                "report": {"stats": {"shots_home": 12, "shots_away": 5, "shots_on_target_home": 5, "shots_on_target_away": 1, "corners_home": 7, "corners_away": 2, "yellow_cards_home": 8, "yellow_cards_away": 1}},
            },
            {
                "id": 202,
                "home_team": "Peru",
                "away_team": "Argentina",
                "competition": "World Cup Qualifying",
                "is_official": True,
                "status": "completed",
                "home_score": 0,
                "away_score": 2,
                "match_date": "2026-03-24T04:00:00+08:00",
                "report": {"stats": {"shots_home": 6, "shots_away": 13, "shots_on_target_home": 2, "shots_on_target_away": 6, "corners_home": 3, "corners_away": 8, "yellow_cards_home": 2, "yellow_cards_away": 8}},
            },
            {
                "id": 203,
                "home_team": "Argentina",
                "away_team": "Uruguay",
                "competition": "World Cup Qualifying",
                "is_official": True,
                "status": "completed",
                "home_score": 1,
                "away_score": 1,
                "match_date": "2026-06-02T04:00:00+08:00",
                "report": {"stats": {"shots_home": 10, "shots_away": 9, "shots_on_target_home": 4, "shots_on_target_away": 4, "corners_home": 6, "corners_away": 4, "yellow_cards_home": 8, "yellow_cards_away": 3}},
            },
            {
                "id": 210,
                "home_team": "Argentina",
                "away_team": "Algeria",
                "group": "J",
                "round": 1,
                "status": "completed",
                "home_score": 3,
                "away_score": 0,
                "match_date": "2026-06-13T04:00:00+08:00",
                "report": {"stats": {"shots_home": 14, "shots_away": 5, "shots_on_target_home": 7, "shots_on_target_away": 1, "corners_home": 5, "corners_away": 2, "yellow_cards_home": 0, "yellow_cards_away": 2}},
            },
            {
                "id": 211,
                "home_team": "Austria",
                "away_team": "Argentina",
                "group": "J",
                "round": 2,
                "status": "completed",
                "home_score": 0,
                "away_score": 2,
                "match_date": "2026-06-18T04:00:00+08:00",
                "report": {"stats": {"shots_home": 6, "shots_away": 12, "shots_on_target_home": 2, "shots_on_target_away": 5, "corners_home": 3, "corners_away": 4, "yellow_cards_home": 2, "yellow_cards_away": 2}},
            },
            {
                "id": 212,
                "home_team": "Argentina",
                "away_team": "Mexico",
                "group": "J",
                "round": 3,
                "status": "completed",
                "home_score": 1,
                "away_score": 1,
                "match_date": "2026-06-23T04:00:00+08:00",
                "report": {"stats": {"shots_home": 11, "shots_away": 8, "shots_on_target_home": 4, "shots_on_target_away": 3, "corners_home": 4, "corners_away": 3, "yellow_cards_home": 4, "yellow_cards_away": 3}},
            },
        ]
        future_match = {
            "id": 289,
            "home_team": "Argentina",
            "away_team": "Morocco",
            "stage": "round_of_32",
            "status": "upcoming",
            "match_date": "2026-06-28T04:00:00+08:00",
        }

        adjustment = build_review_adjustment(future_match, matches)
        argentina_context = adjustment["review_context"]["form_context"]["home"]
        rendered = "\n".join(
            adjustment["reasons"]
            + adjustment["review_context"]["team_review_notes"]
            + [adjustment["review_context"]["summary"]]
        )

        self.assertEqual(adjustment["review_context"]["mode"], "knockout_group_stage_review")
        self.assertIn("小组赛全阶段", rendered)
        self.assertNotIn("首轮状态校准", rendered)
        self.assertNotIn("小组前两轮", rendered)
        self.assertEqual(argentina_context["source_label"], "本届世界杯3场正式赛均值")
        self.assertEqual(argentina_context["sample_matches"], 3)
        self.assertEqual(argentina_context["world_cup_sample_matches"], 3)
        self.assertEqual(argentina_context["pre_world_cup_sample_matches"], 0)
        self.assertEqual(argentina_context["yellow_cards_for"], 2.0)

    def test_review_adjustment_provides_backtest_fallback_when_team_samples_missing(self):
        matches = [
            {
                "id": 1,
                "home_team": "Mexico",
                "away_team": "South Africa",
                "group": "A",
                "round": 1,
                "status": "completed",
                "home_score": 2,
                "away_score": 0,
                "match_date": "2026-06-12T03:00:00+08:00",
                "venue": "Azteca",
            },
        ]
        future_match = {
            "id": 25,
            "home_team": "Brazil",
            "away_team": "Haiti",
            "group": "C",
            "round": 2,
            "status": "upcoming",
            "match_date": "2026-06-18T09:00:00+08:00",
            "venue": "MetLife",
        }

        adjustment = build_review_adjustment(future_match, matches)

        self.assertFalse(adjustment["applied"])
        self.assertEqual(adjustment["review_context"]["mode"], "simulated_backtest_review")
        self.assertTrue(any("回测兜底" in note for note in adjustment["review_context"]["fallback_notes"]))


if __name__ == "__main__":
    unittest.main()
