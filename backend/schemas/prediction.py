from pydantic import BaseModel
from typing import Optional, List

class PredictionRequest(BaseModel):
    home_team: str
    away_team: str
    venue: Optional[str] = None
    weather: Optional[str] = None
    match_date: Optional[str] = None
    model_type: Optional[str] = "form_weighted"
    advantage_team: Optional[str] = "none"
    advantage_level: Optional[str] = "none"
    is_knockout: Optional[bool] = False
    high_press: Optional[bool] = False
    home_key_absence: Optional[bool] = False
    away_key_absence: Optional[bool] = False
    home_fatigue: Optional[bool] = False
    away_fatigue: Optional[bool] = False
    match_round: Optional[int] = None
    stage: Optional[str] = None
    venue_factor: Optional[str] = "normal"
    force_neutral: Optional[bool] = False

class PredictionResponse(BaseModel):
    home_win_probability: float
    draw_probability: float
    away_win_probability: float
    predicted_score: Optional[str] = None
    possible_scores: Optional[List[dict]] = None
    penalty_probability: Optional[float] = None
    confidence: float
    model_version: str
    model_type: Optional[str] = None
    xg_home: Optional[float] = None
    xg_away: Optional[float] = None
    is_knockout: Optional[bool] = False
    factors: Optional[List[str]] = None
    total_goals_prediction: Optional[dict] = None
    tactical_analysis: Optional[List[dict]] = None
    tactical_matchup: Optional[dict] = None
    lineup_prediction: Optional[List[dict]] = None
    key_players: Optional[List[dict]] = None
    goal_scorer_predictions: Optional[List[dict]] = None
    discipline_analysis: Optional[List[dict]] = None
    market_odds: Optional[dict] = None
    market_calibration: Optional[dict] = None
    upset_prediction: Optional[dict] = None
    set_piece_card_prediction: Optional[dict] = None
    ranking_snapshot: Optional[dict] = None
