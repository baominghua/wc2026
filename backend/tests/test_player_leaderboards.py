import sys
import unittest
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from services.player_leaderboards import build_player_leaderboards


class PlayerLeaderboardTests(unittest.TestCase):
    def test_builds_live_scorer_and_assist_boards_from_completed_match_reports(self):
        matches = [
            {
                "id": 1,
                "status": "completed",
                "report": {
                    "goals": [
                        {
                            "minute": 12,
                            "team": "USA",
                            "player": "Folarin Balogun",
                            "assist": "Christian Pulisic",
                            "type": "goal",
                        },
                        {
                            "minute": 30,
                            "team": "USA",
                            "player": "Own Goal Defender",
                            "type": "own_goal",
                        },
                    ],
                    "cards": [
                        {
                            "minute": 70,
                            "team": "USA",
                            "player": "Tyler Adams",
                            "type": "yellow_card",
                        }
                    ],
                },
            },
            {
                "id": 2,
                "status": "completed",
                "report": {
                    "goals": [
                        {
                            "minute": 88,
                            "team": "USA",
                            "player": "Folarin Balogun",
                            "assist": "Giovanni Reyna",
                            "type": "goal",
                        },
                        {
                            "minute": 90,
                            "team": "Morocco",
                            "player": "Ismael Saibari",
                            "type": "penalty",
                        },
                    ]
                },
            },
        ]

        result = build_player_leaderboards(matches)

        self.assertEqual(result["summary"]["completed_match_count"], 2)
        self.assertEqual(result["summary"]["goal_event_count"], 3)
        self.assertEqual(result["summary"]["assist_event_count"], 2)
        self.assertEqual(result["scorers"][0]["name"], "Folarin Balogun")
        self.assertEqual(result["scorers"][0]["goals"], 2)
        self.assertNotIn("Own Goal Defender", [player["name"] for player in result["scorers"]])
        self.assertEqual(result["assists"][0]["name"], "Christian Pulisic")
        self.assertEqual(result["assists"][0]["assists"], 1)
        self.assertEqual(result["players_by_name"]["Tyler Adams"]["yellowCards"], 1)

    def test_deduplicates_repeated_events_from_multiple_live_sources(self):
        matches = [
            {
                "id": 12,
                "status": "completed",
                "report": {
                    "goals": [
                        {"minute": 7, "team": "瑞典", "player": "Yasin Ayari", "type": "goal"},
                        {"minute": 7, "team": "瑞典", "player": "Yasin Ayari", "type": "goal"},
                        {
                            "minute": 84,
                            "team": "瑞典",
                            "player": "Mattias Svanberg",
                            "assist": "Alexander Isak",
                            "type": "goal",
                        },
                        {
                            "minute": 84,
                            "team": "瑞典",
                            "player": "Mattias Svanberg",
                            "assist": "Alexander Isak",
                            "type": "goal",
                        },
                    ],
                    "cards": [
                        {"minute": 70, "team": "瑞典", "player": "Alexander Isak", "type": "yellow_card"},
                        {"minute": 70, "team": "瑞典", "player": "Alexander Isak", "type": "yellow_card"},
                    ],
                },
            }
        ]

        result = build_player_leaderboards(matches)

        self.assertEqual(result["summary"]["goal_event_count"], 2)
        self.assertEqual(result["summary"]["assist_event_count"], 1)
        self.assertEqual(result["players_by_name"]["Yasin Ayari"]["goals"], 1)
        self.assertEqual(result["players_by_name"]["Alexander Isak"]["assists"], 1)
        self.assertEqual(result["players_by_name"]["Alexander Isak"]["yellowCards"], 1)


if __name__ == "__main__":
    unittest.main()
