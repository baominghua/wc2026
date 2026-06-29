from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List


EMPTY_TEAM_STATUS = {
    "unavailable_players": [],
    "doubtful_players": [],
    "card_risk_players": [],
    "note": "暂无可信实时伤停数据",
    "source": "not_configured",
}


def _default_feed_path() -> Path:
    return Path(__file__).resolve().parent.parent / "data" / "injuries.json"


def _read_local_feed() -> Dict[str, Any] | None:
    feed_path = Path(os.getenv("INJURY_FEED_PATH", str(_default_feed_path())))
    if not feed_path.exists():
        return None
    with feed_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _read_provider_feed(
    home_team: str,
    away_team: str,
    match_date: str | None = None,
) -> tuple[Dict[str, Any] | None, str | None]:
    errors: list[str] = []
    try:
        from services.api_football import api_football_enabled, fetch_api_football_injury_feed

        if api_football_enabled():
            return fetch_api_football_injury_feed(match_date), None
    except Exception as exc:
        errors.append(f"API-Football: {exc}")

    try:
        from services.sportmonks import sportmonks_enabled, fetch_sportmonks_injury_feed

        if sportmonks_enabled():
            return fetch_sportmonks_injury_feed(home_team, away_team, match_date), None
    except Exception as exc:
        errors.append(f"SportMonks: {exc}")

    return None, "；".join(errors) if errors else None


def _read_public_feed(
    home_team: str,
    away_team: str,
    match_date: str | None = None,
) -> tuple[Dict[str, Any] | None, str | None]:
    try:
        from services.public_injury_sources import get_public_match_injury_feed

        return get_public_match_injury_feed(home_team, away_team, match_date), None
    except Exception as exc:
        return None, str(exc)


def _dedupe(items: Iterable[str]) -> List[str]:
    seen: set[str] = set()
    result: List[str] = []
    for item in items:
        clean = str(item).strip()
        if clean and clean not in seen:
            seen.add(clean)
            result.append(clean)
    return result


def _team_status_from_feed(feed: Dict[str, Any], team_name: str) -> Dict[str, Any]:
    teams = feed.get("teams", {})
    team_status = teams.get(team_name, {})
    unavailable = list(team_status.get("unavailable_players", []))
    doubtful = list(team_status.get("doubtful_players", []))
    card_risk = list(team_status.get("card_risk_players", []))
    return {
        "unavailable_players": unavailable,
        "doubtful_players": doubtful,
        "card_risk_players": card_risk,
        "note": team_status.get("note")
        or ("有伤停信息" if unavailable or doubtful or card_risk else "暂无伤停记录"),
        "source": team_status.get("source") or feed.get("source") or "local_feed",
        "source_url": team_status.get("source_url") or feed.get("source_url") or "",
    }


def _combine_team_statuses(team_name: str, statuses: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    status_list = list(statuses)
    unavailable = _dedupe(player for status in status_list for player in status.get("unavailable_players", []))
    doubtful = _dedupe(player for status in status_list for player in status.get("doubtful_players", []))
    card_risk = _dedupe(player for status in status_list for player in status.get("card_risk_players", []))
    sources = _dedupe(status.get("source", "") for status in status_list)
    source_urls = _dedupe(status.get("source_url", "") for status in status_list)
    notes = _dedupe(
        status.get("note", "")
        for status in status_list
        if str(status.get("note", "")).strip()
        and "暂无可信" not in str(status.get("note", ""))
        and "暂无伤停记录" not in str(status.get("note", ""))
    )
    note = "；".join(notes[:3])
    if not note:
        note = "公开源暂无伤停记录，保留人工复核"
    return {
        "unavailable_players": unavailable,
        "doubtful_players": doubtful,
        "card_risk_players": card_risk,
        "note": note,
        "source": "+".join(sources) if sources else "public_and_manual",
        "source_url": source_urls[0] if source_urls else "",
    }


def _latest_updated(feeds: Iterable[Dict[str, Any]]) -> str | None:
    latest: datetime | None = None
    latest_raw: str | None = None
    for feed in feeds:
        raw = feed.get("last_updated")
        if not raw:
            continue
        try:
            parsed = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        if latest is None or parsed > latest:
            latest = parsed
            latest_raw = str(raw)
    return latest_raw


def _is_stale(last_updated: str | None) -> bool:
    if not last_updated:
        return False
    try:
        updated = datetime.fromisoformat(last_updated.replace("Z", "+00:00"))
        if updated.tzinfo is None:
            updated = updated.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - updated).total_seconds() > 12 * 60 * 60
    except ValueError:
        return False


