from __future__ import annotations

import asyncio
import json
import os
import urllib.request
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List

from services.api_football import api_football_enabled, fetch_api_football_match_feed
from services.espn_scoreboard import fetch_espn_scoreboard_feed
from services.match_stage import normalize_match_stage
from services.schedule import enrich_match_from_schedule


_CACHE: Dict[str, Any] | None = None
_SYNC_STATUS: Dict[str, Any] = {
    "status": "not_configured",
    "source": "none",
    "last_updated": None,
    "last_sync_attempt": None,
    "message": "尚未配置比赛实时数据源",
    "match_count": 0,
}
_SYNC_TASK: asyncio.Task | None = None

KNOCKOUT_STAGE_SLOT_COUNTS = {
    "Round of 32": 16,
    "Round of 16": 8,
    "Quarter-final": 4,
    "Semi-final": 2,
    "Third place": 1,
    "Final": 1,
}


def _default_feed_path() -> Path:
    return Path(__file__).resolve().parent.parent / "data" / "matches.live.json"


def _default_backfill_path() -> Path:
    return Path(__file__).resolve().parent.parent / "data" / "matches.public-results.json"


def _feed_path() -> Path:
    return Path(os.getenv("MATCH_FEED_PATH", str(_default_feed_path())))


def _backfill_path() -> Path:
    return Path(os.getenv("MATCH_RESULTS_BACKFILL_PATH", str(_default_backfill_path())))


def _local_match_feeds_enabled() -> bool:
    return os.getenv("LOCAL_MATCH_FEED_ENABLED", "false").lower() in {"1", "true", "yes"}


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _now_iso() -> str:
    return _now_utc().isoformat()


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _read_json_url(url: str) -> Dict[str, Any]:
    with urllib.request.urlopen(url, timeout=8) as response:
        payload = response.read().decode("utf-8")
    return json.loads(payload)


def _read_json_file(path: Path) -> Dict[str, Any] | None:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _read_feed(url_env: str, path: Path, allow_local_file: bool = False) -> Dict[str, Any] | None:
    feed_url = os.getenv(url_env)
    if feed_url:
        return _read_json_url(feed_url)
    if not allow_local_file:
        return None
    return _read_json_file(path)


def _normalise_feed(raw_feed: Dict[str, Any] | None, fallback_source: str) -> Dict[str, Any] | None:
    if not raw_feed:
        return None
    matches = raw_feed.get("matches")
    if not isinstance(matches, list):
        raise ValueError("match feed must contain a matches array")
    return {
        "source": raw_feed.get("source") or fallback_source,
        "last_updated": raw_feed.get("last_updated"),
        "matches": [enrich_match_from_schedule(match) for match in matches],
    }


def _match_id(match: Dict[str, Any]) -> int | None:
    try:
        return int(match.get("id"))
    except (TypeError, ValueError):
        return None


def _feed_identity(match: Dict[str, Any]) -> str:
    match_id = _match_id(match)
    if match_id is not None:
        return f"id:{match_id}"
    return f"object:{id(match)}"


def _match_day_key(match: Dict[str, Any]) -> str | None:
    parsed = _parse_datetime(str(match.get("match_date")) if match.get("match_date") else None)
    if not parsed:
        return None
    return parsed.astimezone(timezone(timedelta(hours=8))).date().isoformat()


def _confirmed_external_knockout_keys(matches: Iterable[Dict[str, Any]]) -> set[tuple[str, str]]:
    keys: set[tuple[str, str]] = set()
    for match in matches:
        stage = match.get("stage")
        day_key = _match_day_key(match)
        if (
            stage
            and day_key
            and not match.get("group")
            and match.get("fixture_status") == "confirmed"
            and match.get("live_source")
        ):
            keys.add((str(stage), day_key))
    return keys


def _officially_replaced_stages(matches: Iterable[Dict[str, Any]]) -> set[str]:
    counts: Dict[str, int] = {}
    for match in matches:
        stage = match.get("stage")
        if stage and not match.get("group") and match.get("live_source"):
            stage_key = str(stage)
            counts[stage_key] = counts.get(stage_key, 0) + 1
    return {
        stage
        for stage, count in counts.items()
        if count >= KNOCKOUT_STAGE_SLOT_COUNTS.get(stage, 999)
    }


