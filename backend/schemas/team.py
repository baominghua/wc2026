from pydantic import BaseModel
from typing import Any, List, Optional

class TeamResponse(BaseModel):
    id: int
    name: str
    code: str
    group: str
    fifa_rank: int
    elo_rating: int

class TeamDetail(BaseModel):
    id: int
    name: str
    code: str
    group: str
    fifa_rank: int
    elo_rating: int
    coach: str
    key_players: List[str]
    world_cup_titles: int
    recent_form: List[str]
    xg_for: float
    xg_against: float
    squad: Optional[dict[str, Any]] = None
    feature_profile: Optional[dict[str, Any]] = None
