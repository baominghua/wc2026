import sys
import unittest
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from services.espn_scoreboard import normalise_espn_scoreboard


class EspnScoreboardTests(unittest.TestCase):
    def test_normalise_completed_match_with_score_goals_cards_and_stats(self):
        raw = {
            "events": [
                {
                    "id": "760419",
                    "date": "2026-06-13T22:00Z",
                    "competitions": [
                        {
                            "date": "2026-06-13T22:00Z",
                            "attendance": 80663,
                            "altGameNote": "FIFA World Cup, Group C",
                            "status": {
                                "type": {
                                    "state": "post",
                                    "completed": True,
                                    "description": "Full Time",
                                }
                            },
                            "venue": {
                                "fullName": "MetLife Stadium",
                                "address": {"city": "East Rutherford", "country": "USA"},
                            },
                            "competitors": [
                                {
                                    "homeAway": "home",
                                    "score": "1",
                                    "team": {
                                        "id": "205",
                                        "abbreviation": "BRA",
                                        "displayName": "Brazil",
                                    },
                                    "statistics": [
                                        {"name": "possessionPct", "displayValue": "51.4"},
                                        {"name": "totalShots", "displayValue": "12"},
                                        {"name": "shotsOnTarget", "displayValue": "5"},
                                        {"name": "wonCorners", "displayValue": "6"},
                                        {"name": "foulsCommitted", "displayValue": "16"},
                                    ],
                                },
                                {
                                    "homeAway": "away",
                                    "score": "1",
                                    "team": {
                                        "id": "2869",
                                        "abbreviation": "MAR",
                                        "displayName": "Morocco",
                                    },
                                    "statistics": [
                                        {"name": "possessionPct", "displayValue": "48.6"},
                                        {"name": "totalShots", "displayValue": "14"},
                                        {"name": "shotsOnTarget", "displayValue": "3"},
                                        {"name": "wonCorners", "displayValue": "2"},
                                        {"name": "foulsCommitted", "displayValue": "14"},
                                    ],
                                },
                            ],
                            "details": [
                                {
                                    "type": {"text": "Goal"},
                                    "clock": {"displayValue": "21'"},
                                    "team": {"id": "2869"},
                                    "scoringPlay": True,
                                    "penaltyKick": False,
                                    "ownGoal": False,
                                    "athletesInvolved": [
                                        {"displayName": "Ismael Saibari"}
                                    ],
                                },
                                {
                                    "type": {"text": "Yellow Card"},
                                    "clock": {"displayValue": "37'"},
                                    "team": {"id": "205"},
                                    "yellowCard": True,
                                    "athletesInvolved": [{"displayName": "Casemiro"}],
                                },
                            ],
                        }
                    ],
                }
            ]
        }

        feed = normalise_espn_scoreboard(raw, fetched_at="2026-06-15T00:00:00+08:00")

        self.assertEqual(feed["source"], "espn_scoreboard")
        self.assertEqual(len(feed["matches"]), 1)
        match = feed["matches"][0]
        self.assertEqual(match["id"], 760419)
        self.assertEqual(match["home_team"], "巴西")
        self.assertEqual(match["away_team"], "摩洛哥")
        self.assertEqual(match["status"], "completed")
        self.assertEqual(match["home_score"], 1)
        self.assertEqual(match["away_score"], 1)
        self.assertEqual(match["group"], "C")
        self.assertEqual(match["match_date"], "2026-06-14T06:00:00+08:00")
        self.assertEqual(match["report"]["attendance"], 80663)
        self.assertEqual(match["report"]["stats"]["shots_home"], 12)
        self.assertEqual(match["report"]["stats"]["shots_away"], 14)
        self.assertEqual(match["report"]["stats"]["yellow_cards_home"], 1)
        self.assertEqual(match["report"]["goals"][0]["player"], "Ismael Saibari")

    def test_normalise_summary_rosters_as_lineups(self):
        def player(name, place, starter=True):
            return {
                "starter": starter,
                "active": True,
                "formationPlace": place,
                "athlete": {"displayName": name},
            }

        raw = {
            "events": [
                {
                    "id": "760460",
                    "date": "2026-06-23T23:00Z",
                    "competitions": [
                        {
                            "date": "2026-06-23T23:00Z",
                            "status": {"type": {"state": "post", "completed": True}},
                            "competitors": [
                                {
                                    "homeAway": "home",
                                    "score": "0",
                                    "team": {"id": "304", "abbreviation": "PAN", "displayName": "Panama"},
                                },
                                {
                                    "homeAway": "away",
                                    "score": "1",
                                    "team": {"id": "477", "abbreviation": "CRO", "displayName": "Croatia"},
                                },
                            ],
                        }
                    ],
                }
            ]
        }
        summary = {
            "rosters": [
                {
                    "homeAway": "home",
                    "formation": "5-4-1",
                    "team": {"id": "304", "abbreviation": "PAN", "displayName": "Panama"},
                    "roster": [player(f"Panama Starter {index}", index) for index in range(1, 12)]
                    + [player("Panama Bench", 0, starter=False)],
                },
                {
                    "homeAway": "away",
                    "formation": "4-3-3",
                    "team": {"id": "477", "abbreviation": "CRO", "displayName": "Croatia"},
                    "roster": [player(f"Croatia Starter {index}", index) for index in range(1, 12)],
                },
            ]
        }

        feed = normalise_espn_scoreboard(
            raw,
            fetched_at="2026-06-24T08:00:00+08:00",
            summary_by_event_id={"760460": summary},
        )

        match = feed["matches"][0]
        self.assertEqual(match["home_formation"], "5-4-1")
        self.assertEqual(match["away_formation"], "4-3-3")
        self.assertEqual(len(match["report"]["lineups"]), 2)
        self.assertEqual(len(match["report"]["lineups"][0]["starters"]), 11)
        self.assertEqual(match["report"]["lineups"][0]["starters"][0], "Panama Starter 1")
        self.assertEqual(match["report"]["lineups"][0]["substitutes"], ["Panama Bench"])


if __name__ == "__main__":
    unittest.main()
