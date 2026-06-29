from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Mapping

from services.espn_scoreboard import ESPN_SCOREBOARD_URL
from services.odds_market import (
    HISTORICAL_MARKET_SOURCE,
    HISTORICAL_MARKET_SOURCE_URL,
    HISTORICAL_PRIOR_SAMPLE_MATCHES,
    THE_ODDS_API_BASE_URL,
)


SHANGHAI_TZ = timezone(timedelta(hours=8))
OPENFOOTBALL_WORLDCUP_URL = "https://github.com/openfootball/worldcup"
STATSBOMB_OPEN_DATA_URL = "https://github.com/statsbomb/open-data"
API_FOOTBALL_DOCS_URL = "https://www.api-football.com/documentation-v3"
SPORTMONKS_DOCS_URL = "https://docs.sportmonks.com/football"
SPORTMONKS_SIDELINED_URL = "https://www.sportmonks.com/glossary/injuries-and-suspensions/"
FIFA_RANKING_URL = "https://inside.fifa.com/fifa-world-ranking/men"
WC_SQUADS_SOURCE_URL = "https://en.wikipedia.org/wiki/2026_FIFA_World_Cup_squads"
TRANSFERMARKT_PARTICIPANTS_URL = "https://www.transfermarkt.us/world-cup/teilnehmer/pokalwettbewerb/FIWC"
ESPN_INJURY_TRACKER_URL = "https://www.espn.com/soccer/story/_/id/48572979/2026-fifa-world-cup-injuries-tracker-which-stars-miss-latest-info"
SPORTS_MOLE_TEAM_NEWS_URL = "https://www.sportsmole.co.uk/football/world-cup-2026/team-news/"
TRANSFERMARKT_HISTORICAL_INJURIES_URL = (
    "https://raw.githubusercontent.com/salimt/football-datasets/main/"
    "datalake/transfermarkt/player_injuries/player_injuries.csv"
)


def _now_iso() -> str:
    return datetime.now(SHANGHAI_TZ).replace(microsecond=0).isoformat()


def _env_enabled(name: str, default: bool = True) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() not in {"0", "false", "no", "off"}


def _realtime_market_source(market_odds: Mapping[str, Any] | None) -> Dict[str, Any]:
    market_odds = market_odds or {}
    raw_status = str(market_odds.get("status") or "not_configured")
    source = str(market_odds.get("source") or os.getenv("ODDS_PROVIDER", "the_odds_api"))
    available = bool(market_odds.get("available"))

    if source == "the_odds_api" and available and raw_status in {"connected", "no_markets"}:
        status = "connected" if raw_status == "connected" else "no_markets"
        message = str(market_odds.get("message") or "赛前实时赔率源已接入。")
    elif raw_status == "historical_prior" or source == HISTORICAL_MARKET_SOURCE:
        status = "not_configured"
        message = "实时赔率源未启用；当前使用公开历史赔率样本低权重参考。"
    elif raw_status in {"disabled", "unsupported_provider", "error", "no_match", "not_configured"}:
        status = raw_status
        message = str(market_odds.get("message") or "实时赔率源未能用于本场。")
    else:
        status = "not_configured"
        message = str(market_odds.get("message") or "实时赔率源未配置。")

    return {
        "id": "realtime_market_odds",
        "label": "实时赔率",
        "provider": "The Odds API",
        "status": status,
        "source": source,
        "source_url": os.getenv("THE_ODDS_API_BASE_URL", THE_ODDS_API_BASE_URL),
        "role": "赛前市场共识校验",
        "scope": "胜平负/大小球/让球，只有匹配到本场才参与低权重校准",
        "weight": "matched_only",
        "last_updated": market_odds.get("last_updated"),
        "message": message,
    }


def _football_data_source(market_odds: Mapping[str, Any] | None) -> Dict[str, Any]:
    market_odds = market_odds or {}
    is_active_prior = market_odds.get("source") == HISTORICAL_MARKET_SOURCE
    return {
        "id": "football_data_historical_odds",
        "label": "Football-Data",
        "provider": "Football-Data.co.uk",
        "status": "connected" if is_active_prior else "standby",
        "source": HISTORICAL_MARKET_SOURCE,
        "source_url": str(market_odds.get("source_url") or HISTORICAL_MARKET_SOURCE_URL),
        "role": "历史盘口/赛果样本",
        "scope": "用于热门受阻、平局和总进球风险先验，不替代实时赔率",
        "weight": "low",
        "last_updated": market_odds.get("last_updated") if is_active_prior else _now_iso(),
        "sample_match_count": int(market_odds.get("sample_match_count") or HISTORICAL_PRIOR_SAMPLE_MATCHES),
        "message": "已作为历史样本源接入；无实时赔率时低权重参考。",
    }


