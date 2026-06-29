from fastapi import APIRouter, HTTPException

from routers.matches import mock_matches
from services.live_match_feed import merge_live_matches
from services.pre_world_cup_history import load_pre_world_cup_official_matches
from services.tournament_projection import build_tournament_projection


router = APIRouter()


@router.get("/projection")
async def get_tournament_projection(simulate: bool = True):
    """Build qualification and knockout projections from live scores plus model predictions."""
    try:
        live_matches = [*load_pre_world_cup_official_matches(), *merge_live_matches(mock_matches)]
        return build_tournament_projection(live_matches, simulate=simulate)
    except Exception as exc:  # pragma: no cover - defensive API boundary
        raise HTTPException(status_code=500, detail=f"Tournament projection failed: {exc}") from exc
