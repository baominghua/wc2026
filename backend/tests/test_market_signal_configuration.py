from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
COMPOSE_FILE = ROOT / "docker-compose.yml"
PREDICT_PAGE = ROOT / "frontend" / "src" / "pages" / "PredictPage.tsx"


class MarketSignalConfigurationTests(unittest.TestCase):
    def test_compose_passes_market_signal_env_to_backend(self):
        compose = COMPOSE_FILE.read_text(encoding="utf-8")

        required_env = [
            "ODDS_MARKET_ENABLED",
            "ODDS_PROVIDER",
            "THE_ODDS_API_KEY",
            "THE_ODDS_API_SPORT_KEY",
            "THE_ODDS_API_REGIONS",
            "THE_ODDS_API_MARKETS",
            "THE_ODDS_API_ODDS_FORMAT",
            "THE_ODDS_API_TIMEOUT_SECONDS",
        ]
        for key in required_env:
            self.assertIn(f"{key}: \"${{{key}", compose)
        self.assertIn('ODDS_MARKET_ENABLED: "${ODDS_MARKET_ENABLED:-true}"', compose)

    def test_predict_page_uses_clear_market_signal_status_labels(self):
        source = PREDICT_PAGE.read_text(encoding="utf-8")

        self.assertIn("not_configured: '待配置赔率源'", source)
        self.assertIn("historical_prior: '历史样本参考'", source)
        self.assertIn("error: '连接异常'", source)
        self.assertIn("unsupported_provider: '数据源不支持'", source)


if __name__ == "__main__":
    unittest.main()