def _api_football_source() -> Dict[str, Any]:
    enabled = _env_enabled("API_FOOTBALL_ENABLED", True)
    configured = bool(os.getenv("API_FOOTBALL_KEY"))
    if not enabled:
        status = "disabled"
        message = "API-Football 已通过 API_FOOTBALL_ENABLED 关闭。"
    elif configured:
        status = "configured"
        message = "备用商业细节源已配置，可读取赛果细节、阵容、技术统计、榜单与伤停。"
    else:
        status = "standby"
        message = "备用商业细节源未启用；当前不影响公开伤停与赛果源流程。"
    return {
        "id": "api_football_match_injuries",
        "label": "API-Football",
        "provider": "API-SPORTS",
        "status": status,
        "source": "api_football",
        "source_url": API_FOOTBALL_DOCS_URL,
        "role": "赛果细节/阵容/技术统计/伤停",
        "scope": "作为可选备用细节源；公开源与本地复核优先展示",
        "weight": "verified_input",
        "last_updated": _now_iso() if configured and enabled else None,
        "message": message,
    }


def _sportmonks_source() -> Dict[str, Any]:
    enabled = _env_enabled("SPORTMONKS_ENABLED", True)
    configured = bool(os.getenv("SPORTMONKS_TOKEN") or os.getenv("SPORTMONKS_API_TOKEN"))
    if not enabled:
        status = "disabled"
        message = "SportMonks 已通过 SPORTMONKS_ENABLED 关闭。"
    elif configured:
        status = "configured"
        message = "备用商业伤停源已配置，可读取球队 sidelined 伤停与停赛信息。"
    else:
        status = "standby"
        message = "备用商业伤停源未启用；公开伤停页与本地复核继续工作。"
    return {
        "id": "sportmonks_sidelined",
        "label": "SportMonks 伤停",
        "provider": "SportMonks Football API v3",
        "status": status,
        "source": "sportmonks_sidelined",
        "source_url": SPORTMONKS_SIDELINED_URL,
        "docs_url": SPORTMONKS_DOCS_URL,
        "role": "赛前伤停/停赛兜底",
        "scope": "作为可选备用伤停源；公开伤停页与本地复核优先展示",
        "weight": "verified_input_backup",
        "last_updated": _now_iso() if configured and enabled else None,
        "message": message,
    }


def _transfermarkt_injury_source() -> Dict[str, Any]:
    enabled = _env_enabled("PUBLIC_INJURY_SOURCES_ENABLED", True)
    return {
        "id": "transfermarkt_public_injuries",
        "label": "Transfermarkt 伤停",
        "provider": "Transfermarkt",
        "status": "connected" if enabled else "disabled",
        "source": "transfermarkt_public",
        "source_url": TRANSFERMARKT_PARTICIPANTS_URL,
        "role": "国家队伤病/停赛/停赛风险",
        "scope": "按 48 队公开 participants 索引生成各队 suspensions and injuries 页面，赛前低权重提示并可触发人工复核",
        "weight": "matched_only",
        "last_updated": _now_iso() if enabled else None,
        "message": "已接入 48 队公开伤停页索引；当前缺阵会进入伤停提示，关键缺阵仍需人工复核。",
    }


def _espn_injury_tracker_source() -> Dict[str, Any]:
    return {
        "id": "espn_worldcup_injury_tracker",
        "label": "ESPN 伤停追踪",
        "provider": "ESPN",
        "status": "reference",
        "source": "espn_worldcup_injury_tracker",
        "source_url": ESPN_INJURY_TRACKER_URL,
        "role": "世界杯重点球员伤情追踪",
        "scope": "用于交叉核验球星缺阵、恢复与赛前新闻，不直接覆盖本地人工复核",
        "weight": "reference_only",
        "last_updated": _now_iso(),
        "message": "已加入公开参考源清单，用于人工复核和赛前观点补强。",
    }


def _sports_mole_team_news_source() -> Dict[str, Any]:
    return {
        "id": "sports_mole_team_news",
        "label": "Sports Mole 阵容消息",
        "provider": "Sports Mole",
        "status": "reference",
        "source": "sports_mole_team_news",
        "source_url": SPORTS_MOLE_TEAM_NEWS_URL,
        "role": "单场 team news / 预测首发交叉验证",
        "scope": "有单场预览页时读取 injury、suspension list 与 predicted XIs 作为赛前人工复核参考",
        "weight": "reference_only",
        "last_updated": _now_iso(),
        "message": "已加入公开参考源清单，适合临近比赛日补充首发与伤停观点。",
    }


