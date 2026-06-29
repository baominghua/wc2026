import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch


BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from services.injury_feed import get_match_injury_feed
from services.public_injury_sources import parse_transfermarkt_injury_page


class PublicInjurySourceTests(unittest.TestCase):
    def test_parses_transfermarkt_injury_and_card_risk_rows(self):
        html = """
        <h2 class="content-box-headline">Suspensions and injuries</h2>
        <table class="items"><tbody>
          <tr><td class="extrarow bg_blau_20 hauptlink" colspan="6">Injuries</td></tr>
          <tr class="odd"><td><table class="inline-table"><tr><td rowspan="2"></td>
            <td class="hauptlink"><a title="Neymar" href="/neymar/profil/spieler/68290">Neymar</a></td></tr>
            <tr><td>Attacking Midfield</td></tr></table></td>
            <td class="zentriert">34</td><td class="links hauptlink img-vat">Calf injury</td>
            <td class="zentriert">May 18, 2026</td><td class="zentriert"></td><td class="zentriert">4</td></tr>
        </tbody></table>
        <h2 class="content-box-headline">Risk of suspension</h2>
        <table class="items"><tbody>
          <tr class="even"><td><table class="inline-table"><tr><td rowspan="2"></td>
            <td class="hauptlink"><a title="Raphinha" href="/raphinha/profil/spieler/411295">Raphinha</a></td></tr>
            <tr><td>Left Winger</td></tr></table></td>
            <td class="zentriert">29</td><td class="links hauptlink img-vat">Yellow cards</td>
            <td class="zentriert">Jun 21, 2026</td><td class="zentriert"></td><td class="zentriert">0</td></tr>
        </tbody></table>
        """

        parsed = parse_transfermarkt_injury_page(html)

        self.assertEqual(parsed["unavailable"][0]["name"], "Neymar")
        self.assertEqual(parsed["unavailable"][0]["reason"], "Calf injury")
        self.assertEqual(parsed["card_risk"][0]["name"], "Raphinha")

    def test_injury_feed_merges_public_source_without_removing_local_data(self):
        fresh_updated_at = datetime.now(timezone.utc).isoformat()
        local_feed = {
            "source": "manual_review",
            "last_updated": fresh_updated_at,
            "teams": {
                "巴西": {
                    "unavailable_players": ["Manual Player（Knee）"],
                    "doubtful_players": [],
                    "source": "manual_review",
                    "note": "人工复核伤停",
                },
                "摩洛哥": {
                    "unavailable_players": [],
                    "doubtful_players": [],
                    "source": "manual_review",
                    "note": "人工复核暂无",
                },
            },
        }
        public_feed = {
            "source": "transfermarkt_public",
            "last_updated": fresh_updated_at,
            "teams": {
                "巴西": {
                    "unavailable_players": ["Neymar（Calf injury）"],
                    "doubtful_players": [],
                    "card_risk_players": ["Raphinha（Yellow cards）"],
                    "source": "transfermarkt_public",
                    "note": "公开源当前记录缺阵/停赛 1 人，停赛风险 1 人",
                },
                "摩洛哥": {
                    "unavailable_players": [],
                    "doubtful_players": [],
                    "card_risk_players": [],
                    "source": "transfermarkt_public",
                    "note": "公开源暂无伤病、停赛或停赛风险记录",
                },
            },
        }

        with patch.dict("os.environ", {"API_FOOTBALL_ENABLED": "false", "SPORTMONKS_ENABLED": "false"}, clear=False), patch(
            "services.injury_feed._read_public_feed", return_value=(public_feed, None)
        ), patch("services.injury_feed._read_local_feed", return_value=local_feed):
            result = get_match_injury_feed("巴西", "摩洛哥", "2026-06-14T06:00:00+08:00")

        self.assertEqual(result["status"], "connected")
        self.assertIn("Manual Player（Knee）", result["teams"]["home"]["unavailable_players"])
        self.assertIn("Neymar（Calf injury）", result["teams"]["home"]["unavailable_players"])
        self.assertIn("Raphinha（Yellow cards）", result["teams"]["home"]["card_risk_players"])


if __name__ == "__main__":
    unittest.main()
