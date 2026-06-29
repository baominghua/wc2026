from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
PREDICT_PAGE = ROOT / "frontend" / "src" / "pages" / "PredictPage.tsx"
API_TS = ROOT / "frontend" / "src" / "services" / "api.ts"
DAILY_EXPORT = ROOT / "frontend" / "src" / "components" / "DailyPredictionsExport.tsx"
LOTTERY_PAGE = ROOT / "frontend" / "src" / "pages" / "LotteryPage.tsx"
MODEL_DOC = ROOT / "模型预测依据说明.md"
PRD_DOC = ROOT / "PRD-2026世界杯预测与数据分析网站.md"


class PredictionPageExportTests(unittest.TestCase):
    def test_prediction_page_and_download_image_show_alternative_scorelines(self):
        source = PREDICT_PAGE.read_text(encoding="utf-8")

        self.assertIn("const alternativeScores", source)
        self.assertIn("其他2个最有可能结果", source)
        self.assertIn("possible_scores?.slice(1, 3)", source)

    def test_download_image_includes_total_goals_and_over_under_summary(self):
        source = PREDICT_PAGE.read_text(encoding="utf-8")

        self.assertIn("总进球与大小球", source)
        self.assertIn("mainLineLabel", source)
        self.assertIn("overUnderLabel", source)

    def test_total_goals_card_separates_probability_from_signal_strength(self):
        source = PREDICT_PAGE.read_text(encoding="utf-8")

        self.assertIn("主线方向概率", source)
        self.assertIn("主线信号强度", source)
        self.assertIn("保护：{totalGoalsProtectionRecommendation}", source)
        self.assertIn("totalGoalsSignalStrength", source)
        self.assertNotIn("大小球置信度", source)

    def test_mobile_download_uses_blob_or_share_instead_of_data_url_navigation(self):
        source = PREDICT_PAGE.read_text(encoding="utf-8")

        self.assertIn("canvas.toBlob", source)
        self.assertIn("URL.createObjectURL", source)
        self.assertIn("canvas.toDataURL", source)
        self.assertIn("window.setTimeout", source)
        self.assertIn("document.body.appendChild(link)", source)
        self.assertIn("navigator.canShare", source)
        self.assertIn("window.open('', '_blank'", source)
        self.assertNotIn("window.open('', '_blank', 'noopener,noreferrer')", source)
        self.assertIn("downloadStatus", source)

    def test_single_match_export_uses_pre_match_brief_copy(self):
        source = PREDICT_PAGE.read_text(encoding="utf-8")

        self.assertIn("2026WC赛前简报", source)
        self.assertIn("大小", source)
        self.assertIn("主线", source)
        self.assertIn("信号", source)
        self.assertIn("冷门概率", source)
        self.assertIn("免责声明", source)
        self.assertNotIn("2026 世界杯单场预测", source)
        self.assertNotIn("['妯″瀷', prediction.model_version]", source)

    def test_prediction_page_and_download_image_include_corners_cards_and_basis(self):
        source = PREDICT_PAGE.read_text(encoding="utf-8")

        self.assertIn("set_piece_card_prediction", source)
        self.assertIn("角球与黄牌预测", source)
        self.assertIn("角球/黄牌依据", source)
        self.assertIn("imageSetPieceCards", source)
        self.assertIn("downloadBasisItems", source)

    def test_single_match_export_core_points_include_rankings_and_key_injuries(self):
        source = PREDICT_PAGE.read_text(encoding="utf-8")

        self.assertIn("function buildRankingInsight", source)
        self.assertIn("function buildInjuryInsight", source)
        self.assertIn("function buildInjuryFactorInsight", source)
        self.assertIn("buildPosterInsights(prediction, selectedMatch, selectedInjuryFeed)", source)
        self.assertIn("return Array.from(new Set(candidates)).slice(0, 8)", source)
        self.assertIn("Elo评分", source)
        self.assertIn("世界排名", source)
        self.assertIn("关键伤停", source)

    def test_injury_summary_shows_specific_player_names(self):
        source = PREDICT_PAGE.read_text(encoding="utf-8")

        self.assertIn("缺阵/停赛 ${formatPosterPlayerList(status.unavailable_players, 4)}", source)
        self.assertIn("成疑 ${formatPosterPlayerList(status.doubtful_players, 4)}", source)
        self.assertIn("停赛风险 ${formatPosterPlayerList(status.card_risk_players, 4)}", source)
        self.assertNotIn("缺阵${unavailable}人", source)

    def test_prediction_page_exposes_daily_export_and_blocks_stale_single_export(self):
        source = PREDICT_PAGE.read_text(encoding="utf-8")

        self.assertIn("import DailyPredictionsExport", source)
        self.assertIn("<DailyPredictionsExport matches={matches} loading={matchesLoading}", source)
        self.assertIn("predictionMatchId", source)
        self.assertIn("predictionRequestIdRef", source)
        self.assertIn("predictionMatchId !== selectedMatch.id", source)
        self.assertIn("请先完成当前比赛预测", source)

    def test_prediction_page_and_download_image_show_market_and_upset_reference(self):
        source = PREDICT_PAGE.read_text(encoding="utf-8")

        self.assertIn("市场信号与冷门参考", source)
        self.assertIn("冷门概率", source)
        self.assertIn("冷门比分", source)
        self.assertIn("prediction.market_calibration", source)
        self.assertIn("prediction.upset_prediction", source)
        self.assertIn("imageMarketCalibration", source)
        self.assertIn("imageUpset", source)

    def test_daily_prediction_export_includes_score_pool_and_upset_probability(self):
        source = DAILY_EXPORT.read_text(encoding="utf-8")

        self.assertIn("比分池", source)
        self.assertIn("冷门比分", source)
        self.assertIn("possible_scores", source)
        self.assertIn("upset_prediction", source)
        self.assertIn("formatScorePool", source)
        self.assertIn("formatUpsetScore", source)

    def test_daily_prediction_export_uses_selected_day_and_all_day_matches(self):
        source = DAILY_EXPORT.read_text(encoding="utf-8")
        predict_source = PREDICT_PAGE.read_text(encoding="utf-8")

        self.assertIn("targetDayKey?: string", source)
        self.assertIn("maxMatches?: number", source)
        self.assertIn("targetDayKey={activeScheduleDayKey}", predict_source)
        self.assertIn("maxMatches={activeDateMatches.length}", predict_source)
        self.assertIn("下载${dayLabel(exportTarget.dayKey)}${exportTarget.matches.length}场预测", source)
        self.assertIn("typeof maxMatches === 'number' ? Math.max(1, maxMatches) : dayMatches.length", source)
        self.assertNotIn("maxMatches = 4", source)
        self.assertNotIn("dayMatches.slice(0, 4)", source)

    def test_daily_prediction_export_uses_single_match_context_parameters(self):
        source = DAILY_EXPORT.read_text(encoding="utf-8")

        self.assertIn("detectBatchVenueAdvantage", source)
        self.assertIn("detectBatchWeatherContext", source)
        self.assertIn("injuryAPI", source)
        self.assertIn(".getMatchInjuries", source)
        self.assertIn("advantage_team: venueAdvantage.side", source)
        self.assertIn("advantage_level: venueAdvantage.level", source)
        self.assertIn("force_neutral: false", source)
        self.assertIn("weather: weatherContext.weather", source)
        self.assertIn("venue_factor: weatherContext.venue_factor", source)
        self.assertIn("home_key_absence: Boolean(injuryFeed?.auto_apply.home_key_absence)", source)
        self.assertIn("away_key_absence: Boolean(injuryFeed?.auto_apply.away_key_absence)", source)

    def test_daily_prediction_export_enlarges_top_three_scores_and_refines_total_goals_copy(self):
        source = DAILY_EXPORT.read_text(encoding="utf-8")

        self.assertIn("function getScorePoolItems", source)
        self.assertIn("function drawScorePick", source)
        self.assertIn("const labels = ['首选', '次选', '三选']", source)
        self.assertIn("前三比分池", source)
        self.assertIn("大小球主线", source)
        self.assertIn("主线大小", source)
        self.assertIn("formatTotalGoalsShort", source)

    def test_knockout_prediction_ui_exposes_extra_time_and_penalty_decision_layer(self):
        page_source = PREDICT_PAGE.read_text(encoding="utf-8")
        api_source = API_TS.read_text(encoding="utf-8")

        self.assertIn("extra_time_probability?: number", api_source)
        self.assertIn("knockout_decision?:", api_source)
        self.assertIn("regular_time_draw_probability", api_source)
        self.assertIn("extra_time_probability", page_source)
        self.assertIn("knockoutDecision", page_source)
        self.assertIn("90分钟平局", page_source)
        self.assertIn("加时决胜", page_source)
        self.assertIn("点球决胜", page_source)

    def test_single_match_download_image_draws_knockout_decision_layer(self):
        source = PREDICT_PAGE.read_text(encoding="utf-8")

        self.assertIn("imageKnockoutDecision", source)
        self.assertIn("hasImageKnockoutDecision", source)
        self.assertIn("drawKnockoutDecisionMetric", source)
        self.assertIn("posterKnockoutDecisionY", source)
        self.assertIn("90分钟比分与晋级概率分开读取", source)

    def test_single_match_download_image_visibly_updates_group_stage_poster(self):
        source = PREDICT_PAGE.read_text(encoding="utf-8")

        self.assertIn("drawPosterScorePick", source)
        self.assertIn("scoreCardAccent", source)
        self.assertIn("前三比分池 · 等权放大", source)
        self.assertIn("posterTotalGoalsSummary", source)
        self.assertIn("大小球主线", source)
        self.assertIn("小组赛复盘口径", source)
        self.assertNotIn("const active = index === 0", source)

    def test_daily_prediction_download_image_draws_knockout_decision_layer(self):
        source = DAILY_EXPORT.read_text(encoding="utf-8")

        self.assertIn("getKnockoutDecisionText", source)
        self.assertIn("drawKnockoutDecisionStrip", source)
        self.assertIn("isKnockoutPrediction", source)
        self.assertIn("knockout_decision", source)
        self.assertIn("90分钟平局", source)
        self.assertIn("加时决胜", source)
        self.assertIn("点球决胜", source)

    def test_public_copy_uses_neutral_market_signal_wording(self):
        public_text = "\n".join([
            PREDICT_PAGE.read_text(encoding="utf-8"),
            LOTTERY_PAGE.read_text(encoding="utf-8"),
            MODEL_DOC.read_text(encoding="utf-8"),
            PRD_DOC.read_text(encoding="utf-8"),
        ])

        self.assertIn("赛前市场信号", public_text)
        self.assertIn("实时赔率", public_text)
        forbidden_terms = (
            "\u535a\u5f69",
            "\u6295\u6ce8",
            "\u4e0b\u6ce8",
        )
        for forbidden in forbidden_terms:
            self.assertNotIn(forbidden, public_text)


if __name__ == "__main__":
    unittest.main()
