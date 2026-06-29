from __future__ import annotations

import json
import os
from collections import defaultdict
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Set, Tuple


WORLD_CUP_2026_START = datetime(2026, 6, 11, tzinfo=timezone.utc)
PROFILE_AVERAGE_KEYS = [
    "points",
    "goals_for",
    "goals_against",
    "goal_diff",
    "shots_for",
    "shots_against",
    "shots_on_target_for",
    "shots_on_target_against",
    "corners_for",
    "corners_against",
    "yellow_cards_for",
    "yellow_cards_against",
]
OFFICIAL_COMPETITION_KEYWORDS = (
    "qualifying",
    "qualification",
    "qualifier",
    "nations league",
    "copa america",
    "euro",
    "asian cup",
    "afcon",
    "gold cup",
    "concacaf",
    "conmebol",
    "uefa",
    "afc",
    "caf",
    "ofc",
    "fifa",
    "预选",
    "欧国联",
    "美洲杯",
    "欧洲杯",
    "亚洲杯",
    "非洲杯",
    "金杯赛",
    "正式",
)
FRIENDLY_COMPETITION_KEYWORDS = ("friendly", "friendlies", "友谊")
PLACEHOLDER_TEAM_TOKENS = ("winner", "runner", "third", "slot", "待定", "胜者", "败者", "小组")


def _safe_int(value: Any) -> Optional[int]:
    try:
        if value is None or value == "":
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _parse_datetime(value: Any) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        parsed = value
    else:
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _is_completed(match: Mapping[str, Any]) -> bool:
    return (
        match.get("status") == "completed"
        and _safe_int(match.get("home_score")) is not None
        and _safe_int(match.get("away_score")) is not None
    )


def _competition_text(match: Mapping[str, Any]) -> str:
    values = [
        match.get("competition"),
        match.get("tournament"),
        match.get("league"),
        match.get("event"),
        match.get("competition_name"),
    ]
    return " ".join(str(value or "") for value in values).strip().casefold()


def _is_current_world_cup_match(match: Mapping[str, Any]) -> bool:
    text = _competition_text(match)
    if "qualif" in text or "预选" in text:
        return False
    if match.get("group") or match.get("stage"):
        return True
    match_time = _parse_datetime(match.get("match_date"))
    if not match_time or match_time < WORLD_CUP_2026_START:
        return False
    if _safe_int(match.get("round")) is not None and not text:
        return True
    return "world cup" in text or "世界杯" in text or "fifa" in text


def _is_pre_world_cup_official_match(match: Mapping[str, Any]) -> bool:
    if _is_current_world_cup_match(match):
        return False
    match_time = _parse_datetime(match.get("match_date"))
    if match_time and match_time >= WORLD_CUP_2026_START:
        return False
    if match.get("is_official") is False or match.get("official") is False:
        return False
    if match.get("is_official") is True or match.get("official") is True:
        return True

    text = _competition_text(match)
    if any(keyword in text for keyword in FRIENDLY_COMPETITION_KEYWORDS):
        return False
    return any(keyword in text for keyword in OFFICIAL_COMPETITION_KEYWORDS)


