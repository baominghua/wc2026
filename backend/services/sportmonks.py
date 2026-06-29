from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, Iterable, Mapping

from services.api_football import TEAM_NAME_TO_CN


SPORTMONKS_BASE_URL = "https://api.sportmonks.com/v3/football"
SPORTMONKS_SIDELINED_SOURCE_URL = "https://www.sportmonks.com/glossary/injuries-and-suspensions/"
SPORTMONKS_TEAM_SEARCH_DOC_URL = (
    "https://docs.sportmonks.com/v3/endpoints-and-entities/endpoints/teams/get-teams-by-search-by-name"
)
SHANGHAI_TZ = timezone(timedelta(hours=8))

CN_TEAM_NAME_TO_QUERY = {
    cn_name: en_name
    for en_name, cn_name in TEAM_NAME_TO_CN.items()
}
CN_TEAM_NAME_TO_QUERY.update(
    {
        "美国": "United States",
        "捷克": "Czech Republic",
        "民主刚果": "DR Congo",
        "科特迪瓦": "Ivory Coast",
        "韩国": "Korea Republic",
        "土耳其": "Turkey",
    }
)


def sportmonks_enabled() -> bool:
    enabled = os.getenv("SPORTMONKS_ENABLED", "true").strip().lower() not in {"0", "false", "no", "off"}
    return enabled and bool(_token())


def _token() -> str:
    return os.getenv("SPORTMONKS_TOKEN") or os.getenv("SPORTMONKS_API_TOKEN") or ""


def _now_iso() -> str:
    return datetime.now(SHANGHAI_TZ).replace(microsecond=0).isoformat()


def _safe_str(value: Any) -> str:
    return str(value or "").strip()


def _unwrap(value: Any) -> Any:
    if isinstance(value, dict) and "data" in value and len(value) <= 2:
        return value.get("data")
    return value


def _api_get(path: str, params: Mapping[str, Any] | None = None) -> Dict[str, Any]:
    token = _token()
    if not token:
        raise RuntimeError("SPORTMONKS_TOKEN is not configured")
    base_url = os.getenv("SPORTMONKS_BASE_URL", SPORTMONKS_BASE_URL).rstrip("/")
    query = dict(params or {})
    query["api_token"] = token
    url = f"{base_url}{path}?{urllib.parse.urlencode({k: v for k, v in query.items() if v is not None})}"
    request = urllib.request.Request(url)
    with urllib.request.urlopen(
        request,
        timeout=int(os.getenv("SPORTMONKS_TIMEOUT_SECONDS", "12")),
    ) as response:
        return json.loads(response.read().decode("utf-8"))


def _configured_team_ids() -> Dict[str, int]:
    raw = os.getenv("SPORTMONKS_TEAM_IDS_JSON", "").strip()
    if not raw:
        return {}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    result: Dict[str, int] = {}
    if isinstance(payload, dict):
        for key, value in payload.items():
            try:
                result[str(key)] = int(value)
            except (TypeError, ValueError):
                continue
    return result


def _team_query(team_name: str) -> str:
    return CN_TEAM_NAME_TO_QUERY.get(team_name, team_name)


def _team_id(team_name: str) -> int:
    configured = _configured_team_ids()
    if team_name in configured:
        return configured[team_name]
    query = _team_query(team_name)
    payload = _api_get(
        f"/teams/search/{urllib.parse.quote(query)}",
        {"per_page": 10},
    )
    teams = payload.get("data") or []
    if not isinstance(teams, list):
        raise RuntimeError(f"SportMonks team search returned unexpected shape for {team_name}")
    exact = [
        team for team in teams
        if _safe_str(team.get("name")).casefold() == query.casefold()
    ]
    national = [
        team for team in teams
        if _safe_str(team.get("type")).casefold() == "national"
    ]
    chosen = (exact or national or teams)[0] if teams else None
    if not chosen or chosen.get("id") is None:
        raise RuntimeError(f"SportMonks team id not found for {team_name} ({query})")
    return int(chosen["id"])


def _parse_day(value: Any) -> date | None:
    text = _safe_str(value)
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        try:
            return date.fromisoformat(text[:10])
        except ValueError:
            return None


