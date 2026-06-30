from pydantic import BaseModel
from typing import Any, Optional
from datetime import datetime

class MatchResponse(BaseModel):
    id: int
    home_team: str
    away_team: str
    group: Optional[str] = None
    match_date: datetime
    venue: str
    status: str
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    round: Optional[int] = None
    stage: Optional[str] = None
    report: Optional[dict[str, Any]] = None
    data_status: Optional[str] = None
    data_message: Optional[str] = None
    fixture_status: Optional[str] = None
    fixture_message: Optional[str] = None
    live_source: Optional[str] = None
    last_updated: Optional[str] = None

class MatchDetail(BaseModel):
    id: int
    home_team: str
    away_team: str
    group: Optional[str] = None
    match_date: datetime
    venue: str
    status: str
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    round: Optional[int] = None
    stage: Optional[str] = None
    report: Optional[dict[str, Any]] = None
    data_status: Optional[str] = None
    data_message: Optional[str] = None
    fixture_status: Optional[str] = None
    fixture_message: Optional[str] = None
    live_source: Optional[str] = None
    last_updated: Optional[str] = None
    weather: Optional[str] = None
    attendance: Optional[int] = None
    referee: Optional[str] = None
    home_formation: Optional[str] = None
    away_formation: Optional[str] = None
    home_xg: Optional[float] = None
    away_xg: Optional[float] = None
    home_possession: Optional[float] = None
    away_possession: Optional[float] = None
