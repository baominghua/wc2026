from __future__ import annotations

import csv
from io import StringIO
from typing import Any, Dict, List, Mapping, Optional

from fastapi import APIRouter, HTTPException, Response

from routers.matches import mock_matches
from services.live_match_feed import merge_live_matches
from services.pre_world_cup_history import load_pre_world_cup_official_matches
from services.prediction_model import predict_match
from services.prediction_snapshot_store import load_prediction_snapshots
from services.review_engine import build_review_adjustment
from services.review_engine import build_prediction_audit, generate_match_review
from services.team_feature_library import build_match_feature_adjustment, sync_team_profile_store
from services.wc2026_skill_audit import build_skill_audit


router = APIRouter()


def _matches() -> List[Dict[str, Any]]:
    return [*load_pre_world_cup_official_matches(), *merge_live_matches(mock_matches)]


def _current_model_prediction(
    match: Dict[str, Any],
    *,
    use_profile: bool = True,
    live_matches: Optional[List[Dict[str, Any]]] = None,
    profile_store: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    live_matches = live_matches or _matches()
    team_feature_adjustment = (
        build_match_feature_adjustment(match, live_matches, profile_store=profile_store)
        if use_profile
        else None
    )
    result = predict_match(
        home_team=match["home_team"],
        away_team=match["away_team"],
        venue=match.get("venue"),
        model_type="form_weighted",
        is_knockout=bool(match.get("stage")),
        match_round=match.get("round"),
        stage=match.get("stage"),
        force_neutral=False,
        review_adjustment=build_review_adjustment(match, live_matches),
        team_feature_adjustment=team_feature_adjustment,
    )
    result["skill_audit"] = build_skill_audit(result, match=match)
    return result


PROFILE_COMPARISON_KEYS = [
    "wdl_accuracy",
    "score_pick1_accuracy",
    "score_total_accuracy",
    "total_goals_range_accuracy",
    "btts_accuracy",
]


def _profile_comparison(with_profile: Mapping[str, Any], without_profile: Mapping[str, Any]) -> Dict[str, Any]:
    with_summary = with_profile.get("summary") if isinstance(with_profile.get("summary"), Mapping) else {}
    without_summary = without_profile.get("summary") if isinstance(without_profile.get("summary"), Mapping) else {}

    def pick(summary: Mapping[str, Any]) -> Dict[str, Any]:
        payload = {"reviewed_matches": summary.get("reviewed_matches", 0)}
        for key in PROFILE_COMPARISON_KEYS:
            payload[key] = summary.get(key, 0.0)
        return payload

    with_payload = pick(with_summary)
    without_payload = pick(without_summary)
    delta = {
        key: round(float(with_payload.get(key, 0.0)) - float(without_payload.get(key, 0.0)), 4)
        for key in PROFILE_COMPARISON_KEYS
    }
    delta["reviewed_matches"] = with_payload.get("reviewed_matches", 0)
    return {
        "without_profile": without_payload,
        "with_profile": with_payload,
        "delta": delta,
    }


@router.get("/")
async def get_prediction_reviews():
    matches = _matches()
    team_profiles = sync_team_profile_store(matches)
    audit = build_prediction_audit(matches, predictions_by_match=load_prediction_snapshots())
    audit["team_profiles"] = team_profiles
    return audit


@router.get("/current-model-backtest")
async def get_current_model_backtest():
    matches = _matches()
    team_profiles = sync_team_profile_store(matches)
    with_profile = build_prediction_audit(
        matches,
        predictor=lambda match: _current_model_prediction(
            match,
            use_profile=True,
            live_matches=matches,
            profile_store=team_profiles,
        ),
        evaluation_mode="current_model_backtest",
        source_policy="当前模型回测：使用现有模型参数重跑已完赛比赛，用于评估模型结构；它不是赛前真实命中率。各项命中率严格按Top N候选是否包含真实结果计算。",
    )


    without_profile = build_prediction_audit(
        matches,
        predictor=lambda match: _current_model_prediction(
            match,
            use_profile=False,
            live_matches=matches,
            profile_store=team_profiles,
        ),
        evaluation_mode="current_model_backtest_without_profile",
        source_policy="当前模型回测基线：关闭球队特征库，只保留原有复盘和模型层。",
    )
    with_profile["team_profiles"] = team_profiles
    with_profile["profile_comparison"] = _profile_comparison(with_profile, without_profile)
    return with_profile


@router.get("/export.csv")
async def export_prediction_reviews_csv():
    audit = build_prediction_audit(_matches(), predictions_by_match=load_prediction_snapshots())
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "match_id",
            "home_team",
            "away_team",
            "actual_score",
            "predicted_score",
            "wdl_hit",
            "score_pick1",
            "score_pick2",
            "score_pick3",
            "upset_score_hit",
            "score_total_hit",
            "total_goals_range",
            "total_goals_range_hit",
            "btts_view",
            "btts_hit",
            "main_variance",
        ]
    )
    for row in audit["rows"]:
        writer.writerow(
            [
                row["match_id"],
                row["home_team"],
                row["away_team"],
                row["actual"]["score"],
                row["prediction"]["score"],
                row["accuracy"].get("wdl_hit"),
                row["accuracy"].get("score_pick1"),
                row["accuracy"].get("score_pick2"),
                row["accuracy"].get("score_pick3"),
                row["accuracy"].get("upset_score_hit"),
                row["accuracy"].get("score_pool_hit"),
                row["prediction"].get("total_goals_range"),
                row["accuracy"].get("total_goals_range_hit"),
                row["prediction"].get("btts_view"),
                row["accuracy"].get("btts_hit"),
                row["variance_notes"][0]["title"] if row.get("variance_notes") else "",
            ]
        )
    return Response(
        content=buffer.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="wc2026-prediction-review.csv"'},
    )


@router.get("/{match_id}")
async def get_match_review(match_id: int):
    match = next((item for item in _matches() if item.get("id") == match_id), None)
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    if match.get("status") != "completed" or match.get("home_score") is None or match.get("away_score") is None:
        raise HTTPException(status_code=409, detail="Match is not completed yet")
    prediction = load_prediction_snapshots().get(match_id)
    if not prediction:
        raise HTTPException(status_code=409, detail="No pre-match prediction snapshot for this match")
    return generate_match_review(match, prediction)
