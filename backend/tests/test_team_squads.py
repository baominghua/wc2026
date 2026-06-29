import sys
import unittest
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from services.team_squads import all_team_squads, get_team_squad, squad_lineup


class TeamSquadsTests(unittest.TestCase):
    def test_all_48_teams_have_official_26_player_squad(self):
        squads = all_team_squads()

        self.assertEqual(len(squads), 48)
        self.assertFalse({code: squad["player_count"] for code, squad in squads.items() if squad["player_count"] != 26})
        self.assertEqual(get_team_squad("AUT")["player_count"], 26)

    def test_france_squad_excludes_retired_players_and_drives_lineup(self):
        squad = get_team_squad("FRA")
        names = {player["name"] for player in squad["players"]}
        starters, bench = squad_lineup("FRA", "4-3-3")
        stale = {"Antoine Griezmann", "Olivier Giroud", "Griezmann", "Giroud"}

        self.assertFalse(names & stale)
        self.assertEqual(len(starters), 11)
        self.assertTrue(set(starters).issubset(names))
        self.assertFalse(set(starters + bench) & stale)


if __name__ == "__main__":
    unittest.main()
