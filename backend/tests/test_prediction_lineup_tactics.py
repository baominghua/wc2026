import sys
import unittest
from pathlib import Path
from unittest.mock import patch


BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from services.prediction_model import predict_match
from services.review_engine import build_review_adjustment
from services.team_squads import get_team_squad


class PredictionLineupTacticsTests(unittest.TestCase):
    def test_current_match_lineups_override_static_tactical_candidates(self):
        home_starters = [f"NED Starter {index}" for index in range(1, 12)]
        away_starters = [f"SWE Starter {index}" for index in range(1, 12)]
        match_context = {
            "id": 901,
            "home_team": "Netherlands",
            "away_team": "Sweden",
            "round": 2,
            "_live_source": "official_match_centre",
            "report": {
                "lineups": [
                    {
                        "team": "Netherlands",
                        "formation": "4-3-3",
                        "starters": home_starters,
                        "substitutes": ["NED Sub 1", "NED Sub 2"],
                    },
                    {
                        "team": "Sweden",
                        "formation": "5-4-1",
                        "starters": away_starters,
                        "substitutes": ["SWE Sub 1", "SWE Sub 2"],
                    },
                ]
            },
        }

        with patch.dict("os.environ", {"ODDS_MARKET_ENABLED": "false"}, clear=False):
            result = predict_match(
                "Netherlands",
                "Sweden",
                match_round=2,
                match_context=match_context,
            )

        self.assertEqual(result["tactical_matchup"]["home_formation"], "4-3-3")
        self.assertEqual(result["tactical_matchup"]["away_formation"], "5-4-1")
        self.assertEqual(result["lineup_prediction"][0]["starters"], home_starters)
        self.assertEqual(result["lineup_prediction"][1]["starters"], away_starters)
        self.assertEqual(result["tactical_analysis"][0]["source"], "current_match_lineup")
        self.assertGreaterEqual(result["lineup_prediction"][0]["confidence"], 0.82)
        self.assertTrue(any("官方/赛前首发" in factor for factor in result["factors"]))

    def test_api_football_startxi_lineups_feed_current_tactical_evidence(self):
        starters = [{"name": f"NED API {index}", "position": "MF"} for index in range(1, 12)]
        match_context = {
            "id": 902,
            "home_team": "Netherlands",
            "away_team": "Sweden",
            "round": 2,
            "report": {
                "lineups": [
                    {"team": "Netherlands", "formation": "4-2-3-1", "startXI": starters},
                    {"team": "Sweden", "formation": "4-4-2", "startXI": [{"name": f"SWE API {index}"} for index in range(1, 12)]},
                ]
            },
        }

        with patch.dict("os.environ", {"ODDS_MARKET_ENABLED": "false"}, clear=False):
            result = predict_match("Netherlands", "Sweden", match_round=2, match_context=match_context)

        self.assertEqual(result["lineup_prediction"][0]["formation"], "4-2-3-1")
        self.assertEqual(result["lineup_prediction"][0]["starters"][0], "NED API 1")
        self.assertEqual(result["tactical_analysis"][0]["source"], "current_match_lineup")

    def test_review_engine_exposes_recent_completed_lineup_sample(self):
        completed = [
            {
                "id": 12,
                "home_team": "Netherlands",
                "away_team": "Japan",
                "home_score": 2,
                "away_score": 1,
                "status": "completed",
                "round": 1,
                "match_date": "2026-06-15T20:00:00+00:00",
                "report": {
                    "lineups": [
                        {
                            "team": "Netherlands",
                            "formation": "4-4-2",
                            "starters": [f"NED R1 {index}" for index in range(1, 12)],
                        }
                    ],
                    "stats": {
                        "shots_home": 15,
                        "shots_away": 8,
                        "shots_on_target_home": 7,
                        "shots_on_target_away": 3,
                        "corners_home": 6,
                        "corners_away": 2,
                        "yellow_cards_home": 1,
                        "yellow_cards_away": 3,
                    },
                },
            }
        ]
        current = {
            "id": 13,
            "home_team": "Netherlands",
            "away_team": "Sweden",
            "round": 2,
            "group": "G",
            "match_date": "2026-06-20T20:00:00+00:00",
        }

        adjustment = build_review_adjustment(current, [*completed, current])
        home_context = adjustment["review_context"]["form_context"]["home"]

        self.assertEqual(home_context["latest_formation"], "4-4-2")
        self.assertEqual(home_context["latest_starters"][0], "NED R1 1")
        self.assertEqual(home_context["lineup_source"], "current_world_cup_official_matches")

    def test_recent_completed_lineup_sample_updates_tactical_matchup_when_no_current_lineup(self):
        review_adjustment = {
            "applied": True,
            "home_attack_delta": 0.0,
            "away_attack_delta": 0.0,
            "draw_probability_delta": 0.0,
            "reasons": ["Netherlands changed shape in the opening match."],
            "review_context": {
                "form_context": {
                    "home": {
                        "team": "Netherlands",
                        "score": 7.8,
                        "source_label": "本届世界杯最近1场正式赛",
                        "latest_formation": "4-4-2",
                        "latest_starters": [f"NED R1 {index}" for index in range(1, 12)],
                        "lineup_source": "current_world_cup_official_matches",
                        "note": "荷兰最近1场正式赛使用4-4-2并提高双前锋反击占比",
                    },
                    "away": {
                        "team": "Sweden",
                        "score": 8.9,
                        "source_label": "本届世界杯最近1场正式赛",
                    },
                }
            },
        }

        with patch.dict("os.environ", {"ODDS_MARKET_ENABLED": "false"}, clear=False):
            result = predict_match(
                "Netherlands",
                "Sweden",
                match_round=2,
                review_adjustment=review_adjustment,
            )

        self.assertEqual(result["tactical_matchup"]["home_formation"], "4-4-2")
        self.assertEqual(result["lineup_prediction"][0]["formation"], "4-4-2")
        self.assertEqual(result["lineup_prediction"][0]["starters"][0], "NED R1 1")
        self.assertEqual(result["tactical_analysis"][0]["source"], "recent_world_cup_lineup")
        self.assertTrue(any("最近正式赛实际阵型" in factor for factor in result["factors"]))

    def test_official_26_squad_replaces_stale_static_candidates(self):
        squad = get_team_squad("FRA")
        self.assertIsNotNone(squad)
        self.assertEqual(squad["player_count"], 26)

        with patch.dict("os.environ", {"ODDS_MARKET_ENABLED": "false"}, clear=False):
            result = predict_match("France", "Iraq", match_round=1)

        lineup = result["lineup_prediction"][0]
        roster_names = {player["name"] for player in squad["players"]}
        predicted_names = set(lineup["starters"] + lineup["bench_options"])
        stale_names = {"Griezmann", "Giroud", "Antoine Griezmann", "Olivier Giroud", "格列兹曼", "吉鲁"}

        self.assertEqual(lineup["evidence_source"], "official_26_squad_candidate_pool")
        self.assertTrue(set(lineup["starters"]).issubset(roster_names))
        self.assertFalse(predicted_names & stale_names)
        self.assertFalse({"Griezmann", "Giroud"} & {player["name"] for player in result["key_players"]})


if __name__ == "__main__":
    unittest.main()
