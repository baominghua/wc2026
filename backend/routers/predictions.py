from fastapi import APIRouter, HTTPException
from typing import Optional
from pydantic import BaseModel
from services.prediction_model import predict_match
from services.prediction_snapshot_store import load_prediction_snapshots, save_pre_match_prediction
from services.pre_world_cup_history import load_pre_world_cup_official_matches
from services.review_engine import build_prediction_audit, build_review_adjustment
from services.team_feature_library import build_match_feature_adjustment, sync_team_profile_store
from services.live_match_feed import merge_live_matches
from services.match_stage import infer_effective_stage, is_knockout_stage, normalize_match_stage
from services.wc2026_skill_audit import build_skill_audit
from services.injury_feed import get_match_injury_feed
from routers.matches import mock_matches

router = APIRouter()


class PredictionRequest(BaseModel):
    match_id: Optional[int] = None
    home_team: str
    away_team: str
    venue: Optional[str] = None
    weather: Optional[str] = None
    model_type: Optional[str] = "form_weighted"  # baseline | form_weighted | monte_carlo
    advantage_team: Optional[str] = "none"  # home | away | none
    advantage_level: Optional[str] = "none"  # full | half | none
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


def _player_list(items: list[str] | None, limit: int = 4) -> str:
    values = [str(item).strip() for item in (items or []) if str(item).strip()]
    if not values:
        return ""
    suffix = "等" if len(values) > limit else ""
    return "、".join(values[:limit]) + suffix


def _injury_factor_lines(injury_feed: dict | None) -> list[str]:
    if not isinstance(injury_feed, dict):
        return []
    teams = injury_feed.get("teams") if isinstance(injury_feed.get("teams"), dict) else {}
    lines: list[str] = []
    for side in ("home", "away"):
        status = teams.get(side)
        if not isinstance(status, dict):
            continue
        team = str(status.get("team") or ("主队" if side == "home" else "客队"))
        unavailable = _player_list(status.get("unavailable_players"))
        doubtful = _player_list(status.get("doubtful_players"))
        card_risk = _player_list(status.get("card_risk_players"))
        pieces = []
        if unavailable:
            pieces.append(f"缺阵/停赛 {unavailable}")
        if doubtful:
            pieces.append(f"成疑 {doubtful}")
        if card_risk:
            pieces.append(f"停赛风险 {card_risk}")
        if pieces:
            lines.append(f"伤停分析: {team} {'；'.join(pieces)}，已纳入赛前风险复核")
    if not lines and injury_feed.get("status") in {"connected", "stale"}:
        lines.append("伤停分析: 公开源暂无具体缺阵、成疑或停赛风险记录，仅保留临场复核")
    return lines


