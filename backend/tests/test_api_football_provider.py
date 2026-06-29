import sys
import unittest
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from services.api_football import normalise_api_football_leaderboards


class ApiFootballProviderTests(unittest.TestCase):
    def test_normalises_top_scorers_and_assists(self):
        payloads = {
            "topscorers": {
                "response": [
                    {
                        "player": {"name": "Folarin Balogun"},
                        "statistics": [
                            {
                                "team": {"name": "USA"},
                                "games": {"appearences": 1, "minutes": 90, "position": "Attacker"},
                                "goals": {"total": 2, "assists": 0},
                                "cards": {"yellow": 0, "red": 0},
                            }
                        ],
                    }
                ]
            },
            "topassists": {
                "response": [
                    {
                        "player": {"name": "Alexander Isak"},
                        "statistics": [
                            {
                                "team": {"name": "Sweden"},
                                "games": {"appearences": 1, "minutes": 90, "position": "Attacker"},
                                "goals": {"total": 1, "assists": 2},
                                "cards": {"yellow": 1, "red": 0},
                            }
                        ],
                    }
                ]
            },
            "topyellowcards": {"response": []},
            "topredcards": {"response": []},
        }

        result = normalise_api_football_leaderboards(payloads, fetched_at="2026-06-16T12:00:00+08:00")

        self.assertEqual(result["source"], "api_football")
        self.assertEqual(result["summary"]["assist_event_count"], 2)
        self.assertEqual(result["summary"]["goal_event_count"], 3)
        self.assertEqual(result["scorers"][0]["name"], "Folarin Balogun")
        self.assertEqual(result["scorers"][0]["goals"], 2)
        self.assertEqual(result["assists"][0]["name"], "Alexander Isak")
        self.assertEqual(result["assists"][0]["assists"], 2)
        self.assertEqual(result["players_by_name"]["Alexander Isak"]["yellowCards"], 1)


if __name__ == "__main__":
    unittest.main()
