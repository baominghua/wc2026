import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch


BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from services.injury_feed import get_match_injury_feed
from services.sportmonks import normalise_sportmonks_sidelined_feed


class SportmonksProviderTests(unittest.TestCase):
    def test_normalises_current_sidelined_records(self):
        payload = {
            "data": {
                "id": 18644,
                "name": "Norway",
                "sidelined": [
                    {
                        "player": {"name": "Test Striker"},
                        "type": {"name": "Hamstring"},
                        "start_date": "2026-06-20",
                        "end_date": None,
                        "completed": False,
                    },
                    {
                        "player": {"name": "Old Injury"},
                        "type": {"name": "Knee"},
                        "start_date": "2026-05-01",
                        "end_date": "2026-06-01",
                        "completed": True,
                    },
                ],
            }
        }

        feed = normalise_sportmonks_sidelined_feed(
            {"挪威": payload},
            fetched_at="2026-06-22T12:00:00+08:00",
            match_date="2026-06-23T08:00:00+08:00",
        )

        self.assertEqual(feed["source"], "sportmonks_sidelined")
        self.assertIn("Test Striker（Hamstring）", feed["teams"]["挪威"]["unavailable_players"])
        self.assertNotIn("Old Injury（Knee）", feed["teams"]["挪威"]["unavailable_players"])

    def test_injury_feed_uses_sportmonks_when_configured(self):
        fetched_at = datetime.now(timezone.utc).isoformat()
        feed = {
            "source": "sportmonks_sidelined",
            "last_updated": fetched_at,
            "teams": {
                "挪威": {
                    "unavailable_players": ["Test Striker（Hamstring）"],
                    "doubtful_players": [],
                    "source": "sportmonks_sidelined",
                    "note": "SportMonks sidelined include",
                },
                "塞内加尔": {
                    "unavailable_players": [],
                    "doubtful_players": ["Test Midfielder（Doubtful）", "Test Defender（Doubtful）"],
                    "source": "sportmonks_sidelined",
                    "note": "SportMonks sidelined include",
                },
            },
        }

        with patch.dict(
            "os.environ",
            {
                "API_FOOTBALL_ENABLED": "false",
                "SPORTMONKS_ENABLED": "true",
                "SPORTMONKS_TOKEN": "unit-test-token",
                "PUBLIC_INJURY_SOURCES_ENABLED": "false",
            },
            clear=False,
        ), patch("services.sportmonks.fetch_sportmonks_injury_feed", return_value=feed):
            result = get_match_injury_feed("挪威", "塞内加尔", "2026-06-23T08:00:00+08:00")

        self.assertEqual(result["status"], "connected")
        self.assertEqual(result["source"], "sportmonks_sidelined")
        self.assertTrue(result["provider_key_present"])
        self.assertTrue(result["auto_apply"]["home_key_absence"])
        self.assertTrue(result["auto_apply"]["away_key_absence"])


if __name__ == "__main__":
    unittest.main()
