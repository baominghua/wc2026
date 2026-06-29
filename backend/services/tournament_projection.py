from __future__ import annotations

import json
import os
import re
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, Tuple

from services.injury_feed import get_match_injury_feed
from services.prediction_model import TEAM_PROFILES, predict_match
from services.review_engine import build_review_adjustment
from services.schedule import load_schedule_matches
from services.team_feature_library import build_match_feature_adjustment, sync_team_profile_store
from services.wc2026_skill_audit import build_skill_audit


Predictor = Callable[[Dict[str, Any], bool, str | None], Dict[str, Any]]

GROUPS = list("ABCDEFGHIJKL")
THIRD_PLACE_COLUMNS = ["1A", "1B", "1D", "1E", "1G", "1I", "1K", "1L"]

KNOCKOUT_DECISION_BASIS = [
    "FIFA 2026淘汰赛规则: 90分钟打平后进行上下半场各15分钟加时赛",
    "加时仍平后进入点球大战；点球仅用于决出晋级方，不改写120分钟比分",
    "90分钟比分沿用当前Elo/FIFA排名/状态权重/xG概率矩阵模型",
    "加时与点球层参考1998-2022世界杯淘汰赛的加时/点球经验先验，并按双方强度差修正",
]

VENUE_CONTEXT_PROFILES = [
    (("azteca", "阿兹特克"), "normal", "high_altitude"),
    (("akron", "阿克伦"), "hot", "normal"),
    (("bbva",), "hot", "normal"),
    (("bc place", "bc广场"), "normal", "indoor"),
    (("bmo", "bmo球场"), "normal", "normal"),
    (("sofi",), "normal", "indoor"),
    (("at&t", "att stadium", "at＆t"), "hot", "indoor"),
    (("metlife", "met life", "大都会人寿"), "normal", "normal"),
    (("mercedes-benz", "mercedes benz", "梅赛德斯"), "normal", "indoor"),
    (("nrg",), "hot", "indoor"),
    (("hard rock", "硬石"), "hot", "normal"),
    (("gillette", "吉列"), "normal", "normal"),
    (("arrowhead", "geha field", "箭头"), "hot", "normal"),
    (("lincoln financial", "林肯金融"), "normal", "normal"),
    (("levi", "李维斯"), "normal", "normal"),
    (("lumen", "流明"), "rain", "normal"),
]

REMOTE_INJURY_ENV_KEYS = ("PUBLIC_INJURY_SOURCES_ENABLED", "API_FOOTBALL_ENABLED", "SPORTMONKS_ENABLED")

ROUND_OF_32_TEMPLATE = [
    (73, "A2", "B2"),
    (74, "E1", "1E"),
    (75, "F1", "C2"),
    (76, "C1", "F2"),
    (77, "I1", "1I"),
    (78, "E2", "I2"),
    (79, "A1", "1A"),
    (80, "L1", "1L"),
    (81, "D1", "1D"),
    (82, "G1", "1G"),
    (83, "K2", "L2"),
    (84, "H1", "J2"),
    (85, "B1", "1B"),
    (86, "J1", "H2"),
    (87, "K1", "1K"),
    (88, "D2", "G2"),
]

KNOCKOUT_TREE = {
    "Round of 16": [
        (89, 74, 77),
        (90, 73, 75),
        (91, 76, 78),
        (92, 79, 80),
        (93, 83, 84),
        (94, 81, 82),
        (95, 86, 88),
        (96, 85, 87),
    ],
    "Quarter-final": [
        (97, 89, 90),
        (98, 93, 94),
        (99, 91, 92),
        (100, 95, 96),
    ],
    "Semi-final": [
        (101, 97, 98),
        (102, 99, 100),
    ],
    "Final": [
        (104, 101, 102),
    ],
}


def _third_place_options_path() -> Path:
    return Path(__file__).resolve().parent.parent / "data" / "fifa2026_third_place_options.json"


def _load_third_place_options() -> Dict[int, Dict[str, str]]:
    with _third_place_options_path().open("r", encoding="utf-8") as file:
        payload = json.load(file)
    columns = payload.get("columns") or THIRD_PLACE_COLUMNS
    options: Dict[int, Dict[str, str]] = {}
    for option_id, values in (payload.get("options") or {}).items():
        if len(values) != len(columns):
            continue
        options[int(option_id)] = {column: str(value) for column, value in zip(columns, values)}
    return options