def _has_key_absence(status: Dict[str, Any]) -> bool:
    unavailable: List[str] = status.get("unavailable_players", [])
    doubtful: List[str] = status.get("doubtful_players", [])
    return len(unavailable) > 0 or len(doubtful) >= 2


def get_match_injury_feed(home_team: str, away_team: str, match_date: str | None = None) -> Dict[str, Any]:
    provider_key_present = bool(
        os.getenv("API_FOOTBALL_KEY")
        or os.getenv("SPORTMONKS_TOKEN")
        or os.getenv("SPORTMONKS_API_TOKEN")
    )
    provider_error = None
    public_error = None
    feeds: list[Dict[str, Any]] = []
    try:
        provider_feed, provider_error = _read_provider_feed(home_team, away_team, match_date)
        public_feed, public_error = _read_public_feed(home_team, away_team, match_date)
        local_feed = _read_local_feed()
        for feed in (provider_feed, public_feed, local_feed):
            if feed:
                feeds.append(feed)
    except Exception as exc:
        return {
            "status": "error",
            "source": "injury_feed",
            "last_updated": None,
            "message": f"伤停 feed 读取失败: {exc}",
            "provider_key_present": provider_key_present,
            "teams": {
                "home": {"team": home_team, **EMPTY_TEAM_STATUS},
                "away": {"team": away_team, **EMPTY_TEAM_STATUS},
            },
            "auto_apply": {"home_key_absence": False, "away_key_absence": False},
        }

    if not feeds:
        status = "error" if provider_error else "not_configured"
        message = (
            "公开伤停源暂时读取失败；当前保留手动伤停勾选，未知信息不会自动计入模型。"
            if provider_error or public_error
            else "公开伤停源暂无可用记录；当前保留手动伤停勾选，未知信息不会自动计入模型。"
        )
        return {
            "status": status,
            "source": "manual_only",
            "last_updated": None,
            "message": message,
            "provider_key_present": provider_key_present,
            "teams": {
                "home": {"team": home_team, **EMPTY_TEAM_STATUS},
                "away": {"team": away_team, **EMPTY_TEAM_STATUS},
            },
            "auto_apply": {"home_key_absence": False, "away_key_absence": False},
        }

    home_status = _combine_team_statuses(home_team, [_team_status_from_feed(feed, home_team) for feed in feeds])
    away_status = _combine_team_statuses(away_team, [_team_status_from_feed(feed, away_team) for feed in feeds])
    last_updated = _latest_updated(feeds)
    sources = _dedupe(feed.get("source", "") for feed in feeds)
    status = "stale" if _is_stale(last_updated) else "connected"
    return {
        "status": status,
        "source": "+".join(sources) if sources else "public_and_manual",
        "last_updated": last_updated,
        "match_date": match_date,
        "message": "公开伤停与本地复核数据已合并读取" if status == "connected" else "伤停数据可能超过12小时未更新",
        "provider_key_present": provider_key_present,
        "teams": {
            "home": {"team": home_team, **home_status},
            "away": {"team": away_team, **away_status},
        },
        "auto_apply": {
            "home_key_absence": _has_key_absence(home_status),
            "away_key_absence": _has_key_absence(away_status),
        },
    }
