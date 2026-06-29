from fastapi import APIRouter

from services.injury_feed import get_match_injury_feed

router = APIRouter()


@router.get("/match")
async def get_match_injuries(home_team: str, away_team: str, match_date: str | None = None):
    """获取单场比赛伤停信息。

    合并公开伤停页、可选供应商源和本地人工复核 JSON；未知信息不会自动计入模型。
    """
    return get_match_injury_feed(home_team=home_team, away_team=away_team, match_date=match_date)