THIRD_PLACE_OPTIONS = _load_third_place_options()


def _parse_score(score: str) -> Tuple[int, int]:
    match = re.search(r"(\d+)\s*[-:]\s*(\d+)", str(score))
    if not match:
        raise ValueError(f"invalid score: {score!r}")
    return int(match.group(1)), int(match.group(2))


def _is_completed_with_score(match: Dict[str, Any]) -> bool:
    return (
        str(match.get("status") or "").lower() == "completed"
        and match.get("home_score") is not None
        and match.get("away_score") is not None
    )


def _team_rank(team: str) -> int:
    profile = TEAM_PROFILES.get(team)
    return profile.fifa_rank if profile else 999


def _player_list(items: List[str] | None, limit: int = 4) -> str:
    values = [str(item).strip() for item in (items or []) if str(item).strip()]
    if not values:
        return ""
    suffix = "等" if len(values) > limit else ""
    return "、".join(values[:limit]) + suffix


def _injury_factor_lines(injury_feed: Mapping[str, Any] | None) -> List[str]:
    if not isinstance(injury_feed, Mapping):
        return []
    teams = injury_feed.get("teams") if isinstance(injury_feed.get("teams"), Mapping) else {}
    lines: List[str] = []
    for side in ("home", "away"):
        status = teams.get(side)
        if not isinstance(status, Mapping):
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


def _venue_weather_context(match: Mapping[str, Any]) -> Dict[str, str]:
    venue_text = str(match.get("venue") or "").lower()
    for patterns, weather, venue_factor in VENUE_CONTEXT_PROFILES:
        if any(pattern.lower() in venue_text for pattern in patterns):
            return {
                "weather": "normal" if venue_factor == "indoor" else weather,
                "venue_factor": venue_factor,
            }
    return {"weather": "normal", "venue_factor": "normal"}


