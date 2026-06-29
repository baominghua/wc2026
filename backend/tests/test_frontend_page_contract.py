from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
HOME_PAGE = ROOT / "frontend" / "src" / "pages" / "HomePage.tsx"
TEAM_DETAIL_PAGE = ROOT / "frontend" / "src" / "pages" / "TeamDetail.tsx"
PREDICT_PAGE = ROOT / "frontend" / "src" / "pages" / "PredictPage.tsx"
WC2026_DATA = ROOT / "frontend" / "src" / "services" / "wc2026-data.ts"
DAILY_EXPORT = ROOT / "frontend" / "src" / "components" / "DailyPredictionsExport.tsx"
LOTTERY_PAGE = ROOT / "frontend" / "src" / "pages" / "LotteryPage.tsx"
MATCHES_PAGE = ROOT / "frontend" / "src" / "pages" / "MatchesPage.tsx"


class FrontendPageContractTests(unittest.TestCase):
    def test_team_detail_page_renders_team_feature_profile(self):
        source = TEAM_DETAIL_PAGE.read_text(encoding="utf-8")

        self.assertIn("teamAPI.getTeamDetail", source)
        self.assertIn("feature_profile", source)
        self.assertIn("球队特征库", source)
        self.assertIn("下次预测注意事项", source)

    def test_home_explore_more_matches_current_modules(self):
        source = HOME_PAGE.read_text(encoding="utf-8")

        expected_routes = ("/predict", "/tournament", "/reviews", "/teams", "/matches", "/stats")
        for route in expected_routes:
            self.assertIn(f"link: '{route}'", source)
        self.assertIn("出线与淘汰赛", source)
        self.assertIn("赛果复盘", source)
        self.assertIn("球队档案", source)
        self.assertIn("模型记忆", source)

    def test_predict_match_picker_selects_match_and_detail_keeps_team_links(self):
        source = PREDICT_PAGE.read_text(encoding="utf-8")

        self.assertIn("SELECTED_MATCH_REFRESH_MS = 180000", source)
        self.assertIn('data-testid="match-selector-card"', source)
        self.assertNotIn("<TeamFlagLink teamName={match.home_team}", source)
        self.assertNotIn("<TeamFlagLink teamName={match.away_team}", source)
        self.assertIn('data-testid="match-detail-home-team-link"', source)
        self.assertIn('data-testid="match-detail-away-team-link"', source)

    def test_frontend_uses_effective_knockout_stage_for_resolved_bracket_matches(self):
        data_source = WC2026_DATA.read_text(encoding="utf-8")
        self.assertIn("getEffectiveMatchStage", data_source)
        self.assertIn("isEffectiveKnockoutMatch", data_source)
        self.assertIn("2026-06-29T00:00:00+08:00", data_source)

        for path in (PREDICT_PAGE, DAILY_EXPORT, LOTTERY_PAGE, MATCHES_PAGE):
            source = path.read_text(encoding="utf-8")
            self.assertIn("getEffectiveMatchStage", source, path.name)
            self.assertIn("isEffectiveKnockoutMatch", source, path.name)

        predict_source = PREDICT_PAGE.read_text(encoding="utf-8")
        daily_source = DAILY_EXPORT.read_text(encoding="utf-8")
        lottery_source = LOTTERY_PAGE.read_text(encoding="utf-8")
        self.assertNotIn("is_knockout: !!selectedMatch.stage", predict_source)
        self.assertNotIn("is_knockout: !!selectedMatch.stage", lottery_source)
        self.assertNotIn("Boolean(match.stage && !match.group)", daily_source)


if __name__ == "__main__":
    unittest.main()
