from fastapi import APIRouter

from routers.matches import mock_matches
from services.live_match_feed import get_live_sync_status, refresh_live_cache

router = APIRouter()


@router.get("/status")
async def get_live_status():
    """查看比赛实时数据同步状态。"""
    return get_live_sync_status(mock_matches)


@router.post("/sync")
async def sync_live_data():
    """手动触发一次实时数据同步。"""
    status = refresh_live_cache()
    status["pending_results"] = get_live_sync_status(mock_matches).get("pending_results", [])
    status["message"] = f"{status.get('message', '同步完成')}；已手动触发"
    return status
