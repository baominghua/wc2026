import sys
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch


BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from services import espn_scoreboard
from services.match_stage import normalize_match_stage


class EspnScoreboardWindowTests(unittest.TestCase):
    def test_default_scoreboard_window_covers_tournament_to_date(self):
        with patch.dict(
            "os.environ",
            {
                "ESPN_SCOREBOARD_START_DATE": "20260611",
                "ESPN_SCOREBOARD_DAYS_FORWARD": "2",
            },
            clear=True,
        ), patch.object(
            espn_scoreboard,
            "_now",
            return_value=datetime(2026, 6, 18, 12, tzinfo=espn_scoreboard.SHANGHAI_TZ),
        ):
            dates = espn_scoreboard._date_values()

        self.assertEqual(dates[0], "20260611")
        self.assertIn("20260612", dates)
        self.assertIn("20260613", dates)
        self.assertIn("20260620", dates)

    def test_default_scoreboard_window_reaches_announced_knockout_dates(self):
        with patch.dict(
            "os.environ",
            {
                "ESPN_SCOREBOARD_START_DATE": "20260611",
            },
            clear=True,
        ), patch.object(
            espn_scoreboard,
            "_now",
            return_value=datetime(2026, 6, 30, 12, tzinfo=espn_scoreboard.SHANGHAI_TZ),
        ):
            dates = espn_scoreboard._date_values()

        self.assertIn("20260704", dates)
        self.assertIn("20260707", dates)
        self.assertIn("20260714", dates)

    def test_normalise_scoreboard_uses_official_knockout_stage_and_placeholders(self):
        raw_feed = {
            "events": [
                {
                    "id": "760503",
                    "date": "2026-07-04T21:00Z",
                    "name": "Round of 32 5 Winner at Paraguay",
                    "season": {"slug": "round-of-16"},
                    "competitions": [
                        {
                            "date": "2026-07-04T21:00Z",
                            "altGameNote": "FIFA World Cup, Round of 16",
                            "status": {"type": {"state": "pre", "completed": False}},
                            "competitors": [
                                {
                                    "homeAway": "home",
                                    "score": "0",
                                    "team": {"id": "1", "abbreviation": "PAR", "displayName": "Paraguay"},
                                },
                                {
                                    "homeAway": "away",
                                    "score": "0",
                                    "team": {
                                        "id": "2",
                                        "abbreviation": "RD32",
                                        "displayName": "Round of 32 5 Winner",
                                    },
                                },
                            ],
                        }
                    ],
                }
            ]
        }

        feed = espn_scoreboard.normalise_espn_scoreboard(raw_feed, fetched_at="2026-06-30T12:00:00+08:00")
        match = normalize_match_stage(feed["matches"][0])

        self.assertEqual(match["stage"], "Round of 16")
        self.assertIsNone(match["group"])
        self.assertIsNone(match["round"])
        self.assertEqual(match["away_team"], "Round of 32 5 Winner")
        self.assertEqual(match["fixture_status"], "placeholder")

    def test_fetch_scoreboard_combines_multiple_dates(self):
        def fake_read_json_url(url):
            event_id = "1" if "20260611" in url else "2"
            return {
                "events": [
                    {
                        "id": event_id,
                        "date": "2026-06-11T20:00Z",
                        "competitions": [
                            {
                                "date": "2026-06-11T20:00Z",
                                "status": {"type": {"state": "pre", "completed": False}},
                                "competitors": [
                                    {
                                        "homeAway": "home",
                                        "score": "0",
                                        "team": {"id": "1", "abbreviation": "ARG", "displayName": "Argentina"},
                                    },
                                    {
                                        "homeAway": "away",
                                        "score": "0",
                                        "team": {"id": "2", "abbreviation": "ALG", "displayName": "Algeria"},
                                    },
                                ],
                            }
                        ],
                    }
                ]
            }

        with patch.dict(
            "os.environ",
            {
                "ESPN_SCOREBOARD_DATES": "20260611,20260612",
                "ESPN_SCOREBOARD_MAX_WORKERS": "2",
            },
            clear=True,
        ), patch.object(espn_scoreboard, "_read_json_url", side_effect=fake_read_json_url):
            feed = espn_scoreboard.fetch_espn_scoreboard_feed()

        self.assertEqual(feed["source"], "espn_scoreboard")
        self.assertEqual({match["espn_event_id"] for match in feed["matches"]}, {"1", "2"})

    def test_fetch_scoreboard_adds_recent_summary_lineups(self):
        def player(name, place):
            return {
                "starter": True,
                "active": True,
                "formationPlace": place,
                "athlete": {"displayName": name},
            }

        def fake_read_json_url(url):
            if "summary" in url:
                return {
                    "rosters": [
                        {
                            "homeAway": "home",
                            "formation": "5-4-1",
                            "team": {"id": "1", "abbreviation": "PAN", "displayName": "Panama"},
                            "roster": [player(f"Panama Starter {index}", index) for index in range(1, 12)],
                        },
                        {
                            "homeAway": "away",
                            "formation": "4-3-3",
                            "team": {"id": "2", "abbreviation": "CRO", "displayName": "Croatia"},
                            "roster": [player(f"Croatia Starter {index}", index) for index in range(1, 12)],
                        },
                    ]
                }
            return {
                "events": [
                    {
                        "id": "760460",
                        "date": "2026-06-23T23:00Z",
                        "competitions": [
                            {
                                "date": "2026-06-23T23:00Z",
                                "recent": True,
                                "status": {"type": {"state": "post", "completed": True}},
                                "competitors": [
                                    {
                                        "homeAway": "home",
                                        "score": "0",
                                        "team": {"id": "1", "abbreviation": "PAN", "displayName": "Panama"},
                                    },
                                    {
                                        "homeAway": "away",
                                        "score": "1",
                                        "team": {"id": "2", "abbreviation": "CRO", "displayName": "Croatia"},
                                    },
                                ],
                            }
                        ],
                    }
                ]
            }

        with patch.dict(
            "os.environ",
            {
                "ESPN_SCOREBOARD_DATES": "20260624",
                "ESPN_SCOREBOARD_MAX_WORKERS": "1",
                "ESPN_SUMMARY_MAX_WORKERS": "1",
            },
            clear=True,
        ), patch.object(espn_scoreboard, "_read_json_url", side_effect=fake_read_json_url):
            feed = espn_scoreboard.fetch_espn_scoreboard_feed()

        match = feed["matches"][0]
        self.assertEqual(match["home_formation"], "5-4-1")
        self.assertEqual(match["away_formation"], "4-3-3")
        self.assertEqual(len(match["report"]["lineups"][0]["starters"]), 11)


if __name__ == "__main__":
    unittest.main()
