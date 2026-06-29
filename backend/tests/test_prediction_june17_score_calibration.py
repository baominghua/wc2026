import sys
import unittest
from pathlib import Path
from unittest.mock import patch


BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from services.prediction_model import predict_match


class June17ScoreCalibrationTests(unittest.TestCase):
    def test_high_tempo_group_stage_backtest_keeps_reference_scores_in_pool(self):
        reference_matches = [
            ("France", "Senegal", "3-1"),
            ("Argentina", "Algeria", "3-0"),
            ("Austria", "Jordan", "3-1"),
        ]

        with patch.dict("os.environ", {"ODDS_MARKET_ENABLED": "false"}, clear=False):
            score_pools = [
                {item["score"] for item in predict_match(home, away, match_round=1)["possible_scores"]}
                for home, away, _ in reference_matches
            ]

        retained = sum(
            actual in score_pool
            for score_pool, (_, _, actual) in zip(score_pools, reference_matches)
        )
        self.assertGreaterEqual(retained, 2, score_pools)


if __name__ == "__main__":
    unittest.main()
