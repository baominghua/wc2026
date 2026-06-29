from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
TOURNAMENT_PAGE = ROOT / "frontend" / "src" / "pages" / "TournamentPage.tsx"


class TournamentExportLayoutTests(unittest.TestCase):
    def test_landscape_final_hub_leaves_room_for_semifinals(self):
        source = TOURNAMENT_PAGE.read_text(encoding="utf-8")

        self.assertIn("positions.set(101, { x: 37", source)
        self.assertIn("positions.set(102, { x: 63", source)
        self.assertIn("positions.set(104, { x: 50, y: 50", source)
        self.assertNotIn("w-[720px]", source)
        self.assertIn("w-[520px]", source)
        self.assertIn("top-[50%]", source)


if __name__ == "__main__":
    unittest.main()
