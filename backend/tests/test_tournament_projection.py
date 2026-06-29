import unittest
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from services.tournament_projection import (
    build_group_standings,
    build_round_of_32,
    resolve_third_place_assignments,
    simulate_knockout,
)


def make_match(match_id, group, home, away, status="upcoming", home_score=None, away_score=None):
    return {
        "id": match_id,
        "group": group,
        "round": 1,
        "home_team": home,
        "away_team": away,
        "venue": "Test Stadium",
        "status": status,
        "home_score": home_score,
        "away_score": away_score,
    }


class TournamentProjectionTests(unittest.TestCase):
    def test_group_standings_mix_completed_scores_and_predictions(self):
        matches = [
            make_match(1, "A", "A队", "B队", "completed", 1, 0),
            make_match(2, "A", "A队", "C队"),
            make_match(3, "A", "A队", "D队"),
            make_match(4, "A", "B队", "C队"),
            make_match(5, "A", "B队", "D队"),
            make_match(6, "A", "C队", "D队"),
        ]
        predicted_scores = {
            2: "0-2",
            3: "2-0",
            4: "1-1",
            5: "1-0",
            6: "0-0",
        }

        def predictor(match, is_knockout=False, stage=None):
            return {
                "predicted_score": predicted_scores[match["id"]],
                "home_win_probability": 0.4,
                "draw_probability": 0.2,
                "away_win_probability": 0.4,
                "confidence": 0.5,
            }

        groups, projected_matches = build_group_standings(matches, predictor=predictor)

        self.assertEqual([row["team"] for row in groups["A"]], ["A队", "C队", "B队", "D队"])
        self.assertEqual(groups["A"][0]["points"], 6)
        self.assertEqual(groups["A"][1]["points"], 5)
        self.assertEqual(projected_matches[0]["score_source"], "actual")
        self.assertEqual(projected_matches[1]["score_source"], "model")
        self.assertEqual(projected_matches[1]["home_score"], 0)
        self.assertEqual(projected_matches[1]["away_score"], 2)

    def test_third_place_option_476_routes_ab_c_d_e_g_i_j(self):
        assignments = resolve_third_place_assignments(["A", "B", "C", "D", "E", "G", "I", "J"])

        self.assertEqual(assignments["option"], 476)
        self.assertEqual(
            assignments["slots"],
            {
                "1A": "E",
                "1B": "G",
                "1D": "B",
                "1E": "C",
                "1G": "A",
                "1I": "D",
                "1K": "I",
                "1L": "J",
            },
        )

    def test_round_of_32_uses_official_2026_slots(self):
        groups = {}
        for group in "ABCDEFGHIJKL":
            groups[group] = [
                {"team": f"{group}1", "group": group, "rank": 1},
                {"team": f"{group}2", "group": group, "rank": 2},
                {"team": f"{group}3", "group": group, "rank": 3},
                {"team": f"{group}4", "group": group, "rank": 4},
            ]
        best_thirds = [groups[group][2] for group in ["A", "B", "C", "D", "E", "G", "I", "J"]]

        bracket = build_round_of_32(groups, best_thirds)
        by_id = {match["id"]: match for match in bracket}

        self.assertEqual((by_id[73]["home_team"], by_id[73]["away_team"]), ("A2", "B2"))
        self.assertEqual((by_id[74]["home_team"], by_id[74]["away_team"]), ("E1", "C3"))
        self.assertEqual((by_id[79]["home_team"], by_id[79]["away_team"]), ("A1", "E3"))
        self.assertEqual((by_id[81]["home_team"], by_id[81]["away_team"]), ("D1", "B3"))
        self.assertEqual((by_id[85]["home_team"], by_id[85]["away_team"]), ("B1", "G3"))
        self.assertEqual((by_id[87]["home_team"], by_id[87]["away_team"]), ("K1", "I3"))

    def test_simulate_knockout_generates_champion(self):
        round_of_32 = [
            {"id": match_id, "stage": "Round of 32", "home_team": f"H{match_id}", "away_team": f"A{match_id}"}
            for match_id in range(73, 89)
        ]

        def predictor(match, is_knockout=False, stage=None):
            return {
                "predicted_score": "2-1",
                "home_win_probability": 0.62,
                "draw_probability": 0.0,
                "away_win_probability": 0.38,
                "confidence": 0.62,
                "penalty_probability": 0.12,
            }

        result = simulate_knockout(round_of_32, predictor=predictor)

        self.assertEqual(result["champion"], "H74")
        self.assertEqual(len(result["rounds"]["Round of 32"]), 16)
        self.assertEqual(len(result["rounds"]["Round of 16"]), 8)
        self.assertEqual(len(result["rounds"]["Quarter-final"]), 4)
        self.assertEqual(len(result["rounds"]["Semi-final"]), 2)
        self.assertEqual(len(result["rounds"]["Final"]), 1)

    def test_simulate_knockout_keeps_90_minute_draw_and_adds_decision_layer(self):
        round_of_32 = [
            {"id": match_id, "stage": "Round of 32", "home_team": f"H{match_id}", "away_team": f"A{match_id}"}
            for match_id in range(73, 89)
        ]

        def predictor(match, is_knockout=False, stage=None):
            if is_knockout:
                return {
                    "predicted_score": "2-1",
                    "home_win_probability": 0.55,
                    "draw_probability": 0.0,
                    "away_win_probability": 0.45,
                    "penalty_probability": 0.2,
                    "confidence": 0.58,
                    "factors": ["test knockout factor"],
                }
            return {
                "predicted_score": "1-1",
                "home_win_probability": 0.36,
                "draw_probability": 0.32,
                "away_win_probability": 0.32,
                "confidence": 0.52,
                "factors": ["test regulation factor"],
            }

        result = simulate_knockout(round_of_32, predictor=predictor)
        match = result["rounds"]["Round of 32"][0]

        self.assertEqual((match["regulation_home_score"], match["regulation_away_score"]), (1, 1))
        self.assertIn(match["decided_by"], {"extra_time", "penalties"})
        self.assertTrue(match["winner"])
        self.assertTrue(match["prediction_basis"])
        if match["decided_by"] == "penalties":
            self.assertEqual((match["home_score"], match["away_score"]), (1, 1))
            self.assertNotEqual(match["penalty_home_score"], match["penalty_away_score"])
        else:
            self.assertNotEqual(match["home_score"], match["away_score"])

    def test_simulate_knockout_carries_scheduled_context_for_later_rounds(self):
        round_of_32 = [
            {"id": match_id, "stage": "Round of 32", "home_team": f"H{match_id}", "away_team": f"A{match_id}"}
            for match_id in range(73, 89)
        ]
        schedule_by_id = {
            89: {
                "id": 89,
                "stage": "Round of 16",
                "match_date": "2026-07-09T03:00:00+08:00",
                "venue": "阿兹特克体育场，墨西哥城",
            },
            103: {
                "id": 103,
                "stage": "Third place",
                "match_date": "2026-07-20T07:00:00+08:00",
                "venue": "硬石体育场，迈阿密",
            },
        }

        def predictor(match, is_knockout=False, stage=None):
            return {
                "predicted_score": "2-1",
                "home_win_probability": 0.62,
                "draw_probability": 0.0,
                "away_win_probability": 0.38,
                "confidence": 0.62,
            }

        result = simulate_knockout(round_of_32, predictor=predictor, schedule_by_id=schedule_by_id)

        self.assertEqual(result["rounds"]["Round of 16"][0]["venue"], "阿兹特克体育场，墨西哥城")
        self.assertEqual(result["rounds"]["Round of 16"][0]["match_date"], "2026-07-09T03:00:00+08:00")
        self.assertEqual(result["rounds"]["Third place"][0]["venue"], "硬石体育场，迈阿密")


if __name__ == "__main__":
    unittest.main()