def _as_list(value: Any) -> list[Any]:
    value = _unwrap(value)
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _collect_sidelined_records(payload: Mapping[str, Any]) -> list[Dict[str, Any]]:
    data = _unwrap(payload.get("data", payload))
    records: list[Dict[str, Any]] = []
    for team in _as_list(data):
        if not isinstance(team, dict):
            continue
        for key in ("sidelined", "sidelined_players"):
            for item in _as_list(team.get(key)):
                if isinstance(item, dict):
                    records.append(item)
    return records


def _nested_text(value: Any, keys: Iterable[str]) -> str:
    value = _unwrap(value)
    if isinstance(value, dict):
        for key in keys:
            text = _safe_str(value.get(key))
            if text:
                return text
    return _safe_str(value)


def _player_name(record: Mapping[str, Any]) -> str:
    for key in ("player", "participant", "player_name"):
        text = _nested_text(record.get(key), ("display_name", "common_name", "name", "fullname"))
        if text:
            return text
    return _safe_str(record.get("name"))


def _reason(record: Mapping[str, Any]) -> str:
    candidates = [
        _nested_text(record.get("type"), ("name", "label", "description")),
        _nested_text(record.get("sideline"), ("name", "label", "description", "category")),
        _safe_str(record.get("reason")),
        _safe_str(record.get("category")),
    ]
    return next((item for item in candidates if item), "unavailable")


def _is_current(record: Mapping[str, Any], as_of: date | None = None) -> bool:
    completed = record.get("completed")
    if isinstance(completed, str):
        completed = completed.strip().lower() in {"1", "true", "yes"}
    start_day = _parse_day(record.get("start_date") or record.get("start"))
    end_day = _parse_day(record.get("end_date") or record.get("end"))
    target_day = as_of or datetime.now(SHANGHAI_TZ).date()
    if start_day and start_day > target_day:
        return False
    if end_day and end_day < target_day:
        return False
    if completed is True and (end_day is None or end_day <= target_day):
        return False
    return True


def normalise_sportmonks_sidelined_feed(
    team_payloads: Mapping[str, Mapping[str, Any]],
    *,
    fetched_at: str | None = None,
    match_date: str | None = None,
) -> Dict[str, Any]:
    as_of = _parse_day(match_date)
    teams: Dict[str, Dict[str, Any]] = {}
    for team_name, payload in team_payloads.items():
        status = {
            "unavailable_players": [],
            "doubtful_players": [],
            "items": [],
            "source": "sportmonks_sidelined",
            "note": "SportMonks sidelined include",
        }
        for raw_item in _collect_sidelined_records(payload):
            if not _is_current(raw_item, as_of):
                continue
            player = _player_name(raw_item)
            if not player:
                continue
            reason = _reason(raw_item)
            entry = f"{player}（{reason}）" if reason else player
            bucket = status["doubtful_players"] if "doubt" in reason.casefold() else status["unavailable_players"]
            bucket.append(entry)
            status["items"].append(
                {
                    "team": team_name,
                    "player": player,
                    "reason": reason,
                    "category": _safe_str(raw_item.get("category")),
                    "start_date": raw_item.get("start_date"),
                    "end_date": raw_item.get("end_date"),
                    "completed": raw_item.get("completed"),
                    "source": "sportmonks_sidelined",
                }
            )
        if not status["items"]:
            status["note"] = "SportMonks 当前未返回缺阵记录"
        teams[team_name] = status

    return {
        "source": "sportmonks_sidelined",
        "source_url": SPORTMONKS_SIDELINED_SOURCE_URL,
        "last_updated": fetched_at or _now_iso(),
        "teams": teams,
    }


def fetch_sportmonks_injury_feed(
    home_team: str,
    away_team: str,
    match_date: str | None = None,
) -> Dict[str, Any]:
    include = "sidelined.sideline;sidelined.player;sidelined.type"
    team_payloads: Dict[str, Dict[str, Any]] = {}
    for team_name in (home_team, away_team):
        team_payloads[team_name] = _api_get(f"/teams/{_team_id(team_name)}", {"include": include})
    return normalise_sportmonks_sidelined_feed(team_payloads, match_date=match_date)
