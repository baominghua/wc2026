from fastapi import APIRouter
from typing import List

from routers.matches import mock_matches
from services.api_football import api_football_enabled, fetch_api_football_leaderboards
from services.live_match_feed import get_live_sync_status, merge_live_matches
from services.player_leaderboards import build_player_leaderboards

router = APIRouter()

# 模拟球员数据
mock_players = [
    {"id": 1, "name": "Lionel Messi", "team": "Argentina", "position": "FW", "jersey": 10, "age": 38, "goals": 13, "assists": 8},
    {"id": 2, "name": "Kylian Mbappé", "team": "France", "position": "FW", "jersey": 9, "age": 27, "goals": 8, "assists": 4},
    {"id": 3, "name": "Neymar Jr", "team": "Brazil", "position": "FW", "jersey": 10, "age": 34, "goals": 7, "assists": 6},
]

@router.get("/", response_model=List[dict])
async def get_players(team: str = None):
    """获取球员列表，可选按球队筛选"""
    if team:
        return [p for p in mock_players if p["team"] == team]
    return mock_players

@router.get("/leaderboards/2026")
async def get_2026_player_leaderboards():
    """Build real-time 2026 player goals/assists/cards from configured data providers."""
    live_status = get_live_sync_status(mock_matches)
    if api_football_enabled():
        try:
            leaderboards = fetch_api_football_leaderboards()
            leaderboards["live_status"] = {
                **live_status,
                "player_stats_status": "connected",
                "player_stats_source": "api_football",
                "player_stats_message": "球员射手、助攻和红黄牌榜来自 API-Football 供应商接口",
            }
            return leaderboards
        except Exception as exc:
            live_status = {
                **live_status,
                "player_stats_status": "error",
                "player_stats_source": "api_football",
                "player_stats_message": f"API-Football 球员榜读取失败: {exc}",
            }

    live_matches = merge_live_matches(mock_matches)
    leaderboards = build_player_leaderboards(live_matches)
    leaderboards["live_status"] = {
        **live_status,
        "player_stats_status": "event_feed",
        "player_stats_source": live_status.get("source") or "event_feed",
        "player_stats_message": "未配置供应商球员榜接口，仅统计自动比赛事件中包含的射手/助攻/红黄牌",
    }
    return leaderboards

@router.get("/{player_id}")
async def get_player_detail(player_id: int):
    """获取球员详情"""
    player = next((p for p in mock_players if p["id"] == player_id), None)
    if not player:
        return {"error": "Player not found"}
    return player