def _historical_injury_source() -> Dict[str, Any]:
    return {
        "id": "transfermarkt_historical_injury_csv",
        "label": "历史伤病库",
        "provider": "salimt/football-datasets",
        "status": "reference",
        "source": "transfermarkt_player_injuries_csv",
        "source_url": TRANSFERMARKT_HISTORICAL_INJURIES_URL,
        "role": "历史伤病风险基线",
        "scope": "只用于球员伤病倾向背景，不作为当前缺阵或停赛事实",
        "weight": "reference_only",
        "last_updated": _now_iso(),
        "message": "已登记 GitHub 开源历史伤病 CSV；只做风险背景，避免误伤当前名单。",
    }


def _team_memory_source() -> Dict[str, Any]:
    return {
        "id": "team_feature_library",
        "label": "球队特征库",
        "provider": "World Cup Lens local model memory",
        "status": "connected",
        "source": "team_profiles.json",
        "source_url": "",
        "role": "近期状态/纪律/复盘注意事项",
        "scope": "默认启用，只使用目标比赛之前的世界杯样本与世界杯前正式赛样本，低权重修正 xG 和平局倾向",
        "weight": "low_default_on",
        "last_updated": _now_iso(),
        "message": "默认参与预测；不是页面手动开关，复盘页可看 A/B 命中对比。",
    }


def _squad_source() -> Dict[str, Any]:
    return {
        "id": "official_26_squads",
        "label": "官方26人名单",
        "provider": "FIFA squad list mirror",
        "status": "connected",
        "source": "team_squads.json",
        "source_url": WC_SQUADS_SOURCE_URL,
        "role": "完整阵容/首发候选池",
        "scope": "首发预测从官方 26 人候选池生成；官方临场首发或 API 阵容接入后覆盖",
        "weight": "candidate_pool",
        "last_updated": _now_iso(),
        "message": "已生成 48 队官方候选名单，避免退役或未入选球员进入首发预测。",
    }


def _fifa_ranking_source() -> Dict[str, Any]:
    return {
        "id": "fifa_ranking_snapshot",
        "label": "FIFA排名快照",
        "provider": "FIFA",
        "status": "connected",
        "source": "fifa_ranking_snapshot",
        "source_url": FIFA_RANKING_URL,
        "role": "基础实力修正",
        "scope": "2026-06-11 官方排名快照；下次官方发布后再更新",
        "weight": "baseline_factor",
        "last_updated": "2026-06-11",
        "message": "作为 Elo 之外的基础实力层，不替代近期状态。",
    }


def build_public_data_sources(market_odds: Mapping[str, Any] | None = None) -> list[Dict[str, Any]]:
    """Return the external-data contract shown on prediction pages.

    These records describe source readiness and model role. Reference sources are
    intentionally not treated as hard calibration inputs for a current match.
    """
    espn_enabled = _env_enabled("ESPN_SCOREBOARD_ENABLED", True)
    return [
        _realtime_market_source(market_odds),
        {
            "id": "espn_public_results_events",
            "label": "ESPN 赛果事件",
            "provider": "ESPN scoreboard",
            "status": "connected" if espn_enabled else "disabled",
            "source": "espn_scoreboard",
            "source_url": ESPN_SCOREBOARD_URL,
            "role": "公开赛果/事件回填",
            "scope": "匹配到比赛后写入比分、进球、牌面等事件；赛前只提示状态",
            "weight": "post_match_first",
            "last_updated": _now_iso() if espn_enabled else None,
            "message": "已接入 live feed 合并管线。" if espn_enabled else "ESPN scoreboard 已关闭。",
        },
        {
            "id": "openfootball_schedule",
            "label": "openfootball",
            "provider": "openfootball/worldcup",
            "status": "reference",
            "source": "openfootball_worldcup",
            "source_url": OPENFOOTBALL_WORLDCUP_URL,
            "role": "赛程与赛事结构参考",
            "scope": "用于赛程、阶段、对阵结构交叉校验；本项目赛程仍以本地 2026 schedule 为主",
            "weight": "reference_only",
            "last_updated": _now_iso(),
            "message": "已纳入公开源清单，作为赛程交叉校验参考。",
        },
        _football_data_source(market_odds),
        _transfermarkt_injury_source(),
        _espn_injury_tracker_source(),
        _sports_mole_team_news_source(),
        _historical_injury_source(),
        _api_football_source(),
        _sportmonks_source(),
        _squad_source(),
        _team_memory_source(),
        _fifa_ranking_source(),
        {
            "id": "statsbomb_open_data",
            "label": "StatsBomb Open Data",
            "provider": "StatsBomb",
            "status": "reference",
            "source": "statsbomb_open_data",
            "source_url": STATSBOMB_OPEN_DATA_URL,
            "role": "历史事件样本",
            "scope": "用于理解公开事件数据结构和历史风格样本，不直接硬改 2026 单场概率",
            "weight": "reference_only",
            "last_updated": _now_iso(),
            "message": "已纳入公开事件样本参考源。",
        },
    ]