def _remove_shadowed_placeholder_knockouts(matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    confirmed_keys = _confirmed_external_knockout_keys(matches)
    replaced_stages = _officially_replaced_stages(matches)
    if not confirmed_keys and not replaced_stages:
        return matches
    filtered: List[Dict[str, Any]] = []
    for match in matches:
        stage = match.get("stage")
        day_key = _match_day_key(match)
        if (
            stage
            and match.get("fixture_status") == "placeholder"
            and not match.get("live_source")
            and (
                str(stage) in replaced_stages
                or (day_key and (str(stage), day_key) in confirmed_keys)
            )
        ):
            continue
        filtered.append(match)
    return filtered


def _with_feed_meta(match: Dict[str, Any], feed: Dict[str, Any], feed_kind: str) -> Dict[str, Any]:
    cloned = deepcopy(match)
    cloned["_live_source"] = feed.get("source") or feed_kind
    cloned["_live_last_updated"] = feed.get("last_updated")
    cloned["_live_feed_kind"] = feed_kind
    return cloned


def _latest_timestamp(*values: str | None) -> str | None:
    parsed_values: list[tuple[datetime, str]] = []
    for value in values:
        parsed = _parse_datetime(value)
        if parsed:
            parsed_values.append((parsed, value or parsed.isoformat()))
    if not parsed_values:
        return next((value for value in values if value), None)
    return max(parsed_values, key=lambda item: item[0])[1]


def _combine_feeds(primary: Dict[str, Any] | None, backfill: Dict[str, Any] | None) -> Dict[str, Any] | None:
    if not primary and not backfill:
        return None

    matches_by_id: Dict[int, Dict[str, Any]] = {}

    if backfill:
        for match in backfill.get("matches", []):
            match_id = _match_id(match)
            if match_id is not None:
                matches_by_id[match_id] = _with_feed_meta(match, backfill, "public_result_backfill")

    if primary:
        for match in primary.get("matches", []):
            match_id = _match_id(match)
            if match_id is not None:
                matches_by_id[match_id] = _with_feed_meta(match, primary, "primary_live_feed")

    sources = []
    if primary:
        sources.append(primary.get("source") or "primary_live_feed")
    if backfill:
        sources.append(backfill.get("source") or "public_result_backfill")

    return {
        "source": " + ".join(sources) if sources else "none",
        "last_updated": _latest_timestamp(
            primary.get("last_updated") if primary else None,
            backfill.get("last_updated") if backfill else None,
        ),
        "matches": list(matches_by_id.values()),
        "primary_match_count": len(primary.get("matches", [])) if primary else 0,
        "backfill_match_count": len(backfill.get("matches", [])) if backfill else 0,
    }


def _combine_many_feeds(feeds: Iterable[tuple[Dict[str, Any] | None, str]]) -> Dict[str, Any] | None:
    matches_by_id: Dict[int, Dict[str, Any]] = {}
    sources: list[str] = []
    timestamps: list[str | None] = []
    counts: Dict[str, int] = {}
    for feed, feed_kind in feeds:
        if not feed:
            counts[f"{feed_kind}_match_count"] = 0
            continue
        sources.append(feed.get("source") or feed_kind)
        timestamps.append(feed.get("last_updated"))
        matches = feed.get("matches", [])
        counts[f"{feed_kind}_match_count"] = len(matches)
        for match in matches:
            match_id = _match_id(match)
            if match_id is not None:
                matches_by_id[match_id] = _with_feed_meta(match, feed, feed_kind)
    if not matches_by_id:
        return None
    return {
        "source": " + ".join(sources) if sources else "none",
        "last_updated": _latest_timestamp(*timestamps),
        "matches": list(matches_by_id.values()),
        **counts,
        "primary_match_count": counts.get("primary_live_feed_match_count", 0),
        "backfill_match_count": counts.get("public_result_backfill_match_count", 0),
        "espn_match_count": counts.get("espn_scoreboard_match_count", 0),
    }


def refresh_live_cache() -> Dict[str, Any]:
    """Refresh the cached live match feed.

    The primary feed is expected to be the most authoritative source. The public
    result backfill is a second layer used only to fill missing finished matches
    so pages do not silently fall back to predicted or scheduled state.
    """
    global _CACHE, _SYNC_STATUS

    feed_url = os.getenv("MATCH_FEED_URL")
    backfill_url = os.getenv("MATCH_RESULTS_BACKFILL_URL")
    path = _feed_path()
    backfill_path = _backfill_path()
    source_errors: list[str] = []

    try:
        allow_local_file = _local_match_feeds_enabled()
        primary = _normalise_feed(
            _read_feed("MATCH_FEED_URL", path, allow_local_file=allow_local_file),
            "MATCH_FEED_URL" if feed_url else "local_json_feed",
        )
        backfill = _normalise_feed(
            _read_feed("MATCH_RESULTS_BACKFILL_URL", backfill_path, allow_local_file=allow_local_file),
            "MATCH_RESULTS_BACKFILL_URL" if backfill_url else "public_result_backfill",
        )
        espn = None
        if os.getenv("ESPN_SCOREBOARD_ENABLED", "true").lower() not in {"0", "false", "no"}:
            try:
                espn_raw = fetch_espn_scoreboard_feed()
                source_errors.extend(espn_raw.get("source_errors") or [])
                espn = _normalise_feed(espn_raw, "espn_scoreboard")
            except Exception as exc:
                source_errors.append(f"espn_scoreboard: {exc}")
        api_football = None
        if api_football_enabled():
            try:
                api_football = _normalise_feed(fetch_api_football_match_feed(), "api_football")
            except Exception as exc:
                source_errors.append(f"api_football: {exc}")
        feed = _combine_many_feeds(
            [
                (backfill, "public_result_backfill"),
                (espn, "espn_scoreboard"),
                (primary, "primary_live_feed"),
                (api_football, "api_football"),
            ]
        )
    except Exception as exc:
        _SYNC_STATUS = {
            "status": "error",
            "source": "live_feed",
            "last_updated": None,
            "last_sync_attempt": _now_iso(),
            "message": f"比赛实时数据源读取失败: {exc}",
            "feed_path": str(path),
            "backfill_path": str(backfill_path),
            "local_match_feed_enabled": _local_match_feeds_enabled(),
            "feed_url_configured": bool(feed_url),
            "backfill_url_configured": bool(backfill_url),
            "api_football_configured": api_football_enabled(),
            "match_count": 0,
            "primary_match_count": 0,
            "backfill_match_count": 0,
            "espn_match_count": 0,
            "api_football_match_count": 0,
            "source_errors": [*source_errors, f"live_feed: {exc}"],
        }
        return deepcopy(_SYNC_STATUS)

    if not feed:
        _CACHE = None
        _SYNC_STATUS = {
            "status": "not_configured",
            "source": "none",
            "last_updated": None,
            "last_sync_attempt": _now_iso(),
            "message": "未配置比赛实时数据源；可设置 MATCH_FEED_PATH/MATCH_FEED_URL 或 MATCH_RESULTS_BACKFILL_PATH/MATCH_RESULTS_BACKFILL_URL。",
            "feed_path": str(path),
            "backfill_path": str(backfill_path),
            "local_match_feed_enabled": _local_match_feeds_enabled(),
            "feed_url_configured": bool(feed_url),
            "backfill_url_configured": bool(backfill_url),
            "api_football_configured": api_football_enabled(),
            "match_count": 0,
            "primary_match_count": 0,
            "backfill_match_count": 0,
            "espn_match_count": 0,
            "api_football_match_count": 0,
            "source_errors": source_errors,
        }
        return deepcopy(_SYNC_STATUS)

    _CACHE = feed
    last_updated = feed.get("last_updated")
    updated_at = _parse_datetime(last_updated)
    stale_seconds = max(int(os.getenv("LIVE_FEED_STALE_SECONDS", str(12 * 60 * 60))), 60)
    is_stale = bool(updated_at and (_now_utc() - updated_at).total_seconds() > stale_seconds)
    _SYNC_STATUS = {
        "status": "stale" if is_stale else "connected",
        "source": feed.get("source") or "live_feed",
        "last_updated": last_updated,
        "last_sync_attempt": _now_iso(),
        "message": "实时比赛数据已同步" if not is_stale else "实时比赛数据超过设定阈值未更新",
        "feed_path": str(path),
        "backfill_path": str(backfill_path),
        "local_match_feed_enabled": _local_match_feeds_enabled(),
        "feed_url_configured": bool(feed_url),
        "backfill_url_configured": bool(backfill_url),
        "api_football_configured": api_football_enabled(),
        "match_count": len(feed.get("matches", [])),
        "primary_match_count": feed.get("primary_match_count", 0),
        "backfill_match_count": feed.get("backfill_match_count", 0),
        "espn_match_count": feed.get("espn_match_count", 0),
        "api_football_match_count": feed.get("api_football_match_count", 0),
        "source_errors": source_errors,
    }
    return deepcopy(_SYNC_STATUS)


def _feed_matches_by_id(refresh_if_empty: bool = True) -> Dict[int, Dict[str, Any]]:
    if _CACHE is None and refresh_if_empty:
        refresh_live_cache()
    if not _CACHE:
        return {}
    matches_by_id: Dict[int, Dict[str, Any]] = {}
    for match in _CACHE.get("matches", []):
        match_id = _match_id(match)
        if match_id is not None:
            matches_by_id[match_id] = match
    return matches_by_id


def _normalise_match_text(value: Any) -> str:
    return "".join(str(value or "").lower().split())


def _signature_delta_seconds(base_match: Dict[str, Any], feed_match: Dict[str, Any]) -> float | None:
    base_home = _normalise_match_text(base_match.get("home_team"))
    base_away = _normalise_match_text(base_match.get("away_team"))
    base_kickoff = _parse_datetime(str(base_match.get("match_date")) if base_match.get("match_date") else None)
    if not base_home or not base_away or not base_kickoff:
        return None
    same_home = _normalise_match_text(feed_match.get("home_team")) == base_home
    same_away = _normalise_match_text(feed_match.get("away_team")) == base_away
    if not (same_home and same_away):
        return None
    feed_kickoff = _parse_datetime(str(feed_match.get("match_date")) if feed_match.get("match_date") else None)
    if not feed_kickoff:
        return None
    delta = abs((feed_kickoff - base_kickoff).total_seconds())
    return delta if delta <= 18 * 60 * 60 else None


def _find_feed_matches_for_base(base_match: Dict[str, Any], feed_matches: Iterable[Dict[str, Any]]) -> list[Dict[str, Any]]:
    try:
        base_id = int(base_match["id"])
    except (KeyError, TypeError, ValueError):
        base_id = None

    matched: list[tuple[float, int, Dict[str, Any]]] = []
    seen: set[str] = set()
    for index, feed_match in enumerate(feed_matches):
        feed_id = _match_id(feed_match)
        same_id = base_id is not None and feed_id == base_id
        signature_delta = _signature_delta_seconds(base_match, feed_match)
        if not same_id and signature_delta is None:
            continue
        identity = _feed_identity(feed_match)
        if identity in seen:
            continue
        seen.add(identity)
        priority_delta = signature_delta if signature_delta is not None else 0.0
        matched.append((priority_delta, index, feed_match))

    matched.sort(key=lambda item: item[1])
    return [item[2] for item in matched]


def _find_feed_match_by_signature(base_match: Dict[str, Any], feed_matches: Iterable[Dict[str, Any]]) -> Dict[str, Any] | None:
    best: tuple[float, Dict[str, Any]] | None = None
    for feed_match in feed_matches:
        delta = _signature_delta_seconds(base_match, feed_match)
        if delta is not None and (best is None or delta < best[0]):
            best = (delta, feed_match)
    return best[1] if best else None


def _public_feed_fields(match: Dict[str, Any]) -> Dict[str, Any]:
    return {key: value for key, value in match.items() if not key.startswith("_live_")}


def _has_goal_assists(report: Dict[str, Any] | None) -> bool:
    if not isinstance(report, dict):
        return False
    return any(isinstance(goal, dict) and goal.get("assist") for goal in report.get("goals") or [])


def _event_signature(event: Dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        str(event.get("type") or "").lower(),
        str(event.get("minute") or ""),
        str(event.get("team") or "").lower(),
        str(event.get("player") or "").lower(),
    )


def _merge_event_rows(existing_rows: Any, incoming_rows: Any) -> list[Dict[str, Any]]:
    merged: list[Dict[str, Any]] = []
    seen: set[tuple[str, str, str, str]] = set()
    for row in [*(existing_rows or []), *(incoming_rows or [])]:
        if not isinstance(row, dict):
            continue
        signature = _event_signature(row)
        if signature in seen:
            continue
        seen.add(signature)
        merged.append(deepcopy(row))
    return merged


def _meaningful(value: Any) -> bool:
    if value is None or value == "":
        return False
    if isinstance(value, (list, dict)):
        return bool(value)
    return True


def _merge_reports(existing_report: Dict[str, Any] | None, incoming_report: Dict[str, Any] | None) -> Dict[str, Any] | None:
    if not existing_report and not incoming_report:
        return None
    if not existing_report:
        return deepcopy(incoming_report)
    if not incoming_report:
        return deepcopy(existing_report)

    merged = deepcopy(existing_report)
    for key, value in incoming_report.items():
        if key in {"goals", "cards"}:
            continue
        if key == "stats" and isinstance(value, dict):
            current_stats = merged.get("stats") if isinstance(merged.get("stats"), dict) else {}
            merged["stats"] = {**current_stats, **value}
        elif _meaningful(value):
            merged[key] = deepcopy(value)

    existing_goals = existing_report.get("goals") or []
    incoming_goals = incoming_report.get("goals") or []
    if existing_goals and incoming_goals:
        if _has_goal_assists(existing_report) and not _has_goal_assists(incoming_report):
            merged["goals"] = deepcopy(existing_goals)
        else:
            merged["goals"] = deepcopy(incoming_goals)
    elif incoming_goals:
        merged["goals"] = deepcopy(incoming_goals)
    elif existing_goals:
        merged["goals"] = deepcopy(existing_goals)

    cards = _merge_event_rows(existing_report.get("cards"), incoming_report.get("cards"))
    if cards:
        merged["cards"] = cards

    return merged


def _build_report_from_feed(match: Dict[str, Any]) -> Dict[str, Any] | None:
    if isinstance(match.get("report"), dict):
        return match["report"]

    report_keys = ("attendance", "referee", "player_of_match", "lineups", "goals", "cards", "stats", "notes")
    if not any(key in match for key in report_keys):
        return None

    return {
        "attendance": match.get("attendance", 0),
        "referee": match.get("referee", "待官方确认"),
        "player_of_match": match.get("player_of_match", "待官方确认"),
        "lineups": match.get("lineups", []),
        "goals": match.get("goals", []),
        "cards": match.get("cards", []),
        "stats": match.get("stats", {}),
        "notes": match.get("notes", ["赛后详细报告来自实时数据源。"]),
    }


def _merge_feed_match(base_match: Dict[str, Any], feed_match: Dict[str, Any]) -> Dict[str, Any]:
    public_feed = _public_feed_fields(feed_match)
    base_id = base_match.get("id")
    merged = deepcopy(base_match)
    for key, value in public_feed.items():
        if _meaningful(value):
            merged[key] = deepcopy(value)
    for key in ("group", "round"):
        if _meaningful(base_match.get(key)):
            merged[key] = deepcopy(base_match[key])
    if base_id is not None and public_feed.get("id") != base_id:
        merged["id"] = base_id
        merged["espn_event_id"] = public_feed.get("espn_event_id") or public_feed.get("id")
    report = _merge_reports(
        base_match.get("report") if isinstance(base_match.get("report"), dict) else None,
        _build_report_from_feed(public_feed),
    )
    if report:
        merged["report"] = report

    feed_kind = feed_match.get("_live_feed_kind") or "primary_live_feed"
    is_backfill = feed_kind == "public_result_backfill"
    merged["data_status"] = "public_result_backfill" if is_backfill else "official_feed"
    merged["data_message"] = (
        "赛果来自公开赛后战报回填，技术统计待官方实时源补齐"
        if is_backfill
        else "赛果与技术统计来自实时数据源"
    )
    merged["live_source"] = feed_match.get("_live_source") or (_CACHE or {}).get("source") or "live_feed"
    merged["last_updated"] = feed_match.get("_live_last_updated") or (_CACHE or {}).get("last_updated")
    return merged


def _mark_match_data_status(match: Dict[str, Any]) -> Dict[str, Any]:
    if match.get("status") == "completed":
        match.setdefault("data_status", "static_seed")
        match.setdefault("data_message", "已完成比赛，使用内置赛后数据或实时源覆盖数据")
        return match

    kickoff = _parse_datetime(str(match.get("match_date")) if match.get("match_date") else None)
    if not kickoff:
        match.setdefault("status", "upcoming")
        match.setdefault("data_status", "scheduled")
        return match

    now = _now_utc()
    expected_finish = kickoff + timedelta(hours=2, minutes=20)
    if now >= expected_finish:
        match["status"] = "awaiting_result"
        match["data_status"] = "pending_official_result"
        match["data_message"] = "已过预计完场时间，等待官方实时数据源写入赛果"
    elif kickoff <= now < expected_finish:
        match["status"] = "live"
        match["data_status"] = "awaiting_live_feed"
        match["data_message"] = "比赛处于预计进行时段，等待实时数据源刷新"
    else:
        match.setdefault("status", "upcoming")
        match.setdefault("data_status", "scheduled")
        match.setdefault("data_message", "赛程未开赛")
    return match


def merge_live_matches(
    base_matches: Iterable[Dict[str, Any]],
    refresh_if_empty: bool = True,
) -> List[Dict[str, Any]]:
    feed_by_id = _feed_matches_by_id(refresh_if_empty=refresh_if_empty)
    feed_matches = list(feed_by_id.values())
    merged_matches: List[Dict[str, Any]] = []
    seen_feed_keys: set[str] = set()
    for base in base_matches:
        match = deepcopy(base)
        feed_matches_for_base = _find_feed_matches_for_base(match, feed_matches)
        for feed_match in feed_matches_for_base:
            seen_feed_keys.add(_feed_identity(feed_match))
            match = _merge_feed_match(match, feed_match)
        match = normalize_match_stage(_mark_match_data_status(match))
        merged_matches.append(match)

    for match_id, feed_match in feed_by_id.items():
        if _feed_identity(feed_match) in seen_feed_keys:
            continue
        if not feed_match.get("home_team") or not feed_match.get("away_team") or not feed_match.get("match_date"):
            continue
        existing_index = next(
            (
                index
                for index, existing_match in enumerate(merged_matches)
                if _signature_delta_seconds(existing_match, feed_match) is not None
            ),
            None,
        )
        if existing_index is not None:
            existing_match = merged_matches[existing_index]
            existing_id = existing_match.get("id")
            existing_espn_event_id = existing_match.get("espn_event_id")
            match = _merge_feed_match(existing_match, feed_match)
            incoming_kind = feed_match.get("_live_feed_kind")
            incoming_id = _match_id(feed_match)
            if incoming_kind in {"primary_live_feed", "api_football"} and incoming_id is not None:
                match["id"] = incoming_id
            elif existing_id is not None:
                match["id"] = existing_id
            if incoming_kind != "espn_scoreboard":
                if existing_espn_event_id:
                    match["espn_event_id"] = existing_espn_event_id
                elif existing_match.get("live_source") == "espn_scoreboard" and existing_id is not None:
                    match["espn_event_id"] = existing_id
            match = normalize_match_stage(_mark_match_data_status(match))
            merged_matches[existing_index] = match
            continue
        match = _merge_feed_match(feed_match, feed_match)
        match["id"] = match_id
        match = normalize_match_stage(_mark_match_data_status(match))
        merged_matches.append(match)
    return _remove_shadowed_placeholder_knockouts(merged_matches)


def get_live_sync_status(base_matches: Iterable[Dict[str, Any]] | None = None) -> Dict[str, Any]:
    refresh_live_cache()
    status = deepcopy(_SYNC_STATUS)
    if base_matches is not None:
        pending = [
            {
                "id": match["id"],
                "home_team": match["home_team"],
                "away_team": match["away_team"],
                "match_date": match["match_date"],
                "data_message": match.get("data_message"),
            }
            for match in merge_live_matches(base_matches, refresh_if_empty=False)
            if match.get("data_status") == "pending_official_result"
        ]
        status["pending_results"] = pending
        status["pending_result_count"] = len(pending)
    return status


async def _live_sync_loop(interval_seconds: int) -> None:
    while True:
        await asyncio.to_thread(refresh_live_cache)
        await asyncio.sleep(interval_seconds)


def start_live_sync_task() -> None:
    global _SYNC_TASK
    enabled = os.getenv("LIVE_SYNC_ENABLED", "true").lower() not in {"0", "false", "no"}
    if not enabled or _SYNC_TASK:
        return
    interval = max(int(os.getenv("LIVE_SYNC_INTERVAL_SECONDS", "60")), 15)
    _SYNC_TASK = asyncio.create_task(_live_sync_loop(interval))


def stop_live_sync_task() -> None:
    global _SYNC_TASK
    if _SYNC_TASK:
        _SYNC_TASK.cancel()
        _SYNC_TASK = None
