import asyncio
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException


BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from routers.predictions import PredictionRequest, predict_match_result


class PredictionKnockoutStageTests(unittest.TestCase):
    def test_selected_resolved_bracket_match_forces_knockout_model(self):
        match = {
            "id": 901,
            "home_team": "加拿大",
            "away_team": "南非",
            "group": None,
            "round": None,
            "match_date": "2026-06-29T09:00:00+08:00",
            "venue": "BMO Field, Toronto",
            "status": "upcoming",
        }
        prediction_payload = {
            "home_win_probability": 0.55,
            "draw_probability": 0.24,
            "away_win_probability": 0.21,
            "predicted_score": "2-1",
            "confidence": 0.62,
            "model_version": "unit-test",
            "factors": [],
        }

        with patch("routers.predictions.load_pre_world_cup_official_matches", return_value=[]), patch(
            "routers.predictions.merge_live_matches", return_value=[match]
        ), patch("routers.predictions.sync_team_profile_store", return_value={}), patch(
            "routers.predictions.build_review_adjustment", return_value=None
        ), patch("routers.predictions.build_match_feature_adjustment", return_value=None), patch(
            "routers.predictions.get_match_injury_feed", return_value={"auto_apply": {}}
        ), patch("routers.predictions.save_pre_match_prediction"), patch(
            "routers.predictions.build_skill_audit", return_value={}
        ), patch("routers.predictions.predict_match", return_value=prediction_payload) as predict_mock:
            result = asyncio.run(
                predict_match_result(
                    PredictionRequest(
                        match_id=901,
                        home_team="加拿大",
                        away_team="南非",
                    )
                )
            )

        self.assertEqual(result["predicted_score"], "2-1")
        kwargs = predict_mock.call_args.kwargs
        self.assertTrue(kwargs["is_knockout"])
        self.assertEqual(kwargs["stage"], "Round of 32")
        self.assertIsNone(kwargs["match_round"])

    def test_placeholder_knockout_fixture_is_rejected_before_prediction(self):
        match = {
            "id": 73,
            "home_team": "A2",
            "away_team": "B2",
            "group": None,
            "round": None,
            "stage": "Round of 32",
            "match_date": "2026-07-02T03:00:00+08:00",
            "venue": "Slot 73",
            "status": "upcoming",
            "fixture_status": "placeholder",
        }

        with patch("routers.predictions.load_pre_world_cup_official_matches", return_value=[]), patch(
            "routers.predictions.merge_live_matches", return_value=[match]
        ), patch("routers.predictions.predict_match") as predict_mock:
            with self.assertRaises(HTTPException) as raised:
                asyncio.run(
                    predict_match_result(
                        PredictionRequest(
                            match_id=73,
                            home_team="A2",
                            away_team="B2",
                            stage="Round of 32",
                            is_knockout=True,
                        )
                    )
                )

        self.assertEqual(raised.exception.status_code, 400)
        predict_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