def _project_schedule_summary() -> Tuple[Set[str], int]:
    schedule_path = Path(__file__).resolve().parents[1] / "data" / "matches.schedule.json"
    try:
        payload = json.loads(schedule_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set(), 0

    matches = payload.get("matches") if isinstance(payload, Mapping) else []
    if not isinstance(matches, list):
        return set(), 0

    teams: Set[str] = set()
    for match in matches:
        if not isinstance(match, Mapping):
            continue
        match_id = _safe_int(match.get("id")) or 0
        if match_id > 72:
            continue
        for key in ("home_team", "away_team"):
            team = str(match.get(key) or "").strip()
            lowered = team.casefold()
            if team and not any(token in lowered for token in PLACEHOLDER_TEAM_TOKENS):
                teams.add(team)
    return teams, len(matches)


def _is_feature_source_match(match: Mapping[str, Any], project_teams: Set[str]) -> bool:
    teams = {str(match.get("home_team") or ""), str(match.get("away_team") or "")}
    if project_teams and not teams.intersection(project_teams):
        return False
    return _is_current_world_cup_match(match) or _is_pre_world_cup_official_match(match)


def _match_team_names(matches: Iterable[Mapping[str, Any]]) -> Set[str]:
    teams: Set[str] = set()
    for match in matches:
        for key in ("home_team", "away_team"):
            team = str(match.get(key) or "").strip()
            if team:
                teams.add(team)
    return teams


def _report(match: Mapping[str, Any]) -> Mapping[str, Any]:
    report = match.get("report") if isinstance(match.get("report"), Mapping) else {}
    return report


def _stats(match: Mapping[str, Any]) -> Mapping[str, Any]:
    stats = _report(match).get("stats")
    return stats if isinstance(stats, Mapping) else {}


def _stat(stats: Mapping[str, Any], *names: str) -> Optional[float]:
    for name in names:
        if name in stats:
            value = stats.get(name)
            if value is None or value == "":
                return None
            return _safe_float(value)
    return None


def _red_card_counts(match: Mapping[str, Any]) -> Dict[str, int]:
    stats = _stats(match)
    counts = {
        "home": _safe_int(stats.get("red_cards_home") or stats.get("home_red_cards")) or 0,
        "away": _safe_int(stats.get("red_cards_away") or stats.get("away_red_cards")) or 0,
    }
    cards = _report(match).get("cards")
    if not isinstance(cards, list):
        return counts
    home = str(match.get("home_team") or "")
    away = str(match.get("away_team") or "")
    for card in cards:
        if not isinstance(card, Mapping):
            continue
        card_type = str(card.get("type") or card.get("card") or "").lower()
        if "red" not in card_type and "红" not in card_type:
            continue
        team = str(card.get("team") or card.get("team_name") or "")
        if team == home:
            counts["home"] += 1
        elif team == away:
            counts["away"] += 1
    return counts


def _avg(samples: List[Mapping[str, Any]], key: str) -> float:
    values = [_safe_float(item.get(key)) for item in samples if item.get(key) is not None]
    return sum(values) / len(values) if values else 0.0


def _average_profile_sample(samples: List[Mapping[str, Any]]) -> Dict[str, Any]:
    if not samples:
        return {}
    latest = samples[-1]
    averaged = {
        key: _avg(samples, key)
        for key in PROFILE_AVERAGE_KEYS
        if any(item.get(key) is not None for item in samples)
    }
    averaged.update(
        {
            "match_id": "sample_average",
            "match_date": latest.get("match_date"),
            "round": _safe_int(latest.get("round")) or 0,
            "group": latest.get("group"),
            "opponent": "sample_average",
            "score": "sample-average",
            "_sort_time": latest.get("_sort_time") or datetime.min.replace(tzinfo=timezone.utc),
        }
    )
    return averaged


def _team_sample(team: str, match: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
    home = str(match.get("home_team") or "")
    away = str(match.get("away_team") or "")
    home_score = _safe_int(match.get("home_score"))
    away_score = _safe_int(match.get("away_score"))
    if home_score is None or away_score is None or team not in {home, away}:
        return None

    is_home = team == home
    side = "home" if is_home else "away"
    other = "away" if is_home else "home"
    goals_for = home_score if is_home else away_score
    goals_against = away_score if is_home else home_score
    stats = _stats(match)
    red_cards = _red_card_counts(match)
    return {
        "match_id": match.get("id"),
        "match_date": match.get("match_date"),
        "round": _safe_int(match.get("round")) or 0,
        "group": match.get("group"),
        "opponent": away if is_home else home,
        "score": f"{goals_for}-{goals_against}",
        "points": 3 if goals_for > goals_against else 1 if goals_for == goals_against else 0,
        "goals_for": goals_for,
        "goals_against": goals_against,
        "goal_diff": goals_for - goals_against,
        "shots_for": _stat(stats, f"shots_{side}", f"{side}_shots"),
        "shots_against": _stat(stats, f"shots_{other}", f"{other}_shots"),
        "shots_on_target_for": _stat(stats, f"shots_on_target_{side}", f"{side}_shots_on_target"),
        "shots_on_target_against": _stat(stats, f"shots_on_target_{other}", f"{other}_shots_on_target"),
        "corners_for": _stat(stats, f"corners_{side}", f"{side}_corners"),
        "corners_against": _stat(stats, f"corners_{other}", f"{other}_corners"),
        "yellow_cards_for": _stat(stats, f"yellow_cards_{side}", f"{side}_yellow_cards"),
        "yellow_cards_against": _stat(stats, f"yellow_cards_{other}", f"{other}_yellow_cards"),
        "red_cards_for": red_cards[side],
        "red_cards_against": red_cards[other],
    }


def _feature_score(
    avg_points: float,
    avg_goal_diff: float,
    avg_goals_for: float,
    avg_goals_against: float,
    avg_shots_diff: float,
    avg_sot_diff: float,
    red_card_distorted: bool,
) -> float:
    score = (
        5.0
        + avg_points * 0.9
        + avg_goal_diff * 0.42
        + avg_sot_diff * 0.12
        + avg_shots_diff * 0.02
        - avg_goals_against * 0.14
    )
    if avg_goals_for >= 2.8:
        score += 0.3
    if red_card_distorted:
        score = 6.0 + (score - 6.0) * 0.7
    return round(_clamp(score, 3.8, 9.4), 2)


def _tags(
    avg_points: float,
    avg_goal_diff: float,
    avg_goals_for: float,
    avg_goals_against: float,
    avg_sot_diff: float,
    avg_yellow_for: float,
    red_card_distorted: bool,
) -> List[str]:
    tags: List[str] = []
    if avg_goals_for >= 2.5 or avg_sot_diff >= 3.0:
        tags.append("attack_hot")
    if avg_goals_against >= 1.5:
        tags.append("defense_leaky")
    if avg_points >= 2.2 and avg_goal_diff >= 1.5:
        tags.append("momentum_up")
    if avg_goal_diff <= -1.0:
        tags.append("form_dip")
    if avg_points > 0 and avg_points < 1.5 and abs(avg_goal_diff) <= 0.5:
        tags.append("draw_resilience")
    if avg_yellow_for >= 2.0 or red_card_distorted:
        tags.append("discipline_watch")
    if red_card_distorted:
        tags.append("red_card_distorted")
    return tags


def _lessons(team: str, form_state: Mapping[str, Any], tags: List[str]) -> List[str]:
    lessons: List[str] = []
    if "attack_hot" in tags:
        lessons.append(f"{team}近期射正/进球效率偏热，下一场比分池保留多进球上沿。")
    if "draw_resilience" in tags:
        lessons.append(f"{team}近期平局韧性存在，强弱差不大时保留1-1或0-0保护。")
    if "defense_leaky" in tags:
        lessons.append(f"{team}近期失球偏高，双方进球和对手进球预期需要小幅上调。")
    if "discipline_watch" in tags:
        lessons.append(f"{team}纪律风险偏高，黄牌、停赛和防守侵略性要单独复核。")
    if "red_card_distorted" in tags:
        lessons.append(f"{team}样本含红牌变量，不能把该场大比分完全写入基础实力。")
    if not lessons:
        lessons.append(
            f"{team}样本较少，特征库只做低权重提示；当前状态分 {form_state.get('score')}。"
        )
    return lessons[:4]


def build_team_feature_library(
    matches: Iterable[Mapping[str, Any]],
    before: Any = None,
    window_size: int = 3,
) -> Dict[str, Dict[str, Any]]:
    before_time = _parse_datetime(before)
    match_list = list(matches)
    project_teams, _fixture_match_count = _project_schedule_summary()
    input_teams = _match_team_names(match_list)
    active_project_teams = project_teams if project_teams.intersection(input_teams) else set()
    samples_by_team: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for match in match_list:
        if not _is_completed(match):
            continue
        match_time = _parse_datetime(match.get("match_date"))
        if before_time and match_time and match_time >= before_time:
            continue
        for team in (str(match.get("home_team") or ""), str(match.get("away_team") or "")):
            if not team:
                continue
            if active_project_teams and team not in active_project_teams:
                continue
            sample = _team_sample(team, match)
            if sample:
                sample["_sort_time"] = match_time or datetime.min.replace(tzinfo=timezone.utc)
                if _is_current_world_cup_match(match):
                    sample["_sample_source"] = "current_world_cup"
                    samples_by_team[team].append(sample)
                elif _is_pre_world_cup_official_match(match):
                    sample["_sample_source"] = "pre_world_cup_official"
                    samples_by_team[team].append(sample)

    profiles: Dict[str, Dict[str, Any]] = {}
    for team, samples in samples_by_team.items():
        samples.sort(key=lambda item: item["_sort_time"])
        world_cup_samples = [item for item in samples if item.get("_sample_source") == "current_world_cup"]
        pre_world_cup_samples = [item for item in samples if item.get("_sample_source") == "pre_world_cup_official"]
        pre_window = pre_world_cup_samples[-3:]

        if world_cup_samples and len(world_cup_samples) >= 3:
            window = list(world_cup_samples)
            source_samples = list(world_cup_samples)
            source = "current_world_cup_team_features"
            source_label = f"本届世界杯{len(world_cup_samples)}场正式赛均值"
            pre_sample_count = 0
        elif world_cup_samples and pre_window:
            window = [_average_profile_sample(world_cup_samples), _average_profile_sample(pre_window)]
            source_samples = sorted(world_cup_samples + pre_window, key=lambda item: item["_sort_time"])
            source = "world_cup_plus_pre_world_cup_team_features"
            source_label = f"本届世界杯{len(world_cup_samples)}场 + 世界杯前{len(pre_window)}场正式赛均值"
            pre_sample_count = len(pre_window)
        elif world_cup_samples:
            window = list(world_cup_samples)
            source_samples = list(world_cup_samples)
            source = "current_world_cup_team_features"
            source_label = f"本届世界杯{len(world_cup_samples)}场正式赛均值（世界杯前正式赛样本缺失）"
            pre_sample_count = 0
        elif pre_window:
            window = list(pre_window[-max(1, window_size):])
            source_samples = list(window)
            source = "pre_world_cup_team_features"
            source_label = f"世界杯前{len(window)}场正式赛均值"
            pre_sample_count = len(window)
        else:
            continue

        avg_points = _avg(window, "points")
        avg_goal_diff = _avg(window, "goal_diff")
        avg_goals_for = _avg(window, "goals_for")
        avg_goals_against = _avg(window, "goals_against")
        avg_shots_diff = _avg(window, "shots_for") - _avg(window, "shots_against")
        avg_sot_diff = _avg(window, "shots_on_target_for") - _avg(window, "shots_on_target_against")
        avg_yellow_for = _avg(window, "yellow_cards_for")
        red_card_distorted = any(
            (_safe_int(item.get("red_cards_for")) or 0) or (_safe_int(item.get("red_cards_against")) or 0)
            for item in source_samples
        )
        score = _feature_score(
            avg_points,
            avg_goal_diff,
            avg_goals_for,
            avg_goals_against,
            avg_shots_diff,
            avg_sot_diff,
            red_card_distorted,
        )
        tags = _tags(
            avg_points,
            avg_goal_diff,
            avg_goals_for,
            avg_goals_against,
            avg_sot_diff,
            avg_yellow_for,
            red_card_distorted,
        )
        latest = source_samples[-1]
        form_state = {
            "score": score,
            "avg_points": round(avg_points, 2),
            "avg_goal_diff": round(avg_goal_diff, 2),
            "avg_goals_for": round(avg_goals_for, 2),
            "avg_goals_against": round(avg_goals_against, 2),
            "avg_shots_diff": round(avg_shots_diff, 2),
            "avg_shots_on_target_diff": round(avg_sot_diff, 2),
            "latest_score": f"{latest.get('score')} vs {latest.get('opponent')}",
        }
        discipline_state = {
            "yellow_cards_for": round(avg_yellow_for, 2),
            "red_cards_for": sum(_safe_int(item.get("red_cards_for")) or 0 for item in source_samples),
            "risk": "watch" if "discipline_watch" in tags else "normal",
        }
        profile_lessons = _lessons(team, form_state, tags)
        profiles[team] = {
            "team": team,
            "sample_matches": len(source_samples),
            "world_cup_sample_matches": len(world_cup_samples),
            "pre_world_cup_sample_matches": pre_sample_count,
            "source": source,
            "source_label": source_label,
            "prop_sample_policy": "official_mean",
            "last_match_id": latest.get("match_id"),
            "last_match_date": latest.get("match_date"),
            "form_state": form_state,
            "discipline_state": discipline_state,
            "availability_state": {
                "status": "official_absence_feed_required",
                "note": "伤停/停赛以赛前官方信息覆盖，赛后特征库只记录纪律风险。",
            },
            "volatility_state": {
                "red_card_distorted": red_card_distorted,
                "label": "red-card-noise" if red_card_distorted else "normal",
            },
            "motivation_state": {
                "last_points": latest.get("points"),
                "note": "小组出线形势在具体比赛预测时按实时积分表重新计算。",
            },
            "matchup_preference": {
                "tags": tags,
                "note": "淘汰赛对手偏好先以战术标签低权重提示，样本不足不直接改基础实力。",
            },
            "tactical_tags": tags,
            "review_lessons": profile_lessons,
            "next_prediction_notes": profile_lessons,
        }
    return profiles


def _profile_store_path() -> Path:
    configured = os.environ.get("TEAM_PROFILE_STORE_PATH")
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parents[1] / "data" / "team_profiles.json"


def _write_profile_store(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    tmp_path.replace(path)


def load_team_profile_store(path: Optional[Any] = None) -> Dict[str, Any]:
    store_path = Path(path) if path is not None else _profile_store_path()
    if not store_path.exists():
        return {
            "version": 1,
            "generated_at": None,
            "match_count": 0,
            "fixture_match_count": 0,
            "feature_source_match_count": 0,
            "profile_count": 0,
            "profiles": {},
        }
    try:
        payload = json.loads(store_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {
            "version": 1,
            "generated_at": None,
            "match_count": 0,
            "fixture_match_count": 0,
            "feature_source_match_count": 0,
            "profile_count": 0,
            "profiles": {},
        }
    if not isinstance(payload, dict):
        return {
            "version": 1,
            "generated_at": None,
            "match_count": 0,
            "fixture_match_count": 0,
            "feature_source_match_count": 0,
            "profile_count": 0,
            "profiles": {},
        }
    profiles = payload.get("profiles")
    if not isinstance(profiles, Mapping):
        payload["profiles"] = {}
    payload.setdefault("version", 1)
    payload.setdefault("generated_at", None)
    payload.setdefault("match_count", 0)
    payload.setdefault("fixture_match_count", payload.get("match_count", 0))
    payload.setdefault("feature_source_match_count", payload.get("match_count", 0))
    payload.setdefault("profile_count", len(payload.get("profiles") or {}))
    return payload


def sync_team_profile_store(
    matches: Iterable[Mapping[str, Any]],
    before: Any = None,
    path: Optional[Any] = None,
) -> Dict[str, Any]:
    completed = [match for match in matches if _is_completed(match)]
    project_teams, fixture_match_count = _project_schedule_summary()
    input_teams = _match_team_names(completed)
    active_project_teams = project_teams if project_teams.intersection(input_teams) else set()
    feature_completed = [
        match for match in completed
        if _is_feature_source_match(match, active_project_teams)
    ]
    profiles = build_team_feature_library(completed, before=before)
    schedule_count = fixture_match_count if active_project_teams and fixture_match_count else len(completed)
    payload = {
        "version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "match_count": schedule_count,
        "fixture_match_count": schedule_count,
        "feature_source_match_count": len(feature_completed),
        "project_team_count": len(active_project_teams) or len(profiles),
        "profile_count": len(profiles),
        "profiles": profiles,
    }
    _write_profile_store(Path(path) if path is not None else _profile_store_path(), payload)
    return payload


def _profile_is_available_for_match(profile: Mapping[str, Any], current_match: Mapping[str, Any]) -> bool:
    target_time = _parse_datetime(current_match.get("match_date"))
    profile_time = _parse_datetime(profile.get("last_match_date"))
    if target_time and profile_time and profile_time >= target_time:
        return False
    return True


def _profiles_from_store(
    current_match: Mapping[str, Any],
    profile_store: Optional[Mapping[str, Any]],
) -> Dict[str, Optional[Dict[str, Any]]]:
    if not isinstance(profile_store, Mapping):
        return {"home": None, "away": None}
    profiles = profile_store.get("profiles")
    if not isinstance(profiles, Mapping):
        return {"home": None, "away": None}
    home = str(current_match.get("home_team") or "")
    away = str(current_match.get("away_team") or "")

    def pick(team: str) -> Optional[Dict[str, Any]]:
        profile = profiles.get(team)
        if not isinstance(profile, Mapping):
            return None
        if not _profile_is_available_for_match(profile, current_match):
            return None
        return deepcopy(dict(profile))

    return {"home": pick(home), "away": pick(away)}


def _attack_delta(profile: Optional[Mapping[str, Any]]) -> float:
    if not profile:
        return 0.0
    form = profile.get("form_state") if isinstance(profile.get("form_state"), Mapping) else {}
    score = _safe_float(form.get("score"), default=6.5)
    sample_count = _safe_int(profile.get("sample_matches")) or 0
    sample_weight = 0.62 if sample_count <= 1 else 0.8 if sample_count == 2 else 1.0
    delta = (score - 6.5) * 0.018 * sample_weight
    tags = set(profile.get("tactical_tags") or [])
    if "discipline_watch" in tags:
        delta -= 0.006
    if "red_card_distorted" in tags:
        delta *= 0.72
    return round(_clamp(delta, -0.06, 0.06), 4)


def build_match_feature_adjustment(
    current_match: Mapping[str, Any],
    matches: Iterable[Mapping[str, Any]],
    profile_store: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    home = str(current_match.get("home_team") or "")
    away = str(current_match.get("away_team") or "")
    if not home or not away:
        return {"applied": False, "reasons": ["球队特征库: 缺少比赛双方信息，未应用。"]}

    store_profiles = _profiles_from_store(current_match, profile_store if profile_store is not None else load_team_profile_store())
    home_profile = store_profiles.get("home")
    away_profile = store_profiles.get("away")
    source = "team_profile_store" if home_profile or away_profile else "team_feature_library"
    if not home_profile and not away_profile:
        profiles = build_team_feature_library(matches, before=current_match.get("match_date"))
        home_profile = profiles.get(home)
        away_profile = profiles.get(away)
    if not home_profile and not away_profile:
        return {
            "applied": False,
            "home_attack_delta": 0.0,
            "away_attack_delta": 0.0,
            "draw_probability_delta": 0.0,
            "source": source,
            "reasons": ["球队特征库: 暂无双方已完赛样本，保持基础模型。"],
            "team_profiles": {},
        }

    home_delta = _attack_delta(home_profile)
    away_delta = _attack_delta(away_profile)
    home_tags = set(home_profile.get("tactical_tags") if home_profile else [])
    away_tags = set(away_profile.get("tactical_tags") if away_profile else [])
    if "defense_leaky" in home_tags:
        away_delta = round(_clamp(away_delta + 0.01, -0.06, 0.06), 4)
    if "defense_leaky" in away_tags:
        home_delta = round(_clamp(home_delta + 0.01, -0.06, 0.06), 4)

    draw_delta = 0.0
    round_number = _safe_int(current_match.get("round")) or 0
    if round_number >= 2 and ("draw_resilience" in home_tags or "draw_resilience" in away_tags):
        draw_delta = 0.018
    if round_number >= 2 and "discipline_watch" in home_tags and "attack_hot" in away_tags:
        draw_delta = max(draw_delta, 0.012)

    reasons: List[str] = []
    if home_profile:
        reasons.append(
            f"球队特征库: {home} {home_profile['source_label']}，状态分 {home_profile['form_state']['score']}"
        )
    if away_profile:
        reasons.append(
            f"球队特征库: {away} {away_profile['source_label']}，状态分 {away_profile['form_state']['score']}"
        )
    if draw_delta:
        reasons.append("球队特征库: 平局韧性/小组形势触发低权重平局保护。")

    strength = max(abs(home_delta), abs(away_delta), draw_delta)
    return {
        "applied": True,
        "source": source,
        "strength": "medium" if strength >= 0.035 else "low",
        "home_attack_delta": home_delta,
        "away_attack_delta": away_delta,
        "draw_probability_delta": round(_clamp(draw_delta, 0.0, 0.04), 4),
        "reasons": reasons[:4],
        "team_profiles": {
            "home": home_profile,
            "away": away_profile,
        },
    }