@router.post("/predict")
async def predict_match_result(request: PredictionRequest):
    """预测单场比赛结果 - 支持三种模型"""
    try:
        live_matches = [*load_pre_world_cup_official_matches(), *merge_live_matches(mock_matches)]
        selected_match = None
        if request.match_id is not None:
            selected_match = next((match for match in live_matches if match.get("id") == request.match_id), None)
        if selected_match is None:
            selected_match = next(
                (
                    match for match in live_matches
                    if match.get("home_team") == request.home_team and match.get("away_team") == request.away_team
                ),
                None,
            )
        if selected_match:
            selected_match = normalize_match_stage(selected_match)
            if not infer_effective_stage(selected_match) and request.stage:
                selected_match = normalize_match_stage({**selected_match, "stage": request.stage})
        profile_store = (
            sync_team_profile_store(live_matches, before=selected_match.get("match_date"))
            if selected_match
            else None
        )
        review_adjustment = build_review_adjustment(selected_match, live_matches) if selected_match else None
        team_feature_adjustment = (
            build_match_feature_adjustment(selected_match, live_matches, profile_store=profile_store)
            if selected_match
            else None
        )
        effective_round = selected_match.get("round") if selected_match and selected_match.get("round") is not None else request.match_round
        effective_stage = infer_effective_stage(selected_match) if selected_match else None
        if not effective_stage and is_knockout_stage(request.stage):
            effective_stage = request.stage
        if not effective_stage and request.is_knockout:
            effective_stage = request.stage if is_knockout_stage(request.stage) else "Round of 32"
        effective_is_knockout = bool(request.is_knockout or effective_stage)
        injury_feed = get_match_injury_feed(
            request.home_team,
            request.away_team,
            selected_match.get("match_date") if selected_match else None,
        )
        injury_auto_apply = injury_feed.get("auto_apply") if isinstance(injury_feed, dict) else {}
        home_key_absence = bool(request.home_key_absence) or bool(injury_auto_apply.get("home_key_absence"))
        away_key_absence = bool(request.away_key_absence) or bool(injury_auto_apply.get("away_key_absence"))

        result = predict_match(
            home_team=request.home_team,
            away_team=request.away_team,
            venue=request.venue,
            weather=request.weather,
            model_type=request.model_type,
            advantage_team=request.advantage_team,
            advantage_level=request.advantage_level,
            is_knockout=effective_is_knockout,
            high_press=bool(request.high_press),
            home_key_absence=home_key_absence,
            away_key_absence=away_key_absence,
            home_fatigue=bool(request.home_fatigue),
            away_fatigue=bool(request.away_fatigue),
            match_round=effective_round,
            stage=effective_stage,
            venue_factor=request.venue_factor,
            force_neutral=bool(request.force_neutral),
            review_adjustment=review_adjustment,
            team_feature_adjustment=team_feature_adjustment,
            match_context=selected_match,
        )
        if selected_match and request.match_id is not None:
            scenario_settings = request.model_dump() if hasattr(request, "model_dump") else request.dict()
            save_pre_match_prediction(selected_match, result, scenario_settings=scenario_settings)
        match_context = selected_match or (request.model_dump() if hasattr(request, "model_dump") else request.dict())
        result["injury_feed"] = injury_feed
        injury_lines = _injury_factor_lines(injury_feed)
        if injury_lines:
            existing_factors = result.get("factors") if isinstance(result.get("factors"), list) else []
            result["factors"] = [*existing_factors, *injury_lines]
        result["skill_audit"] = build_skill_audit(result, match=match_context)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{match_id}")
async def get_prediction_history(match_id: int):
    """获取比赛的历史预测记录"""
    return {
        "match_id": match_id,
        "predictions": [
            {"timestamp": "2026-06-01T10:00:00Z", "home_win": 0.42, "draw": 0.25, "away_win": 0.33, "model": "baseline"},
            {"timestamp": "2026-06-05T10:00:00Z", "home_win": 0.45, "draw": 0.23, "away_win": 0.32, "model": "form_weighted"},
            {"timestamp": "2026-06-10T10:00:00Z", "home_win": 0.47, "draw": 0.22, "away_win": 0.31, "model": "monte_carlo"},
        ]
    }


@router.get("/model-performance")
async def get_model_performance():
    """获取基于赛前快照的真实模型表现，不返回硬编码命中率。"""
    audit = build_prediction_audit(
        merge_live_matches(mock_matches),
        predictions_by_match=load_prediction_snapshots(),
    )
    summary = audit["summary"]
    accuracy = summary.get("outcome_top1_accuracy", 0.0)
    precision = summary.get("score_top1_accuracy", 0.0)
    recall = summary.get("outcome_top2_accuracy", 0.0)
    models = {
        "form_weighted": {
            "accuracy": accuracy,
            "precision": precision,
            "recall": recall,
        }
    }
    return {
        "model_name": "美加墨世界杯AI预测模型 26.5",
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "models": models,
        "last_updated": audit["generated_at"],
        "total_predictions": summary.get("reviewed_matches", 0),
        "correct_predictions": summary.get("outcome_top1_hits", 0),
        "missing_prediction_count": summary.get("missing_prediction_count", 0),
        "source_policy": audit["source_policy"],
    }
