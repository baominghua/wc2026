import sys
import unittest
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from schemas.match import MatchDetail


class MatchSchemaTests(unittest.TestCase):
    def test_match_detail_accepts_decimal_possession(self):
        detail = MatchDetail(
            id=760460,
            home_team="Panama",
            away_team="Croatia",
            match_date="2026-06-24T07:00:00+08:00",
            venue="NRG Stadium",
            status="completed",
            home_possession=53.6,
            away_possession=46.4,
        )

        self.assertEqual(detail.home_possession, 53.6)
        self.assertEqual(detail.away_possession, 46.4)


if __name__ == "__main__":
    unittest.main()
