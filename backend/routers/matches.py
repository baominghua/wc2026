from fastapi import APIRouter, HTTPException
from typing import List, Optional
from schemas.match import MatchResponse, MatchDetail
from services.live_match_feed import merge_live_matches
from services.schedule import load_schedule_matches

router = APIRouter()

# 模拟比赛数据
mock_matches = [
    {
        "id": 1,
        "home_team": "墨西哥",
        "away_team": "南非",
        "group": "A",
        "round": 1,
        "match_date": "2026-06-12T03:00:00+08:00",
        "venue": "阿兹特克体育场，墨西哥城",
        "status": "completed",
        "home_score": 2,
        "away_score": 0
    },
    {
        "id": 2,
        "home_team": "韩国",
        "away_team": "捷克",
        "group": "A",
        "round": 1,
        "match_date": "2026-06-12T10:00:00+08:00",
        "venue": "阿克伦体育场，萨波潘",
        "status": "completed",
        "home_score": 2,
        "away_score": 1
    },
    {
        "id": 3,
        "home_team": "加拿大",
        "away_team": "波黑",
        "group": "B",
        "round": 1,
        "match_date": "2026-06-13T03:00:00+08:00",
        "venue": "BMO球场，多伦多",
        "status": "upcoming",
        "home_score": None,
        "away_score": None
    },
    {
        "id": 4,
        "home_team": "美国",
        "away_team": "巴拉圭",
        "group": "D",
        "round": 1,
        "match_date": "2026-06-13T09:00:00+08:00",
        "venue": "SoFi体育场，洛杉矶",
        "status": "upcoming",
        "home_score": None,
        "away_score": None
    },
    {
        "id": 5,
        "home_team": "卡塔尔",
        "away_team": "瑞士",
        "group": "B",
        "round": 1,
        "match_date": "2026-06-14T03:00:00+08:00",
        "venue": "李维斯体育场，旧金山",
        "status": "upcoming",
        "home_score": None,
        "away_score": None
    },
    {
        "id": 6,
        "home_team": "巴西",
        "away_team": "摩洛哥",
        "group": "C",
        "round": 1,
        "match_date": "2026-06-14T06:00:00+08:00",
        "venue": "大都会人寿体育场，纽约",
        "status": "upcoming",
        "home_score": None,
        "away_score": None
    },
    {
        "id": 7,
        "home_team": "海地",
        "away_team": "苏格兰",
        "group": "C",
        "round": 1,
        "match_date": "2026-06-14T09:00:00+08:00",
        "venue": "吉列体育场，波士顿",
        "status": "upcoming",
        "home_score": None,
        "away_score": None
    },
    {
        "id": 8,
        "home_team": "澳大利亚",
        "away_team": "土耳其",
        "group": "D",
        "round": 1,
        "match_date": "2026-06-14T12:00:00+08:00",
        "venue": "BC广场，温哥华",
        "status": "upcoming",
        "home_score": None,
        "away_score": None
    }
]

schedule_matches = load_schedule_matches()
if schedule_matches:
    mock_matches = schedule_matches

@router.get("/", response_model=List[MatchResponse])
async def get_matches(group: str = None, status: str = None):
    """获取比赛列表，可选按分组和状态筛选"""
    results = merge_live_matches(mock_matches)
    if group:
        results = [m for m in results if m.get("group") == group]
    if status:
        results = [m for m in results if m["status"] == status]
    return results

@router.get("/upcoming")
async def get_upcoming_matches(limit: int = 5):
    """获取即将进行的比赛"""
    live_matches = merge_live_matches(mock_matches)
    upcoming = [m for m in live_matches if m.get("status") == "upcoming"]
    return sorted(upcoming, key=lambda x: x["match_date"])[:limit]

@router.get("/{match_id}", response_model=MatchDetail)
async def get_match_detail(match_id: int):
    """获取比赛详情"""
    live_matches = merge_live_matches(mock_matches)
    match = next((m for m in live_matches if m["id"] == match_id), None)
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    
    # 模拟详细数据
    match_detail = {
        **match,
        "weather": match.get("weather", "待官方确认"),
        "attendance": match.get("report", {}).get("attendance") if match.get("report") else None,
        "referee": match.get("report", {}).get("referee") if match.get("report") else None,
        "home_formation": match.get("home_formation"),
        "away_formation": match.get("away_formation"),
        "home_xg": match.get("report", {}).get("stats", {}).get("xg_home") if match.get("report") else None,
        "away_xg": match.get("report", {}).get("stats", {}).get("xg_away") if match.get("report") else None,
        "home_possession": match.get("report", {}).get("stats", {}).get("possession_home") if match.get("report") else None,
        "away_possession": match.get("report", {}).get("stats", {}).get("possession_away") if match.get("report") else None
    }
    return match_detail
