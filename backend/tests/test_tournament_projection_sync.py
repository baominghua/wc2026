from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
TOURNAMENT_PAGE = ROOT / "frontend" / "src" / "pages" / "TournamentPage.tsx"
TOURNAMENT_PROJECTION = ROOT / "backend" / "services" / "tournament_projection.py"
TOURNAMENT_ROUTER = ROOT / "backend" / "routers" / "tournament.py"


class TournamentProjectionSyncTests(unittest.TestCase):
    def test_mobile_and_desktop_exports_use_same_poster_dom(self):
        source = TOURNAMENT_PAGE.read_text(encoding="utf-8")

        self.assertIn("void exportNode(node, fileName, label)", source)
        self.assertIn("手机端与电脑端使用同一版高清海报", source)
        self.assertNotIn("renderSvgTemplateToPng", source)
        self.assertNotIn("MobilePosterTemplate", source)
        self.assertNotIn("buildMobilePosterTemplate", source)
        self.assertNotIn("轻量模板", source)

    def test_tournament_projection_uses_single_match_context_inputs(self):
        source = TOURNAMENT_PROJECTION.read_text(encoding="utf-8")

        self.assertIn("def _contextual_predictor_factory", source)
        self.assertIn("profile_store = sync_team_profile_store(context_matches)", source)
        self.assertIn("build_review_adjustment(match_context, context_matches)", source)
        self.assertIn("build_match_feature_adjustment(", source)
        self.assertIn("get_match_injury_feed(", source)
        self.assertIn("TOURNAMENT_REMOTE_INJURY_ENABLED", source)
        self.assertIn("weather=venue_context[\"weather\"]", source)
        self.assertIn("venue_factor=venue_context[\"venue_factor\"]", source)
        self.assertIn("match_context=match_context", source)
        self.assertIn("schedule_by_id=schedule_by_id", source)

    def test_tournament_endpoint_uses_same_history_pool_as_single_prediction(self):
        source = TOURNAMENT_ROUTER.read_text(encoding="utf-8")

        self.assertIn("load_pre_world_cup_official_matches", source)
        self.assertIn("[*load_pre_world_cup_official_matches(), *merge_live_matches(mock_matches)]", source)


if __name__ == "__main__":
    unittest.main()
