import json
import sys
import unittest
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from services.pre_world_cup_history import load_pre_world_cup_official_matches


def _project_teams():
    schedule = json.loads((BACKEND_ROOT / "data" / "matches.schedule.json").read_text(encoding="utf-8"))
    teams = []
    for match in schedule.get("matches", [])[:72]:
        for key in ("home_team", "away_team"):
            team = match.get(key)
            if team and team not in teams:
                teams.append(team)
    return teams


class PreWorldCupHistoryTests(unittest.TestCase):
    def test_all_project_teams_have_three_official_pre_world_cup_samples(self):
        rows = load_pre_world_cup_official_matches()
        payload = json.loads((BACKEND_ROOT / "data" / "pre_worldcup_official_matches.json").read_text(encoding="utf-8"))
        project_teams = set(_project_teams())
        coverage = {item["team"]: item for item in payload.get("team_coverage", [])}

        self.assertEqual(len(project_teams), 48)
        self.assertEqual(set(coverage), project_teams)
        self.assertGreaterEqual(len(rows), 100)

        for team in project_teams:
            item = coverage[team]
            self.assertEqual(item.get("sample_count"), 3, team)
            self.assertEqual(len(item.get("selected_match_ids", [])), 3, team)
            selected_rows = [
                row
                for row in rows
                if team in set(row.get("selected_for_teams") or [])
            ]
            self.assertEqual(len(selected_rows), 3, team)

    def test_rows_are_official_completed_and_do_not_mix_friendlies(self):
        rows = load_pre_world_cup_official_matches()
        for row in rows:
            self.assertTrue(row.get("is_official"), row.get("id"))
            self.assertEqual(row.get("status"), "completed", row.get("id"))
            self.assertNotIn("Friendly", str(row.get("competition")), row.get("id"))
            self.assertNotIn("Friendlies", str(row.get("competition")), row.get("id"))
            self.assertTrue(str(row.get("source_url", "")).startswith("https://www.fotmob.com/api/data/matchDetails?matchId="))

    def test_complete_technical_rows_have_required_keys_without_nulls(self):
        rows = load_pre_world_cup_official_matches()
        required_stats = {
            "shots_home",
            "shots_away",
            "shots_on_target_home",
            "shots_on_target_away",
            "corners_home",
            "corners_away",
            "yellow_cards_home",
            "yellow_cards_away",
            "red_cards_home",
            "red_cards_away",
        }

        complete_rows = 0
        for row in rows:
            stats = row.get("report", {}).get("stats", {})
            if row.get("data_quality") == "A":
                complete_rows += 1
                self.assertTrue(required_stats.issubset(stats.keys()), row.get("id"))
                for key in required_stats:
                    self.assertIsNotNone(stats.get(key), f"{row.get('id')} {key}")

        self.assertGreaterEqual(complete_rows, 100)


if __name__ == "__main__":
    unittest.main()
