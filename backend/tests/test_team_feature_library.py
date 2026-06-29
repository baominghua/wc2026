import os
import sys
import tempfile
import unittest
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from services.team_feature_library import (
    build_match_feature_adjustment,
    build_team_feature_library,
    load_team_profile_store,
    sync_team_profile_store,
)


def completed_match(
    match_id,
    home,
    away,
    home_score,
    away_score,
    match_date,
    group="F",
    round_number=1,
    stats=None,
    cards=None,
):
    return {
        "id": match_id,
        "home_team": home,
        "away_team": away,
        "group": group,
        "round": round_number,
        "match_date": match_date,
        "status": "completed",
        "home_score": home_score,
        "away_score": away_score,
        "report": {
            "stats": stats or {},
            "cards": cards or [],
        },
    }


class TeamFeatureLibraryTests(unittest.TestCase):
    def setUp(self):
        self._old_store_path = os.environ.get("TEAM_PROFILE_STORE_PATH")
        self._tmp = tempfile.TemporaryDirectory()
        os.environ["TEAM_PROFILE_STORE_PATH"] = str(Path(self._tmp.name) / "team-profiles.json")

    def tearDown(self):
        if self._old_store_path is None:
            os.environ.pop("TEAM_PROFILE_STORE_PATH", None)
        else:
            os.environ["TEAM_PROFILE_STORE_PATH"] = self._old_store_path
        self._tmp.cleanup()

    def test_builds_profiles_from_completed_matches_before_target_date(self):
        matches = [
            completed_match(
                10,
                "荷兰",
                "日本",
                2,
                2,
                "2026-06-15T04:00:00+08:00",
                stats={
                    "shots_home": 10,
                    "shots_away": 10,
                    "shots_on_target_home": 6,
                    "shots_on_target_away": 3,
                    "corners_home": 5,
                    "corners_away": 4,
                    "yellow_cards_home": 3,
                    "yellow_cards_away": 0,
                },
            ),
            completed_match(
                12,
                "瑞典",
                "突尼斯",
                5,
                1,
                "2026-06-15T10:00:00+08:00",
                stats={
                    "shots_home": 13,
                    "shots_away": 6,
                    "shots_on_target_home": 7,
                    "shots_on_target_away": 2,
                    "corners_home": 4,
                    "corners_away": 2,
                    "yellow_cards_home": 0,
                    "yellow_cards_away": 1,
                },
            ),
            completed_match(
                99,
                "瑞典",
                "荷兰",
                0,
                4,
                "2026-06-23T10:00:00+08:00",
                round_number=3,
                stats={"shots_home": 2, "shots_away": 20},
            ),
        ]

        profiles = build_team_feature_library(matches, before="2026-06-21T01:00:00+08:00")

        self.assertEqual(profiles["荷兰"]["sample_matches"], 1)
        self.assertEqual(profiles["荷兰"]["form_state"]["avg_points"], 1.0)
        self.assertEqual(profiles["荷兰"]["discipline_state"]["yellow_cards_for"], 3.0)
        self.assertIn("discipline_watch", profiles["荷兰"]["tactical_tags"])
        self.assertIn("draw_resilience", profiles["荷兰"]["tactical_tags"])
        self.assertEqual(profiles["瑞典"]["sample_matches"], 1)
        self.assertGreater(profiles["瑞典"]["form_state"]["score"], profiles["荷兰"]["form_state"]["score"])
        self.assertIn("attack_hot", profiles["瑞典"]["tactical_tags"])
        self.assertNotIn("0-4", " ".join(profiles["荷兰"]["review_lessons"]))

    def test_match_feature_adjustment_is_bounded_and_explainable(self):
        matches = [
            completed_match(
                10,
                "荷兰",
                "日本",
                2,
                2,
                "2026-06-15T04:00:00+08:00",
                stats={
                    "shots_home": 10,
                    "shots_away": 10,
                    "shots_on_target_home": 6,
                    "shots_on_target_away": 3,
                    "yellow_cards_home": 3,
                },
            ),
            completed_match(
                12,
                "瑞典",
                "突尼斯",
                5,
                1,
                "2026-06-15T10:00:00+08:00",
                stats={
                    "shots_home": 13,
                    "shots_away": 6,
                    "shots_on_target_home": 7,
                    "shots_on_target_away": 2,
                    "yellow_cards_home": 0,
                },
            ),
        ]
        target = {
            "id": 33,
            "home_team": "荷兰",
            "away_team": "瑞典",
            "group": "F",
            "round": 2,
            "match_date": "2026-06-21T01:00:00+08:00",
            "status": "upcoming",
        }

        adjustment = build_match_feature_adjustment(target, matches)

        self.assertTrue(adjustment["applied"])
        self.assertGreater(adjustment["away_attack_delta"], adjustment["home_attack_delta"])
        self.assertLessEqual(abs(adjustment["home_attack_delta"]), 0.06)
        self.assertLessEqual(abs(adjustment["away_attack_delta"]), 0.06)
        self.assertIn("球队特征库", " ".join(adjustment["reasons"]))
        self.assertEqual(adjustment["team_profiles"]["home"]["team"], "荷兰")
        self.assertEqual(adjustment["team_profiles"]["away"]["team"], "瑞典")
        self.assertTrue(adjustment["team_profiles"]["home"]["next_prediction_notes"])

    def test_syncs_completed_matches_to_persistent_profile_store_and_reuses_it(self):
        matches = [
            completed_match(
                20,
                "Netherlands",
                "Japan",
                2,
                2,
                "2026-06-15T04:00:00+08:00",
                stats={
                    "shots_home": 12,
                    "shots_away": 9,
                    "shots_on_target_home": 6,
                    "shots_on_target_away": 3,
                    "yellow_cards_home": 3,
                },
            ),
            completed_match(
                21,
                "Sweden",
                "Tunisia",
                5,
                1,
                "2026-06-15T10:00:00+08:00",
                stats={
                    "shots_home": 14,
                    "shots_away": 6,
                    "shots_on_target_home": 8,
                    "shots_on_target_away": 2,
                },
            ),
        ]

        payload = sync_team_profile_store(matches)
        loaded = load_team_profile_store()

        self.assertEqual(payload["match_count"], 2)
        self.assertEqual(loaded["match_count"], 2)
        self.assertIn("Netherlands", loaded["profiles"])
        self.assertIn("Sweden", loaded["profiles"])
        self.assertTrue(loaded["profiles"]["Netherlands"]["next_prediction_notes"])

        target = {
            "id": 34,
            "home_team": "Netherlands",
            "away_team": "Sweden",
            "group": "F",
            "round": 2,
            "match_date": "2026-06-21T01:00:00+08:00",
            "status": "upcoming",
        }
        adjustment = build_match_feature_adjustment(target, [], profile_store=loaded)

        self.assertTrue(adjustment["applied"])
        self.assertEqual(adjustment["source"], "team_profile_store")
        self.assertEqual(adjustment["team_profiles"]["home"]["team"], "Netherlands")
        self.assertGreater(adjustment["away_attack_delta"], adjustment["home_attack_delta"])


if __name__ == "__main__":
    unittest.main()
