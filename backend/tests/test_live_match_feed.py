import importlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from services import live_match_feed


class LiveMatchFeedTests(unittest.TestCase):
    def setUp(self):
        self._old_env = {
            "MATCH_FEED_PATH": os.environ.get("MATCH_FEED_PATH"),
            "MATCH_FEED_URL": os.environ.get("MATCH_FEED_URL"),
            "MATCH_RESULTS_BACKFILL_PATH": os.environ.get("MATCH_RESULTS_BACKFILL_PATH"),
            "MATCH_RESULTS_BACKFILL_URL": os.environ.get("MATCH_RESULTS_BACKFILL_URL"),
            "MATCH_SCHEDULE_PATH": os.environ.get("MATCH_SCHEDULE_PATH"),
            "ESPN_SCOREBOARD_ENABLED": os.environ.get("ESPN_SCOREBOARD_ENABLED"),
            "LOCAL_MATCH_FEED_ENABLED": os.environ.get("LOCAL_MATCH_FEED_ENABLED"),
            "API_FOOTBALL_ENABLED": os.environ.get("API_FOOTBALL_ENABLED"),
            "API_FOOTBALL_KEY": os.environ.get("API_FOOTBALL_KEY"),
        }
        os.environ.pop("MATCH_FEED_URL", None)
        os.environ.pop("MATCH_RESULTS_BACKFILL_URL", None)
        os.environ.pop("LOCAL_MATCH_FEED_ENABLED", None)
        os.environ["API_FOOTBALL_ENABLED"] = "false"
        os.environ.pop("API_FOOTBALL_KEY", None)
        os.environ["ESPN_SCOREBOARD_ENABLED"] = "false"

    def tearDown(self):
        for key, value in self._old_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        importlib.reload(live_match_feed)

    def test_local_file_feeds_are_ignored_unless_explicitly_enabled(self):
        with tempfile.TemporaryDirectory() as tmp:
            feed_path = Path(tmp) / "matches.live.json"
            feed_path.write_text(
                json.dumps(
                    {
                        "source": "manual_file_feed",
                        "last_updated": "2026-06-14T12:00:00+08:00",
                        "matches": [
                            {
                                "id": 99,
                                "home_team": "Manual Home",
                                "away_team": "Manual Away",
                                "match_date": "2026-06-14T03:00:00+08:00",
                                "status": "completed",
                                "home_score": 3,
                                "away_score": 2,
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            os.environ["MATCH_FEED_PATH"] = str(feed_path)
            os.environ["MATCH_RESULTS_BACKFILL_PATH"] = str(Path(tmp) / "missing.public-results.json")
            importlib.reload(live_match_feed)

            merged = live_match_feed.merge_live_matches([])
            status = live_match_feed.get_live_sync_status([])

        self.assertEqual(merged, [])
        self.assertEqual(status["status"], "not_configured")
        self.assertEqual(status["primary_match_count"], 0)

    def test_merge_includes_feed_only_matches(self):
        with tempfile.TemporaryDirectory() as tmp:
            feed_path = Path(tmp) / "matches.live.json"
            feed_path.write_text(
                json.dumps(
                    {
                        "source": "unit_test_feed",
                        "last_updated": "2026-06-14T12:00:00+08:00",
                        "matches": [
                            {
                                "id": 99,
                                "home_team": "测试主队",
                                "away_team": "测试客队",
                                "group": "Z",
                                "round": 1,
                                "match_date": "2026-06-14T03:00:00+08:00",
                                "venue": "测试球场",
                                "status": "completed",
                                "home_score": 3,
                                "away_score": 2,
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            os.environ["MATCH_FEED_PATH"] = str(feed_path)
            os.environ["MATCH_RESULTS_BACKFILL_PATH"] = str(Path(tmp) / "missing.public-results.json")
            os.environ["LOCAL_MATCH_FEED_ENABLED"] = "true"
            importlib.reload(live_match_feed)

            merged = live_match_feed.merge_live_matches(
                [
                    {
                        "id": 1,
                        "home_team": "基础主队",
                        "away_team": "基础客队",
                        "group": "A",
                        "round": 1,
                        "match_date": "2026-06-12T03:00:00+08:00",
                        "venue": "基础球场",
                        "status": "completed",
                        "home_score": 1,
                        "away_score": 0,
                    }
                ]
            )

        self.assertEqual([match["id"] for match in merged], [1, 99])
        feed_only = merged[1]
        self.assertEqual(feed_only["data_status"], "official_feed")
        self.assertEqual(feed_only["live_source"], "unit_test_feed")

    def test_groupless_resolved_fixture_after_group_stage_is_knockout(self):
        with tempfile.TemporaryDirectory() as tmp:
            feed_path = Path(tmp) / "matches.live.json"
            feed_path.write_text(
                json.dumps(
                    {
                        "source": "resolved_bracket_feed",
                        "last_updated": "2026-06-28T22:00:00+08:00",
                        "matches": [
                            {
                                "id": 901,
                                "home_team": "加拿大",
                                "away_team": "南非",
                                "group": None,
                                "round": None,
                                "match_date": "2026-06-29T09:00:00+08:00",
                                "venue": "BMO Field, Toronto",
                                "status": "upcoming",
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            os.environ["MATCH_FEED_PATH"] = str(feed_path)
            os.environ["MATCH_RESULTS_BACKFILL_PATH"] = str(Path(tmp) / "missing.public-results.json")
            os.environ["LOCAL_MATCH_FEED_ENABLED"] = "true"
            importlib.reload(live_match_feed)

            merged = live_match_feed.merge_live_matches([])

        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["home_team"], "加拿大")
        self.assertEqual(merged[0]["away_team"], "南非")
        self.assertIsNone(merged[0].get("group"))
        self.assertEqual(merged[0].get("stage"), "Round of 32")

    def test_confirmed_knockout_feed_does_not_cannibalize_unmatched_placeholder_slots(self):
        with tempfile.TemporaryDirectory() as tmp:
            feed_path = Path(tmp) / "matches.live.json"
            feed_path.write_text(
                json.dumps(
                    {
                        "source": "espn_scoreboard",
                        "last_updated": "2026-06-30T10:00:00+08:00",
                        "matches": [
                            {
                                "id": 760490,
                                "home_team": "Canada",
                                "away_team": "South Africa",
                                "group": None,
                                "round": None,
                                "match_date": "2026-07-01T01:00:00+08:00",
                                "venue": "BMO Field, Toronto",
                                "status": "upcoming",
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            os.environ["MATCH_FEED_PATH"] = str(feed_path)
            os.environ["MATCH_RESULTS_BACKFILL_PATH"] = str(Path(tmp) / "missing.public-results.json")
            os.environ["LOCAL_MATCH_FEED_ENABLED"] = "true"
            importlib.reload(live_match_feed)

            merged = live_match_feed.merge_live_matches(
                [
                    {
                        "id": 73,
                        "home_team": "A2",
                        "away_team": "B2",
                        "group": None,
                        "round": None,
                        "stage": "Round of 32",
                        "match_date": "2026-07-02T03:00:00+08:00",
                        "venue": "Original Slot",
                        "status": "upcoming",
                    },
                    {
                        "id": 74,
                        "home_team": "E1",
                        "away_team": "1E",
                        "group": None,
                        "round": None,
                        "stage": "Round of 32",
                        "match_date": "2026-07-02T07:00:00+08:00",
                        "venue": "Next Slot",
                        "status": "upcoming",
                    },
                ]
            )

        self.assertEqual(len(merged), 3)
        by_id = {match["id"]: match for match in merged}
        self.assertEqual(by_id[73]["home_team"], "A2")
        self.assertEqual(by_id[73]["away_team"], "B2")
        self.assertEqual(by_id[73]["match_date"], "2026-07-02T03:00:00+08:00")
        self.assertEqual(by_id[73]["fixture_status"], "placeholder")
        self.assertEqual(by_id[74]["fixture_status"], "placeholder")
        self.assertEqual(by_id[760490]["home_team"], "Canada")
        self.assertEqual(by_id[760490]["away_team"], "South Africa")
        self.assertEqual(by_id[760490]["fixture_status"], "confirmed")

    def test_confirmed_knockout_feed_hides_placeholders_on_same_stage_date_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            feed_path = Path(tmp) / "matches.live.json"
            feed_path.write_text(
                json.dumps(
                    {
                        "source": "espn_scoreboard",
                        "last_updated": "2026-06-30T10:00:00+08:00",
                        "matches": [
                            {
                                "id": 760497,
                                "home_team": "Spain",
                                "away_team": "Austria",
                                "group": None,
                                "round": None,
                                "match_date": "2026-07-03T03:00:00+08:00",
                                "venue": "SoFi Stadium",
                                "status": "upcoming",
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            os.environ["MATCH_FEED_PATH"] = str(feed_path)
            os.environ["MATCH_RESULTS_BACKFILL_PATH"] = str(Path(tmp) / "missing.public-results.json")
            os.environ["LOCAL_MATCH_FEED_ENABLED"] = "true"
            importlib.reload(live_match_feed)

            merged = live_match_feed.merge_live_matches(
                [
                    {
                        "id": 75,
                        "home_team": "F1",
                        "away_team": "C2",
                        "group": None,
                        "round": None,
                        "stage": "Round of 32",
                        "match_date": "2026-07-03T03:00:00+08:00",
                        "venue": "AT&T Stadium",
                        "status": "upcoming",
                    },
                    {
                        "id": 78,
                        "home_team": "E2",
                        "away_team": "I2",
                        "group": None,
                        "round": None,
                        "stage": "Round of 32",
                        "match_date": "2026-07-04T03:00:00+08:00",
                        "venue": "Hard Rock Stadium",
                        "status": "upcoming",
                    },
                ]
            )

        by_id = {match["id"]: match for match in merged}
        self.assertNotIn(75, by_id)
        self.assertIn(760497, by_id)
        self.assertEqual(by_id[760497]["fixture_status"], "confirmed")
        self.assertIn(78, by_id)
        self.assertEqual(by_id[78]["fixture_status"], "placeholder")

    def test_official_placeholder_from_feed_is_preserved_on_same_day_as_confirmed_match(self):
        with tempfile.TemporaryDirectory() as tmp:
            feed_path = Path(tmp) / "matches.live.json"
            feed_path.write_text(
                json.dumps(
                    {
                        "source": "espn_scoreboard",
                        "last_updated": "2026-06-30T10:00:00+08:00",
                        "matches": [
                            {
                                "id": 760502,
                                "home_team": "Canada",
                                "away_team": "Morocco",
                                "group": None,
                                "round": None,
                                "stage": "Round of 16",
                                "match_date": "2026-07-05T01:00:00+08:00",
                                "venue": "NRG Stadium",
                                "status": "upcoming",
                            },
                            {
                                "id": 760503,
                                "home_team": "Paraguay",
                                "away_team": "Round of 32 5 Winner",
                                "group": None,
                                "round": None,
                                "stage": "Round of 16",
                                "match_date": "2026-07-05T05:00:00+08:00",
                                "venue": "Lincoln Financial Field",
                                "status": "upcoming",
                            },
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            os.environ["MATCH_FEED_PATH"] = str(feed_path)
            os.environ["MATCH_RESULTS_BACKFILL_PATH"] = str(Path(tmp) / "missing.public-results.json")
            os.environ["LOCAL_MATCH_FEED_ENABLED"] = "true"
            importlib.reload(live_match_feed)

            merged = live_match_feed.merge_live_matches([])

        by_id = {match["id"]: match for match in merged}
        self.assertEqual(by_id[760502]["fixture_status"], "confirmed")
        self.assertEqual(by_id[760503]["fixture_status"], "placeholder")
        self.assertEqual(by_id[760503]["live_source"], "espn_scoreboard")

    def test_complete_official_knockout_stage_replaces_static_stage_templates(self):
        with tempfile.TemporaryDirectory() as tmp:
            feed_path = Path(tmp) / "matches.live.json"
            feed_path.write_text(
                json.dumps(
                    {
                        "source": "espn_scoreboard",
                        "last_updated": "2026-06-30T10:00:00+08:00",
                        "matches": [
                            {
                                "id": 9000 + index,
                                "home_team": f"Official Home {index}",
                                "away_team": f"Official Away {index}",
                                "group": None,
                                "round": None,
                                "stage": "Round of 32",
                                "match_date": f"2026-07-{1 + index // 3:02d}T03:00:00+08:00",
                                "venue": "Official Stadium",
                                "status": "upcoming",
                            }
                            for index in range(16)
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            os.environ["MATCH_FEED_PATH"] = str(feed_path)
            os.environ["MATCH_RESULTS_BACKFILL_PATH"] = str(Path(tmp) / "missing.public-results.json")
            os.environ["LOCAL_MATCH_FEED_ENABLED"] = "true"
            importlib.reload(live_match_feed)

            merged = live_match_feed.merge_live_matches(
                [
                    {
                        "id": 73,
                        "home_team": "A2",
                        "away_team": "B2",
                        "group": None,
                        "round": None,
                        "stage": "Round of 32",
                        "match_date": "2026-07-02T03:00:00+08:00",
                        "venue": "Template Stadium",
                        "status": "upcoming",
                    },
                    {
                        "id": 78,
                        "home_team": "E2",
                        "away_team": "I2",
                        "group": None,
                        "round": None,
                        "stage": "Round of 32",
                        "match_date": "2026-07-04T03:00:00+08:00",
                        "venue": "Template Stadium",
                        "status": "upcoming",
                    },
                ]
            )

        ids = {match["id"] for match in merged}
        self.assertEqual(len(merged), 16)
        self.assertNotIn(73, ids)
        self.assertNotIn(78, ids)
        self.assertIn(9000, ids)
        self.assertIn(9015, ids)

    def test_top_level_cards_are_preserved_in_report_when_merging_feed(self):
        with tempfile.TemporaryDirectory() as tmp:
            feed_path = Path(tmp) / "matches.live.json"
            feed_path.write_text(
                json.dumps(
                    {
                        "source": "unit_test_feed",
                        "last_updated": "2026-06-17T12:00:00+08:00",
                        "matches": [
                            {
                                "id": 31,
                                "home_team": "Argentina",
                                "away_team": "Jordan",
                                "match_date": "2026-06-17T10:00:00+08:00",
                                "status": "completed",
                                "home_score": 4,
                                "away_score": 0,
                                "cards": [
                                    {
                                        "minute": 38,
                                        "team": "Jordan",
                                        "player": "Ali Example",
                                        "type": "red_card",
                                    }
                                ],
                                "stats": {
                                    "red_cards_away": 1,
                                },
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            os.environ["MATCH_FEED_PATH"] = str(feed_path)
            os.environ["MATCH_RESULTS_BACKFILL_PATH"] = str(Path(tmp) / "missing.public-results.json")
            os.environ["LOCAL_MATCH_FEED_ENABLED"] = "true"
            importlib.reload(live_match_feed)

            merged = live_match_feed.merge_live_matches(
                [
                    {
                        "id": 31,
                        "home_team": "Argentina",
                        "away_team": "Jordan",
                        "match_date": "2026-06-17T10:00:00+08:00",
                        "status": "upcoming",
                    }
                ]
            )

        report = merged[0]["report"]
        self.assertEqual(report["cards"][0]["type"], "red_card")
        self.assertEqual(report["stats"]["red_cards_away"], 1)

    def test_backfill_feed_completes_missing_results_without_overriding_primary_feed(self):
        with tempfile.TemporaryDirectory() as tmp:
            primary_path = Path(tmp) / "matches.live.json"
            backfill_path = Path(tmp) / "matches.public-results.json"
            primary_path.write_text(
                json.dumps(
                    {
                        "source": "primary_feed",
                        "last_updated": "2026-06-14T12:00:00+08:00",
                        "matches": [
                            {
                                "id": 3,
                                "status": "completed",
                                "home_score": 2,
                                "away_score": 0,
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            backfill_path.write_text(
                json.dumps(
                    {
                        "source": "public_result_backfill",
                        "last_updated": "2026-06-14T12:05:00+08:00",
                        "matches": [
                            {
                                "id": 3,
                                "status": "completed",
                                "home_score": 1,
                                "away_score": 1,
                            },
                            {
                                "id": 5,
                                "status": "completed",
                                "home_score": 1,
                                "away_score": 1,
                            },
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            os.environ["MATCH_FEED_PATH"] = str(primary_path)
            os.environ["MATCH_RESULTS_BACKFILL_PATH"] = str(backfill_path)
            os.environ["LOCAL_MATCH_FEED_ENABLED"] = "true"
            importlib.reload(live_match_feed)

            merged = live_match_feed.merge_live_matches(
                [
                    {
                        "id": 3,
                        "home_team": "加拿大",
                        "away_team": "波黑",
                        "group": "B",
                        "round": 1,
                        "match_date": "2026-06-13T03:00:00+08:00",
                        "venue": "BMO球场",
                        "status": "upcoming",
                    },
                    {
                        "id": 5,
                        "home_team": "卡塔尔",
                        "away_team": "瑞士",
                        "group": "B",
                        "round": 1,
                        "match_date": "2026-06-14T03:00:00+08:00",
                        "venue": "李维斯体育场",
                        "status": "upcoming",
                    },
                ]
            )

        by_id = {match["id"]: match for match in merged}
        self.assertEqual(by_id[3]["home_score"], 2)
        self.assertEqual(by_id[3]["away_score"], 0)
        self.assertEqual(by_id[3]["live_source"], "primary_feed")
        self.assertEqual(by_id[5]["status"], "completed")
        self.assertEqual(by_id[5]["home_score"], 1)
        self.assertEqual(by_id[5]["away_score"], 1)
        self.assertEqual(by_id[5]["live_source"], "public_result_backfill")

    def test_feed_match_updates_base_match_by_teams_and_kickoff_when_ids_differ(self):
        with tempfile.TemporaryDirectory() as tmp:
            feed_path = Path(tmp) / "matches.live.json"
            feed_path.write_text(
                json.dumps(
                    {
                        "source": "espn_scoreboard",
                        "last_updated": "2026-06-15T00:00:00+08:00",
                        "matches": [
                            {
                                "id": 760419,
                                "home_team": "巴西",
                                "away_team": "摩洛哥",
                                "group": "C",
                                "round": 1,
                                "match_date": "2026-06-14T06:00:00+08:00",
                                "venue": "MetLife Stadium",
                                "status": "completed",
                                "home_score": 1,
                                "away_score": 1,
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            os.environ["MATCH_FEED_PATH"] = str(feed_path)
            os.environ["MATCH_RESULTS_BACKFILL_PATH"] = str(Path(tmp) / "missing.public-results.json")
            os.environ["LOCAL_MATCH_FEED_ENABLED"] = "true"
            importlib.reload(live_match_feed)

            merged = live_match_feed.merge_live_matches(
                [
                    {
                        "id": 6,
                        "home_team": "巴西",
                        "away_team": "摩洛哥",
                        "group": "C",
                        "round": 1,
                        "match_date": "2026-06-14T06:00:00+08:00",
                        "venue": "大都会人寿体育场，纽约",
                        "status": "upcoming",
                        "home_score": None,
                        "away_score": None,
                    }
                ]
            )

        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["id"], 6)
        self.assertEqual(merged[0]["status"], "completed")
        self.assertEqual(merged[0]["home_score"], 1)
        self.assertEqual(merged[0]["away_score"], 1)
        self.assertEqual(merged[0]["live_source"], "espn_scoreboard")

    def test_feed_match_preserves_schedule_group_and_round_context(self):
        with tempfile.TemporaryDirectory() as tmp:
            feed_path = Path(tmp) / "matches.live.json"
            feed_path.write_text(
                json.dumps(
                    {
                        "source": "espn_scoreboard",
                        "last_updated": "2026-06-19T12:00:00+08:00",
                        "matches": [
                            {
                                "id": 760438,
                                "home_team": "Czechia",
                                "away_team": "South Africa",
                                "group": "A",
                                "round": 1,
                                "match_date": "2026-06-19T00:00:00+08:00",
                                "status": "completed",
                                "home_score": 1,
                                "away_score": 1,
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            os.environ["MATCH_FEED_PATH"] = str(feed_path)
            os.environ["MATCH_RESULTS_BACKFILL_PATH"] = str(Path(tmp) / "missing.public-results.json")
            os.environ["LOCAL_MATCH_FEED_ENABLED"] = "true"
            importlib.reload(live_match_feed)

            merged = live_match_feed.merge_live_matches(
                [
                    {
                        "id": 25,
                        "home_team": "Czechia",
                        "away_team": "South Africa",
                        "group": "A",
                        "round": 2,
                        "match_date": "2026-06-19T00:00:00+08:00",
                        "status": "upcoming",
                    }
                ]
            )

        self.assertEqual(merged[0]["id"], 25)
        self.assertEqual(merged[0]["group"], "A")
        self.assertEqual(merged[0]["round"], 2)
        self.assertEqual(merged[0]["status"], "completed")
        self.assertEqual(merged[0]["home_score"], 1)
        self.assertEqual(merged[0]["away_score"], 1)

    def test_same_fixture_from_manual_feed_and_espn_is_counted_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            primary_path = Path(tmp) / "matches.live.json"
            primary_path.write_text(
                json.dumps(
                    {
                        "source": "manual_correction",
                        "last_updated": "2026-06-15T01:00:00+08:00",
                        "matches": [
                            {
                                "id": 4,
                                "status": "completed",
                                "home_score": 4,
                                "away_score": 1,
                                "report": {
                                    "goals": [
                                        {"minute": 7, "team": "美国", "player": "Damian Bobadilla", "type": "own_goal"},
                                        {"minute": 31, "team": "美国", "player": "Folarin Balogun", "type": "goal"},
                                        {
                                            "minute": 45,
                                            "team": "美国",
                                            "player": "Folarin Balogun",
                                            "assist": "Christian Pulisic",
                                            "type": "goal",
                                        },
                                        {"minute": 73, "team": "巴拉圭", "player": "Mauricio", "type": "goal"},
                                        {"minute": 90, "team": "美国", "player": "Giovanni Reyna", "type": "goal"},
                                    ]
                                },
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            os.environ["MATCH_FEED_PATH"] = str(primary_path)
            os.environ["MATCH_RESULTS_BACKFILL_PATH"] = str(Path(tmp) / "missing.public-results.json")
            os.environ["ESPN_SCOREBOARD_ENABLED"] = "true"
            os.environ["LOCAL_MATCH_FEED_ENABLED"] = "true"
            importlib.reload(live_match_feed)
            live_match_feed.fetch_espn_scoreboard_feed = lambda: {
                "source": "espn_scoreboard",
                "last_updated": "2026-06-15T01:05:00+08:00",
                "matches": [
                    {
                        "id": 760417,
                        "home_team": "美国",
                        "away_team": "巴拉圭",
                        "group": "D",
                        "round": 1,
                        "match_date": "2026-06-13T09:00:00+08:00",
                        "venue": "SoFi体育场，洛杉矶",
                        "status": "completed",
                        "home_score": 4,
                        "away_score": 1,
                        "report": {
                            "goals": [
                                {"minute": 7, "team": "美国", "player": "Damian Bobadilla", "type": "own_goal"},
                                {"minute": 31, "team": "美国", "player": "Folarin Balogun", "type": "goal"},
                                {"minute": 45, "team": "美国", "player": "Folarin Balogun", "type": "goal"},
                                {"minute": 73, "team": "巴拉圭", "player": "Mauricio", "type": "goal"},
                                {"minute": 90, "team": "美国", "player": "Giovanni Reyna", "type": "goal"},
                            ]
                        },
                    }
                ],
            }

            merged = live_match_feed.merge_live_matches(
                [
                    {
                        "id": 4,
                        "home_team": "美国",
                        "away_team": "巴拉圭",
                        "group": "D",
                        "round": 1,
                        "match_date": "2026-06-13T09:00:00+08:00",
                        "venue": "SoFi体育场，洛杉矶",
                        "status": "upcoming",
                    }
                ]
            )

        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["id"], 4)
        self.assertEqual(merged[0]["espn_event_id"], 760417)
        goals = merged[0]["report"]["goals"]
        self.assertEqual(sum(1 for goal in goals if goal.get("player") == "Folarin Balogun"), 2)
        self.assertEqual(sum(1 for goal in goals if goal.get("assist") == "Christian Pulisic"), 1)

    def test_partial_manual_correction_is_enriched_from_schedule_before_merging_espn(self):
        with tempfile.TemporaryDirectory() as tmp:
            schedule_path = Path(tmp) / "matches.schedule.json"
            primary_path = Path(tmp) / "matches.live.json"
            schedule_path.write_text(
                json.dumps(
                    {
                        "matches": [
                            {
                                "id": 12,
                                "home_team": "瑞典",
                                "away_team": "突尼斯",
                                "group": "F",
                                "round": 1,
                                "match_date": "2026-06-15T10:00:00+08:00",
                                "venue": "BBVA体育场，蒙特雷",
                                "status": "upcoming",
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            primary_path.write_text(
                json.dumps(
                    {
                        "source": "manual_correction",
                        "last_updated": "2026-06-15T12:40:00+08:00",
                        "matches": [
                            {
                                "id": 12,
                                "status": "completed",
                                "home_score": 5,
                                "away_score": 1,
                                "report": {
                                    "goals": [
                                        {"minute": 7, "team": "瑞典", "player": "Yasin Ayari", "type": "goal"},
                                        {"minute": 30, "team": "瑞典", "player": "Alexander Isak", "type": "goal"},
                                        {"minute": 43, "team": "突尼斯", "player": "Omar Rekik", "type": "goal"},
                                        {
                                            "minute": 59,
                                            "team": "瑞典",
                                            "player": "Viktor Gyökeres",
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
                                        {"minute": 90, "team": "瑞典", "player": "Yasin Ayari", "type": "goal"},
                                    ]
                                },
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            os.environ["MATCH_SCHEDULE_PATH"] = str(schedule_path)
            os.environ["MATCH_FEED_PATH"] = str(primary_path)
            os.environ["MATCH_RESULTS_BACKFILL_PATH"] = str(Path(tmp) / "missing.public-results.json")
            os.environ["ESPN_SCOREBOARD_ENABLED"] = "true"
            os.environ["LOCAL_MATCH_FEED_ENABLED"] = "true"
            importlib.reload(live_match_feed)
            live_match_feed.fetch_espn_scoreboard_feed = lambda: {
                "source": "espn_scoreboard",
                "last_updated": "2026-06-15T12:45:00+08:00",
                "matches": [
                    {
                        "id": 760424,
                        "home_team": "瑞典",
                        "away_team": "突尼斯",
                        "group": "F",
                        "round": 1,
                        "match_date": "2026-06-15T10:00:00+08:00",
                        "venue": "BBVA体育场，蒙特雷",
                        "status": "completed",
                        "home_score": 5,
                        "away_score": 1,
                        "report": {
                            "goals": [
                                {"minute": 7, "team": "瑞典", "player": "Yasin Ayari", "type": "goal"},
                                {"minute": 30, "team": "瑞典", "player": "Alexander Isak", "type": "goal"},
                                {"minute": 43, "team": "突尼斯", "player": "Omar Rekik", "type": "goal"},
                                {"minute": 59, "team": "瑞典", "player": "Viktor Gyökeres", "type": "goal"},
                                {"minute": 84, "team": "瑞典", "player": "Mattias Svanberg", "type": "goal"},
                                {"minute": 90, "team": "瑞典", "player": "Yasin Ayari", "type": "goal"},
                            ]
                        },
                    }
                ],
            }

            merged = live_match_feed.merge_live_matches([])

        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["id"], 12)
        self.assertEqual(merged[0]["espn_event_id"], 760424)
        goals = merged[0]["report"]["goals"]
        self.assertEqual(sum(1 for goal in goals if goal.get("player") == "Yasin Ayari"), 2)
        self.assertEqual(sum(1 for goal in goals if goal.get("assist") == "Alexander Isak"), 2)

    def test_espn_failure_keeps_local_feed_available(self):
        with tempfile.TemporaryDirectory() as tmp:
            feed_path = Path(tmp) / "matches.live.json"
            feed_path.write_text(
                json.dumps(
                    {
                        "source": "local_unit_feed",
                        "last_updated": "2026-06-14T12:00:00+08:00",
                        "matches": [
                            {
                                "id": 99,
                                "home_team": "Local Home",
                                "away_team": "Local Away",
                                "match_date": "2026-06-14T03:00:00+08:00",
                                "status": "completed",
                                "home_score": 2,
                                "away_score": 1,
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            os.environ["MATCH_FEED_PATH"] = str(feed_path)
            os.environ["MATCH_RESULTS_BACKFILL_PATH"] = str(Path(tmp) / "missing.public-results.json")
            os.environ["ESPN_SCOREBOARD_ENABLED"] = "true"
            os.environ["LOCAL_MATCH_FEED_ENABLED"] = "true"
            importlib.reload(live_match_feed)

            def failing_espn_feed():
                raise TimeoutError("espn timeout")

            live_match_feed.fetch_espn_scoreboard_feed = failing_espn_feed

            status = live_match_feed.refresh_live_cache()
            merged = live_match_feed.merge_live_matches([])

        self.assertEqual(status["match_count"], 1)
        self.assertEqual(status["primary_match_count"], 1)
        self.assertTrue(any("espn_scoreboard" in item for item in status["source_errors"]))
        self.assertEqual(merged[0]["live_source"], "local_unit_feed")

    def test_live_status_does_not_refresh_twice_when_cache_is_empty(self):
        importlib.reload(live_match_feed)
        calls = 0

        def fake_refresh():
            nonlocal calls
            calls += 1
            live_match_feed._CACHE = None
            live_match_feed._SYNC_STATUS = {
                "status": "error",
                "source": "unit_test",
                "last_updated": None,
                "last_sync_attempt": "2026-06-18T00:00:00+00:00",
                "message": "unit test",
                "match_count": 0,
            }
            return dict(live_match_feed._SYNC_STATUS)

        live_match_feed.refresh_live_cache = fake_refresh

        status = live_match_feed.get_live_sync_status(
            [
                {
                    "id": 1,
                    "home_team": "Home",
                    "away_team": "Away",
                    "match_date": "2026-06-12T03:00:00+08:00",
                    "status": "upcoming",
                }
            ]
        )

        self.assertEqual(calls, 1)
        self.assertEqual(status["status"], "error")

    def test_repository_local_feeds_cover_completed_first_round_when_espn_is_unavailable(self):
        data_dir = BACKEND_ROOT / "data"
        os.environ["MATCH_SCHEDULE_PATH"] = str(data_dir / "matches.schedule.json")
        os.environ["MATCH_FEED_PATH"] = str(data_dir / "matches.live.json")
        os.environ["MATCH_RESULTS_BACKFILL_PATH"] = str(data_dir / "matches.public-results.json")
        os.environ["LOCAL_MATCH_FEED_ENABLED"] = "true"
        os.environ["ESPN_SCOREBOARD_ENABLED"] = "false"
        importlib.reload(live_match_feed)

        from services.schedule import load_schedule_matches

        merged = live_match_feed.merge_live_matches(load_schedule_matches())
        first_round = [
            match
            for match in merged
            if match.get("round") == 1 and 1 <= int(match["id"]) <= 24
        ]
        completed_ids = {
            int(match["id"])
            for match in first_round
            if match.get("status") == "completed"
            and match.get("home_score") is not None
            and match.get("away_score") is not None
        }

        self.assertEqual(len(first_round), 24)
        self.assertEqual(completed_ids, set(range(1, 25)))


if __name__ == "__main__":
    unittest.main()