def _remote_tournament_injury_enabled() -> bool:
    return os.getenv("TOURNAMENT_REMOTE_INJURY_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}


def _tournament_injury_feed(home_team: str, away_team: str, match_date: Any = None) -> Dict[str, Any]:
    if _remote_tournament_injury_enabled():
        return get_match_injury_feed(home_team, away_team, match_date)

    previous = {key: os.environ.get(key) for key in REMOTE_INJURY_ENV_KEYS}
    try:
        for key in REMOTE_INJURY_ENV_KEYS:
            os.environ[key] = "false"
        return get_match_injury_feed(home_team, away_team, match_date)
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _merge_match_context(match: Mapping[str, Any], scheduled: Mapping[str, Any]) -> Dict[str, Any]:
    context = dict(scheduled)
    for key in (
        "home_team",
        "away_team",
        "group",
        "round",
        "stage",
        "home_slot",
        "away_slot",
        "home_source",
        "away_source",
    ):
        value = match.get(key)
        if value not in (None, ""):
            context[key] = value
    return context


def _find_match_context(match: Mapping[str, Any], context_matches: List[Dict[str, Any]]) -> Dict[str, Any]:
    match_id = match.get("id")
    if match_id not in (None, ""):
        match_id_text = str(match_id)
        for candidate in context_matches:
            if str(candidate.get("id")) == match_id_text:
                return _merge_match_context(match, candidate)

    home = match.get("home_team")
    away = match.get("away_team")
    match_date = match.get("match_date")
    for candidate in context_matches:
        if candidate.get("home_team") == home and candidate.get("away_team") == away:
            if not match_date or candidate.get("match_date") == match_date:
                return _merge_match_context(match, candidate)
    return dict(match)


def _contextual_predictor_factory(matches: Iterable[Dict[str, Any]]) -> Predictor:
    context_matches = [dict(match) for match in matches]
    profile_store: Dict[str, Any] | None = None
    injury_cache: Dict[Tuple[str, str, str], Dict[str, Any]] = {}

    def profile_store_for(match_context: Dict[str, Any]) -> Dict[str, Any]:
        nonlocal profile_store
        if profile_store is None:
            profile_store = sync_team_profile_store(context_matches)
        return profile_store

    def predictor(match: Dict[str, Any], is_knockout: bool = False, stage: str | None = None) -> Dict[str, Any]:
        match_context = _find_match_context(match, context_matches)
        profile_store = profile_store_for(match_context)
        review_adjustment = build_review_adjustment(match_context, context_matches)
        team_feature_adjustment = build_match_feature_adjustment(
            match_context,
            context_matches,
            profile_store=profile_store,
        )
        injury_key = (
            str(match_context.get("home_team") or match.get("home_team") or ""),
            str(match_context.get("away_team") or match.get("away_team") or ""),
            str(match_context.get("match_date") or ""),
        )
        if injury_key not in injury_cache:
            injury_cache[injury_key] = _tournament_injury_feed(*injury_key)
        injury_feed = injury_cache[injury_key]
        injury_auto_apply = injury_feed.get("auto_apply") if isinstance(injury_feed, Mapping) else {}
        venue_context = _venue_weather_context(match_context)

        result = predict_match(
            home_team=match.get("home_team"),
            away_team=match.get("away_team"),
            venue=match_context.get("venue") or match.get("venue"),
            weather=venue_context["weather"],
            model_type="form_weighted",
            advantage_team="none",
            advantage_level="none",
            is_knockout=is_knockout,
            high_press=False,
            home_key_absence=bool(injury_auto_apply.get("home_key_absence")),
            away_key_absence=bool(injury_auto_apply.get("away_key_absence")),
            home_fatigue=False,
            away_fatigue=False,
            match_round=match_context.get("round") if match_context.get("round") is not None else match.get("round"),
            stage=stage or match_context.get("stage") or match.get("stage"),
            venue_factor=venue_context["venue_factor"],
            force_neutral=False,
            review_adjustment=review_adjustment,
            team_feature_adjustment=team_feature_adjustment,
            match_context=match_context,
        )
        result["injury_feed"] = injury_feed
        injury_lines = _injury_factor_lines(injury_feed)
        if injury_lines:
            existing_factors = result.get("factors") if isinstance(result.get("factors"), list) else []
            result["factors"] = [*existing_factors, *injury_lines]
        result["skill_audit"] = build_skill_audit(result, match=match_context)
        return result

    return predictor


def _default_predictor(match: Dict[str, Any], is_knockout: bool = False, stage: str | None = None) -> Dict[str, Any]:
    venue_context = _venue_weather_context(match)
    return predict_match(
        match.get("home_team"),
        match.get("away_team"),
        venue=match.get("venue"),
        weather=venue_context["weather"],
        model_type="form_weighted",
        match_round=match.get("round"),
        is_knockout=is_knockout,
        stage=stage or match.get("stage"),
        venue_factor=venue_context["venue_factor"],
    )


def _score_match(match: Dict[str, Any], predictor: Predictor, is_knockout: bool = False, stage: str | None = None) -> Dict[str, Any]:
    projected = deepcopy(match)
    if _is_completed_with_score(match) and not is_knockout:
        projected["home_score"] = int(match["home_score"])
        projected["away_score"] = int(match["away_score"])
        projected["score_source"] = "actual"
        projected["prediction"] = None
        return projected

    prediction = predictor(match, is_knockout, stage)
    home_score, away_score = _parse_score(prediction.get("predicted_score", "0-0"))
    projected["home_score"] = home_score
    projected["away_score"] = away_score
    projected["status"] = "projected"
    projected["score_source"] = "model"
    projected["prediction"] = {
        "predicted_score": prediction.get("predicted_score"),
        "predicted_score_probability": prediction.get("predicted_score_probability"),
        "possible_scores": prediction.get("possible_scores"),
        "confidence": prediction.get("confidence", 0),
        "home_win_probability": prediction.get("home_win_probability", 0),
        "draw_probability": prediction.get("draw_probability", 0),
        "away_win_probability": prediction.get("away_win_probability", 0),
        "penalty_probability": prediction.get("penalty_probability"),
        "model_version": prediction.get("model_version"),
        "xg_home": prediction.get("xg_home"),
        "xg_away": prediction.get("xg_away"),
        "factors": prediction.get("factors") or [],
        "review_adjustment": prediction.get("review_adjustment"),
        "team_feature_adjustment": prediction.get("team_feature_adjustment"),
        "profile_adjustment": prediction.get("profile_adjustment"),
        "injury_feed": prediction.get("injury_feed"),
        "total_goals_prediction": prediction.get("total_goals_prediction"),
        "skill_audit": prediction.get("skill_audit") or build_skill_audit(prediction, match=projected),
    }
    return projected


def _blank_row(team: str, group: str) -> Dict[str, Any]:
    return {
        "team": team,
        "group": group,
        "played": 0,
        "won": 0,
        "drawn": 0,
        "lost": 0,
        "goals_for": 0,
        "goals_against": 0,
        "goal_diff": 0,
        "points": 0,
        "conduct_score": 0,
        "fifa_rank": _team_rank(team),
    }


def _apply_result(rows: Dict[str, Dict[str, Any]], match: Dict[str, Any]) -> None:
    home = match["home_team"]
    away = match["away_team"]
    home_score = int(match["home_score"])
    away_score = int(match["away_score"])
    home_row = rows[home]
    away_row = rows[away]

    home_row["played"] += 1
    away_row["played"] += 1
    home_row["goals_for"] += home_score
    home_row["goals_against"] += away_score
    away_row["goals_for"] += away_score
    away_row["goals_against"] += home_score

    if home_score > away_score:
        home_row["won"] += 1
        home_row["points"] += 3
        away_row["lost"] += 1
    elif home_score < away_score:
        away_row["won"] += 1
        away_row["points"] += 3
        home_row["lost"] += 1
    else:
        home_row["drawn"] += 1
        away_row["drawn"] += 1
        home_row["points"] += 1
        away_row["points"] += 1


def _head_to_head_key(team: str, tied_teams: set[str], matches: List[Dict[str, Any]]) -> Tuple[int, int, int]:
    points = goals_for = goals_against = 0
    for match in matches:
        home = match["home_team"]
        away = match["away_team"]
        if home not in tied_teams or away not in tied_teams:
            continue
        home_score = int(match["home_score"])
        away_score = int(match["away_score"])
        if team == home:
            goals_for += home_score
            goals_against += away_score
            if home_score > away_score:
                points += 3
            elif home_score == away_score:
                points += 1
        elif team == away:
            goals_for += away_score
            goals_against += home_score
            if away_score > home_score:
                points += 3
            elif home_score == away_score:
                points += 1
    return points, goals_for - goals_against, goals_for


def _fallback_key(row: Dict[str, Any]) -> Tuple[int, int, int, int, str]:
    return (
        row["goal_diff"],
        row["goals_for"],
        row.get("conduct_score", 0),
        -row.get("fifa_rank", 999),
        row["team"],
    )


def _rank_tied_rows(rows: List[Dict[str, Any]], matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if len(rows) <= 1:
        return rows

    tied_teams = {row["team"] for row in rows}
    h2h_groups: Dict[Tuple[int, int, int], List[Dict[str, Any]]] = {}
    for row in rows:
        h2h_groups.setdefault(_head_to_head_key(row["team"], tied_teams, matches), []).append(row)

    if len(h2h_groups) > 1:
        ranked: List[Dict[str, Any]] = []
        for key in sorted(h2h_groups.keys(), reverse=True):
            subset = h2h_groups[key]
            ranked.extend(_rank_tied_rows(subset, matches) if len(subset) < len(rows) else sorted(subset, key=_fallback_key, reverse=True))
        return ranked

    return sorted(rows, key=_fallback_key, reverse=True)


def _rank_group(rows: Iterable[Dict[str, Any]], matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    by_points: Dict[int, List[Dict[str, Any]]] = {}
    for row in rows:
        row["goal_diff"] = row["goals_for"] - row["goals_against"]
        by_points.setdefault(row["points"], []).append(row)

    ranked: List[Dict[str, Any]] = []
    for points in sorted(by_points.keys(), reverse=True):
        ranked.extend(_rank_tied_rows(by_points[points], matches))

    for index, row in enumerate(ranked, start=1):
        row["rank"] = index
        row["qualified"] = index <= 2
    return ranked


def build_group_standings(
    matches: Iterable[Dict[str, Any]],
    predictor: Predictor | None = None,
) -> Tuple[Dict[str, List[Dict[str, Any]]], List[Dict[str, Any]]]:
    source_matches = list(matches)
    scorer = predictor or _contextual_predictor_factory(source_matches)
    group_matches = [deepcopy(match) for match in source_matches if match.get("group") and not match.get("stage")]
    projected_matches = [_score_match(match, scorer) for match in group_matches]

    groups: Dict[str, Dict[str, Dict[str, Any]]] = {}
    matches_by_group: Dict[str, List[Dict[str, Any]]] = {}
    for match in projected_matches:
        group = str(match["group"])
        groups.setdefault(group, {})
        matches_by_group.setdefault(group, []).append(match)
        for team in (match["home_team"], match["away_team"]):
            groups[group].setdefault(team, _blank_row(team, group))
        _apply_result(groups[group], match)

    ranked_groups = {
        group: _rank_group(rows.values(), matches_by_group[group])
        for group, rows in sorted(groups.items())
    }
    return ranked_groups, projected_matches


def rank_best_thirds(groups: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    thirds = [rows[2] for group, rows in sorted(groups.items()) if len(rows) >= 3]
    ranked = sorted(
        thirds,
        key=lambda row: (
            row["points"],
            row["goal_diff"],
            row["goals_for"],
            row.get("conduct_score", 0),
            -row.get("fifa_rank", 999),
            row["team"],
        ),
        reverse=True,
    )
    for index, row in enumerate(ranked, start=1):
        row["third_rank"] = index
        row["qualified"] = index <= 8
    return ranked


def resolve_third_place_assignments(groups: Iterable[str]) -> Dict[str, Any]:
    group_set = {str(group).upper() for group in groups}
    if len(group_set) != 8:
        raise ValueError("exactly eight third-place groups are required")

    for option, slots in THIRD_PLACE_OPTIONS.items():
        if set(slots.values()) == group_set:
            return {"option": option, "slots": slots}
    raise ValueError(f"no FIFA Annexe C option for third-place groups: {''.join(sorted(group_set))}")


def _resolve_slot(slot: str, groups: Dict[str, List[Dict[str, Any]]], third_slots: Dict[str, str]) -> Dict[str, Any]:
    if slot in third_slots:
        group = third_slots[slot]
        return groups[group][2]
    match = re.fullmatch(r"([A-L])([12])", slot)
    if not match:
        raise ValueError(f"unsupported knockout slot: {slot}")
    group, rank = match.group(1), int(match.group(2))
    return groups[group][rank - 1]


def build_round_of_32(
    groups: Dict[str, List[Dict[str, Any]]],
    best_thirds: List[Dict[str, Any]],
    schedule_by_id: Dict[int, Dict[str, Any]] | None = None,
) -> List[Dict[str, Any]]:
    assignments = resolve_third_place_assignments([row["group"] for row in best_thirds[:8]])
    schedule_by_id = schedule_by_id or {}
    round_matches: List[Dict[str, Any]] = []
    for match_id, home_slot, away_slot in ROUND_OF_32_TEMPLATE:
        home_row = _resolve_slot(home_slot, groups, assignments["slots"])
        away_row = _resolve_slot(away_slot, groups, assignments["slots"])
        scheduled = schedule_by_id.get(match_id, {})
        round_matches.append(
            {
                "id": match_id,
                "stage": "Round of 32",
                "home_team": home_row["team"],
                "away_team": away_row["team"],
                "home_slot": home_slot,
                "away_slot": away_slot,
                "match_date": scheduled.get("match_date"),
                "venue": scheduled.get("venue"),
            }
        )
    return round_matches


def _winner_from_prediction(match: Dict[str, Any], prediction: Dict[str, Any], home_score: int, away_score: int) -> Tuple[str, str, str]:
    if home_score > away_score:
        return match["home_team"], match["away_team"], "normal_time"
    if away_score > home_score:
        return match["away_team"], match["home_team"], "normal_time"
    home_prob = float(prediction.get("home_win_probability") or 0)
    away_prob = float(prediction.get("away_win_probability") or 0)
    if home_prob >= away_prob:
        return match["home_team"], match["away_team"], "extra_time_or_penalties"
    return match["away_team"], match["home_team"], "extra_time_or_penalties"


def _stable_ratio(*parts: Any) -> float:
    raw = "|".join(str(part) for part in parts).encode("utf-8")
    value = 0
    for byte in raw[:96]:
        value = (value * 131 + byte) % 1_000_003
    return value / 1_000_003


def _team_strength(team: str) -> float:
    profile = TEAM_PROFILES.get(team)
    if not profile:
        return 0.0
    ranking_component = max(0, 120 - profile.fifa_rank) * 2.4
    title_component = profile.titles * 18
    return profile.elo_rating + ranking_component + title_component


def _winner_by_probability(match: Dict[str, Any], prediction: Dict[str, Any]) -> Tuple[str, str]:
    home_prob = float(prediction.get("home_win_probability") or 0)
    away_prob = float(prediction.get("away_win_probability") or 0)
    if abs(home_prob - away_prob) < 0.012:
        home_strength = _team_strength(match["home_team"])
        away_strength = _team_strength(match["away_team"])
        if abs(home_strength - away_strength) < 4:
            home_seed = _stable_ratio(match.get("id"), match["home_team"], match["away_team"], "winner")
            return (match["home_team"], match["away_team"]) if home_seed >= 0.5 else (match["away_team"], match["home_team"])
        return (match["home_team"], match["away_team"]) if home_strength >= away_strength else (match["away_team"], match["home_team"])
    return (match["home_team"], match["away_team"]) if home_prob >= away_prob else (match["away_team"], match["home_team"])


def _penalty_score(match: Dict[str, Any], winner: str, prediction: Dict[str, Any]) -> Tuple[int, int]:
    home_prob = float(prediction.get("home_win_probability") or 0)
    away_prob = float(prediction.get("away_win_probability") or 0)
    balance = 1 - min(abs(home_prob - away_prob) * 2.4, 0.8)
    roll = _stable_ratio(match.get("id"), match["home_team"], match["away_team"], "penalties")
    if balance > 0.78 and roll > 0.58:
        winner_pens, loser_pens = 5, 4
    elif roll < 0.16:
        winner_pens, loser_pens = 3, 2
    elif roll > 0.84:
        winner_pens, loser_pens = 5, 3
    else:
        winner_pens, loser_pens = 4, 3
    if winner == match["home_team"]:
        return winner_pens, loser_pens
    return loser_pens, winner_pens


def _decision_basis(match: Dict[str, Any], prediction: Dict[str, Any], decision: str) -> List[str]:
    factors = list(prediction.get("factors") or [])[:4]
    home_prob = float(prediction.get("home_win_probability") or 0)
    away_prob = float(prediction.get("away_win_probability") or 0)
    penalty_probability = prediction.get("penalty_probability")
    basis = [
        *KNOCKOUT_DECISION_BASIS,
        f"晋级倾向: {match['home_team']} {home_prob:.1%} vs {match['away_team']} {away_prob:.1%}",
    ]
    if penalty_probability is not None:
        basis.append(f"点球风险估计: {float(penalty_probability):.1%}")
    if decision == "extra_time":
        basis.append("本场90分钟打平后，强度差足以在加时层给优势方额外进球")
    elif decision == "penalties":
        basis.append("双方强度接近，90分钟打平后更容易拖入点球决胜")
    else:
        basis.append("90分钟主预测已分出胜负，无需进入加时或点球")
    return basis + factors


def _apply_knockout_decision(
    match: Dict[str, Any],
    regulation_prediction: Dict[str, Any],
    knockout_prediction: Dict[str, Any],
    regulation_home: int,
    regulation_away: int,
) -> Dict[str, Any]:
    projected = deepcopy(match)
    projected["status"] = "projected"
    projected["score_source"] = "model"
    projected["regulation_home_score"] = regulation_home
    projected["regulation_away_score"] = regulation_away
    projected["extra_time_home_score"] = None
    projected["extra_time_away_score"] = None
    projected["penalty_home_score"] = None
    projected["penalty_away_score"] = None
    projected["prediction"] = {
        "predicted_score": knockout_prediction.get("predicted_score"),
        "regulation_predicted_score": regulation_prediction.get("predicted_score"),
        "predicted_score_probability": regulation_prediction.get("predicted_score_probability"),
        "possible_scores": regulation_prediction.get("possible_scores"),
        "confidence": knockout_prediction.get("confidence", 0),
        "home_win_probability": knockout_prediction.get("home_win_probability", 0),
        "draw_probability": regulation_prediction.get("draw_probability", 0),
        "away_win_probability": knockout_prediction.get("away_win_probability", 0),
        "penalty_probability": knockout_prediction.get("penalty_probability"),
        "model_version": knockout_prediction.get("model_version"),
        "xg_home": regulation_prediction.get("xg_home"),
        "xg_away": regulation_prediction.get("xg_away"),
        "factors": regulation_prediction.get("factors") or knockout_prediction.get("factors") or [],
        "review_adjustment": regulation_prediction.get("review_adjustment") or knockout_prediction.get("review_adjustment"),
        "team_feature_adjustment": regulation_prediction.get("team_feature_adjustment") or knockout_prediction.get("team_feature_adjustment"),
        "profile_adjustment": regulation_prediction.get("profile_adjustment") or knockout_prediction.get("profile_adjustment"),
        "injury_feed": regulation_prediction.get("injury_feed") or knockout_prediction.get("injury_feed"),
        "total_goals_prediction": regulation_prediction.get("total_goals_prediction"),
        "skill_audit": regulation_prediction.get("skill_audit") or build_skill_audit(regulation_prediction, match=projected),
    }

    if regulation_home != regulation_away:
        winner, loser, resolution = _winner_from_prediction(projected, knockout_prediction, regulation_home, regulation_away)
        projected["home_score"] = regulation_home
        projected["away_score"] = regulation_away
        projected["winner"] = winner
        projected["loser"] = loser
        projected["resolution"] = resolution
        projected["decided_by"] = "regular_time"
        projected["prediction_basis"] = _decision_basis(projected, knockout_prediction, "regular_time")
        return projected

    winner, loser = _winner_by_probability(projected, knockout_prediction)
    home_prob = float(knockout_prediction.get("home_win_probability") or 0)
    away_prob = float(knockout_prediction.get("away_win_probability") or 0)
    draw_prob_90 = float(regulation_prediction.get("draw_probability") or 0.0)
    penalty_probability = float(knockout_prediction.get("penalty_probability") or 0.0)
    penalty_after_draw = 0.48
    if draw_prob_90 > 0.001 and penalty_probability > 0:
        penalty_after_draw = (penalty_probability / draw_prob_90) * 0.78
    penalty_after_draw = max(0.36, min(0.64, penalty_after_draw - abs(home_prob - away_prob) * 0.38))
    roll = _stable_ratio(match.get("id"), match["home_team"], match["away_team"], "decision")

    if roll < penalty_after_draw:
        home_pens, away_pens = _penalty_score(projected, winner, knockout_prediction)
        projected["home_score"] = regulation_home
        projected["away_score"] = regulation_away
        projected["extra_time_home_score"] = regulation_home
        projected["extra_time_away_score"] = regulation_away
        projected["penalty_home_score"] = home_pens
        projected["penalty_away_score"] = away_pens
        projected["resolution"] = "penalties"
        projected["decided_by"] = "penalties"
        projected["prediction_basis"] = _decision_basis(projected, knockout_prediction, "penalties")
    else:
        home_extra = regulation_home + (1 if winner == match["home_team"] else 0)
        away_extra = regulation_away + (1 if winner == match["away_team"] else 0)
        projected["home_score"] = home_extra
        projected["away_score"] = away_extra
        projected["extra_time_home_score"] = home_extra
        projected["extra_time_away_score"] = away_extra
        projected["resolution"] = "extra_time"
        projected["decided_by"] = "extra_time"
        projected["prediction_basis"] = _decision_basis(projected, knockout_prediction, "extra_time")

    projected["winner"] = winner
    projected["loser"] = loser
    return projected


def _simulate_match(match: Dict[str, Any], predictor: Predictor, stage: str) -> Dict[str, Any]:
    regulation_prediction = predictor(match, False, stage)
    knockout_prediction = predictor(match, True, stage)
    regulation_home, regulation_away = _parse_score(regulation_prediction.get("predicted_score", "0-0"))
    return _apply_knockout_decision(match, regulation_prediction, knockout_prediction, regulation_home, regulation_away)


def _build_next_match(
    match_id: int,
    home_source: int,
    away_source: int,
    results: Dict[int, Dict[str, Any]],
    stage: str,
    schedule_by_id: Dict[int, Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    scheduled = (schedule_by_id or {}).get(match_id, {})
    return {
        "id": match_id,
        "stage": stage,
        "home_team": results[home_source]["winner"],
        "away_team": results[away_source]["winner"],
        "home_source": f"W{home_source}",
        "away_source": f"W{away_source}",
        "match_date": scheduled.get("match_date"),
        "venue": scheduled.get("venue"),
    }


def simulate_knockout(
    round_of_32: List[Dict[str, Any]],
    predictor: Predictor | None = None,
    schedule_by_id: Dict[int, Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    context_matches = [*round_of_32, *((schedule_by_id or {}).values())]
    scorer = predictor or _contextual_predictor_factory(context_matches)
    rounds: Dict[str, List[Dict[str, Any]]] = {"Round of 32": []}
    results: Dict[int, Dict[str, Any]] = {}

    for match in sorted(round_of_32, key=lambda item: item["id"]):
        simulated = _simulate_match(match, scorer, "Round of 32")
        rounds["Round of 32"].append(simulated)
        results[simulated["id"]] = simulated

    for stage, slots in KNOCKOUT_TREE.items():
        rounds[stage] = []
        for match_id, home_source, away_source in slots:
            match = _build_next_match(match_id, home_source, away_source, results, stage, schedule_by_id=schedule_by_id)
            simulated = _simulate_match(match, scorer, stage)
            rounds[stage].append(simulated)
            results[match_id] = simulated

    third_scheduled = (schedule_by_id or {}).get(103, {})
    third_place_match = {
        "id": 103,
        "stage": "Third place",
        "home_team": results[101]["loser"],
        "away_team": results[102]["loser"],
        "home_source": "L101",
        "away_source": "L102",
        "match_date": third_scheduled.get("match_date"),
        "venue": third_scheduled.get("venue"),
    }
    third_place = _simulate_match(third_place_match, scorer, "Third place")
    rounds["Third place"] = [third_place]
    results[103] = third_place

    return {
        "rounds": rounds,
        "champion": results[104]["winner"],
        "runner_up": results[104]["loser"],
        "third_place": third_place["winner"],
    }


def build_tournament_projection(
    matches: Iterable[Dict[str, Any]] | None = None,
    predictor: Predictor | None = None,
    simulate: bool = True,
) -> Dict[str, Any]:
    all_matches = list(matches) if matches is not None else load_schedule_matches()
    schedule_by_id = {}
    for match in all_matches:
        try:
            schedule_by_id[int(match["id"])] = match
        except (KeyError, TypeError, ValueError):
            continue

    scorer = predictor or _contextual_predictor_factory(all_matches)
    groups, projected_group_matches = build_group_standings(all_matches, predictor=scorer)
    best_thirds = rank_best_thirds(groups)
    qualified_thirds = best_thirds[:8]
    third_rule = resolve_third_place_assignments([row["group"] for row in qualified_thirds])
    round_of_32 = build_round_of_32(groups, qualified_thirds, schedule_by_id=schedule_by_id)
    knockout = simulate_knockout(round_of_32, predictor=scorer, schedule_by_id=schedule_by_id) if simulate else None

    qualifiers = []
    for group in GROUPS:
        rows = groups.get(group, [])
        qualifiers.extend(rows[:2])
    qualifiers.extend(qualified_thirds)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_policy": "completed group matches use official/live scores; missing group matches use the current 90-minute model; knockout simulations add FIFA extra-time and penalty decision layers",
        "model_basis": KNOCKOUT_DECISION_BASIS,
        "summary": {
            "group_match_count": len(projected_group_matches),
            "actual_group_match_count": sum(1 for match in projected_group_matches if match.get("score_source") == "actual"),
            "model_group_match_count": sum(1 for match in projected_group_matches if match.get("score_source") == "model"),
            "qualified_count": len(qualifiers),
            "third_place_option": third_rule["option"],
        },
        "groups": [{"group": group, "standings": groups.get(group, [])} for group in GROUPS if group in groups],
        "best_thirds": best_thirds,
        "qualifiers": qualifiers,
        "third_place_rule": third_rule,
        "group_matches": projected_group_matches,
        "round_of_32": round_of_32,
        "knockout": knockout,
    }
