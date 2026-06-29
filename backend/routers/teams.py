from __future__ import annotations

import re
import json
from pathlib import Path
from typing import Any, List

from fastapi import APIRouter, HTTPException

from schemas.team import TeamDetail, TeamResponse
from services.prediction_model import TEAM_PROFILES
from services.live_match_feed import merge_live_matches
from services.pre_world_cup_history import load_pre_world_cup_official_matches
from services.team_feature_library import load_team_profile_store, sync_team_profile_store
from services.team_squads import get_team_squad, squad_player_projections
from routers.matches import mock_matches


router = APIRouter()
ROOT = Path(__file__).resolve().parents[2]
BACKEND_TEAMS_PATH = Path(__file__).resolve().parent.parent / "data" / "teams.json"
FRONTEND_TEAMS_PATH = ROOT / "frontend" / "src" / "services" / "wc2026-data.ts"


def _frontend_teams() -> list[dict[str, Any]]:
    if BACKEND_TEAMS_PATH.exists():
        with BACKEND_TEAMS_PATH.open("r", encoding="utf-8") as file:
            return json.load(file)
    if not FRONTEND_TEAMS_PATH.exists():
        return []
    text = FRONTEND_TEAMS_PATH.read_text(encoding="utf-8")
    teams: list[dict[str, Any]] = []
    pattern = re.compile(
        r"\{\s*id:\s*(\d+),\s*name:\s*'([^']+)',\s*code:\s*'([A-Z]+)',\s*group:\s*'([A-Z])',\s*"
        r"fifa_rank:\s*(\d+),\s*elo_rating:\s*(\d+)",
    )
    for match in pattern.finditer(text):
        teams.append(
            {
                "id": int(match.group(1)),
                "name": match.group(2),
                "code": match.group(3),
                "group": match.group(4),
                "fifa_rank": int(match.group(5)),
                "elo_rating": int(match.group(6)),
            }
        )
    return teams


def _fallback_feature_profile(team_name: str) -> dict[str, Any]:
    return {
        "team": team_name,
        "sample_matches": 0,
        "source": "pending_team_feature_sample",
        "source_label": "待补正式赛样本",
        "form_state": {
            "score": None,
            "avg_points": None,
            "avg_goal_diff": None,
            "avg_goals_for": None,
            "avg_goals_against": None,
            "latest_score": None,
        },
        "discipline_state": {
            "yellow_cards_for": None,
            "red_cards_for": None,
            "risk": "pending",
        },
        "volatility_state": {
            "label": "pending",
        },
        "tactical_tags": ["pending_sample"],
        "review_lessons": [],
        "next_prediction_notes": [
            f"{team_name} 暂无足够正式赛样本，预测时仅低权重保留模型默认画像。",
        ],
    }


def _team_feature_profile(team_name: str) -> dict[str, Any]:
    store = load_team_profile_store()
    profiles = store.get("profiles") if isinstance(store, dict) else {}
    profile = profiles.get(team_name) if isinstance(profiles, dict) else None
    if isinstance(profile, dict):
        return profile

    live_matches = [*load_pre_world_cup_official_matches(), *merge_live_matches(mock_matches)]
    refreshed = sync_team_profile_store(live_matches)
    refreshed_profiles = refreshed.get("profiles") if isinstance(refreshed, dict) else {}
    refreshed_profile = refreshed_profiles.get(team_name) if isinstance(refreshed_profiles, dict) else None
    if isinstance(refreshed_profile, dict):
        return refreshed_profile
    return _fallback_feature_profile(team_name)


@router.get("/", response_model=List[TeamResponse])
async def get_teams(group: str | None = None):
    teams = _frontend_teams()
    if group:
        return [team for team in teams if team["group"] == group.upper()]
    return teams


@router.get("/groups/{group_id}", response_model=List[TeamResponse])
async def get_group_teams(group_id: str):
    teams = [team for team in _frontend_teams() if team["group"] == group_id.upper()]
    if not teams:
        raise HTTPException(status_code=404, detail="Group not found")
    return teams


@router.get("/{team_id}", response_model=TeamDetail)
async def get_team_detail(team_id: int):
    team = next((item for item in _frontend_teams() if item["id"] == team_id), None)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    profile = TEAM_PROFILES.get(team["name"])
    squad = get_team_squad(team["code"])
    projections = squad_player_projections(team["code"])
    key_players = [str(player["name"]) for player in projections[:4]]
    if not key_players and squad:
        key_players = [str(player["name"]) for player in squad.get("players", [])[:4]]

    return {
        **team,
        "coach": str(squad.get("coach") if squad else ""),
        "key_players": key_players,
        "world_cup_titles": int(profile.titles if profile else 0),
        "recent_form": [],
        "xg_for": 0.0,
        "xg_against": 0.0,
        "squad": squad,
        "feature_profile": _team_feature_profile(team["name"]),
    }
