import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from services.prediction_snapshot_store import load_prediction_snapshots, save_pre_match_prediction


class PredictionSnapshotStoreTests(unittest.TestCase):
    def setUp(self):
        self._old_path = os.environ.get("PREDICTION_SNAPSHOT_PATH")
        self._tmp = tempfile.TemporaryDirectory()
        os.environ["PREDICTION_SNAPSHOT_PATH"] = str(Path(self._tmp.name) / "snapshots.json")

    def tearDown(self):
        if self._old_path is None:
            os.environ.pop("PREDICTION_SNAPSHOT_PATH", None)
        else:
            os.environ["PREDICTION_SNAPSHOT_PATH"] = self._old_path
        self._tmp.cleanup()

    def test_saves_only_predictions_made_before_kickoff(self):
        match = {
            "id": 99,
            "home_team": "Mexico",
            "away_team": "South Africa",
            "status": "upcoming",
            "match_date": "2026-06-12T03:00:00+08:00",
        }
        prediction = {
            "home_win_probability": 0.64,
            "draw_probability": 0.21,
            "away_win_probability": 0.15,
            "predicted_score": "2-0",
        }

        saved = save_pre_match_prediction(
            match,
            prediction,
            now=datetime(2026, 6, 11, 12, 0, tzinfo=timezone.utc),
        )

        self.assertTrue(saved)
        snapshots = load_prediction_snapshots()
        self.assertIn(99, snapshots)
        self.assertEqual(snapshots[99]["predicted_score"], "2-0")

    def test_does_not_save_completed_or_late_predictions(self):
        match = {
            "id": 100,
            "home_team": "Korea Republic",
            "away_team": "Czech Republic",
            "status": "completed",
            "match_date": "2026-06-12T10:00:00+08:00",
        }
        prediction = {"predicted_score": "1-1"}

        saved = save_pre_match_prediction(
            match,
            prediction,
            now=datetime(2026, 6, 12, 3, 0, tzinfo=timezone.utc),
        )

        self.assertFalse(saved)
        self.assertEqual(load_prediction_snapshots(), {})


if __name__ == "__main__":
    unittest.main()
