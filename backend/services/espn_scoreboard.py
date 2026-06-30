from __future__ import annotations

import json
import os
import re
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Mapping


ESPN_SCOREBOARD_URL = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard"
ESPN_SUMMARY_URL = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/summary"
SHANGHAI_TZ = timezone(timedelta(hours=8))

ESPN_STAGE_BY_SLUG = {
    "round-of-32": "Round of 32",
    "round-of-16": "Round of 16",
    "quarterfinal": "Quarter-final",
    "quarterfinals": "Quarter-final",
    "quarter-final": "Quarter-final",
    "quarter-finals": "Quarter-final",
    "semifinal": "Semi-final",
    "semifinals": "Semi-final",
    "semi-final": "Semi-final",
    "semi-finals": "Semi-final",
    "third-place": "Third place",
    "third-place-game": "Third place",
    "final": "Final",
}

ESPN_STAGE_BY_TEXT = (
    ("round of 32", "Round of 32"),
    ("round of 16", "Round of 16"),
    ("quarterfinal", "Quarter-final"),
    ("quarter-final", "Quarter-final"),
    ("semifinal", "Semi-final"),
    ("semi-final", "Semi-final"),
    ("third place", "Third place"),
    ("third-place", "Third place"),
    ("final", "Final"),
)

TEAM_ABBR_TO_CN = {
    "ALG": "阿尔及利亚",
    "ARG": "阿根廷",
    "AUS": "澳大利亚",
    "AUT": "奥地利",
    "BEL": "比利时",
    "BIH": "波黑",
    "BRA": "巴西",
    "CAN": "加拿大",
    "CIV": "科特迪瓦",
    "COL": "哥伦比亚",
    "COD": "民主刚果",
    "CPV": "佛得角",
    "CRO": "克罗地亚",
    "CUW": "库拉索",
    "CZE": "捷克",
    "ECU": "厄瓜多尔",
    "EGY": "埃及",
    "ENG": "英格兰",
    "ESP": "西班牙",
    "FRA": "法国",
    "GER": "德国",
    "GHA": "加纳",
    "HAI": "海地",
    "IRN": "伊朗",
    "IRQ": "伊拉克",
    "JOR": "约旦",
    "JPN": "日本",
    "KOR": "韩国",
    "KSA": "沙特阿拉伯",
    "MAR": "摩洛哥",
    "MEX": "墨西哥",
    "NED": "荷兰",
    "NOR": "挪威",
    "NZL": "新西兰",
    "PAN": "巴拿马",
    "PAR": "巴拉圭",
    "POR": "葡萄牙",
    "QAT": "卡塔尔",
    "RSA": "南非",
    "SCO": "苏格兰",
    "SEN": "塞内加尔",
    "SUI": "瑞士",
    "SWE": "瑞典",
    "TUN": "突尼斯",
    "TUR": "土耳其",
    "URU": "乌拉圭",
    "USA": "美国",
    "UZB": "乌兹别克斯坦",
}


def _now() -> datetime:
    return datetime.now(SHANGHAI_TZ)


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(SHANGHAI_TZ)


def _to_iso_shanghai(value: str | None) -> str | None:
    parsed = _parse_datetime(value)
    if not parsed:
        return value
    return parsed.replace(microsecond=0).isoformat()


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(str(value).replace("%", "")))
    except (TypeError, ValueError):
        return default


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(str(value).replace("%", ""))
    except (TypeError, ValueError):
        return default


def _team_name(team: Dict[str, Any]) -> str:
    abbr = str(team.get("abbreviation") or "").upper()
    if abbr in TEAM_ABBR_TO_CN:
        return TEAM_ABBR_TO_CN[abbr]
    return str(team.get("displayName") or team.get("name") or team.get("shortDisplayName") or "")


def _team_id(competitor: Dict[str, Any]) -> str:
    return str((competitor.get("team") or {}).get("id") or competitor.get("id") or "")


def _player_name(player: Dict[str, Any]) -> str:
    athlete = player.get("athlete") or {}
    return str(
        athlete.get("displayName")
        or athlete.get("fullName")
        or athlete.get("shortName")
        or player.get("name")
        or ""
    ).strip()


def _lineup_player_sort_key(player: Dict[str, Any]) -> tuple[int, int, str]:
    place = _safe_int(player.get("formationPlace"), 99)
    return (1 if place <= 0 else 0, place if place > 0 else 99, _player_name(player))


def _normalise_roster_players(players: Iterable[Dict[str, Any]]) -> list[str]:
    names: list[str] = []
    for player in sorted(players, key=_lineup_player_sort_key):
        name = _player_name(player)
        if name:
            names.append(name)
    return names


def _normalise_summary_lineups(summary: Dict[str, Any] | None) -> list[Dict[str, Any]]:
    if not isinstance(summary, dict):
        return []

    lineups: list[Dict[str, Any]] = []
    for roster_group in summary.get("rosters") or []:
        if not isinstance(roster_group, dict):
            continue
        roster = [player for player in roster_group.get("roster") or [] if isinstance(player, dict)]
        starters = [player for player in roster if player.get("starter") is True]
        if len(starters) < 8:
            continue
        substitutes = [
            player
            for player in roster
            if player.get("starter") is not True and player.get("active") is not False
        ]
        lineups.append(
            {
                "team": _team_name(roster_group.get("team") or {}),
                "side": str(roster_group.get("homeAway") or ""),
                "formation": str(roster_group.get("formation") or "").strip(),
                "starters": _normalise_roster_players(starters),
                "substitutes": _normalise_roster_players(substitutes),
                "source": "espn_summary_rosters",
            }
        )
    return lineups


def _stat_map(competitor: Dict[str, Any]) -> Dict[str, Any]:
    stats = {}
    for item in competitor.get("statistics") or []:
        name = item.get("name")
        if name:
            stats[name] = item.get("displayValue")
    return stats


def _extract_group(note: str | None) -> str | None:
    if not note:
        return None
    match = re.search(r"Group\s+([A-L])", note, re.IGNORECASE)
    return match.group(1).upper() if match else None


def _extract_stage(event: Dict[str, Any], competition: Dict[str, Any]) -> str | None:
    slug = str((event.get("season") or {}).get("slug") or "").strip().lower()
    if slug in ESPN_STAGE_BY_SLUG:
        return ESPN_STAGE_BY_SLUG[slug]

    for candidate in (competition.get("altGameNote"), event.get("name"), event.get("shortName")):
        text = str(candidate or "").strip().lower()
        if not text:
            continue
        for marker, stage in ESPN_STAGE_BY_TEXT:
            if marker in text:
                return stage
    return None


def _normalise_status(competition: Dict[str, Any]) -> str:
    status_type = ((competition.get("status") or {}).get("type") or {})
    if status_type.get("completed"):
        return "completed"
    if status_type.get("state") == "in":
        return "live"
    return "upcoming"


def _event_links(event: Dict[str, Any]) -> list[str]:
    links = []
    for link in event.get("links") or []:
        href = link.get("href")
        if href:
            links.append(href)
    return links


def _event_notes(event: Dict[str, Any]) -> list[str]:
    notes = ["ESPN scoreboard 自动同步。"]
    for headline in event.get("headlines") or []:
        text = headline.get("description") or headline.get("shortLinkText")
        if text:
            notes.append(text)
    return notes


def _detail_minute(detail: Dict[str, Any]) -> int:
    clock = (detail.get("clock") or {}).get("displayValue") or ""
    match = re.search(r"\d+", str(clock))
    return int(match.group(0)) if match else 0


def _first_athlete_name(detail: Dict[str, Any]) -> str:
    athletes = detail.get("athletesInvolved") or []
    if not athletes:
        return "待确认"
    return athletes[0].get("displayName") or athletes[0].get("shortName") or "待确认"


def _normalise_details(details: Iterable[Dict[str, Any]], team_names_by_id: Dict[str, str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    goals: list[dict[str, Any]] = []
    cards: list[dict[str, Any]] = []
    for detail in details:
        team = team_names_by_id.get(str((detail.get("team") or {}).get("id") or ""), "待确认")
        item = {
            "minute": _detail_minute(detail),
            "team": team,
            "player": _first_athlete_name(detail),
            "type": "goal",
        }
        if detail.get("scoringPlay"):
            if detail.get("ownGoal"):
                item["type"] = "own_goal"
            elif detail.get("penaltyKick"):
                item["type"] = "penalty"
            goals.append(item)
        elif detail.get("yellowCard") or detail.get("redCard"):
            cards.append(
                {
                    "minute": item["minute"],
                    "team": team,
                    "player": item["player"],
                    "type": "red_card" if detail.get("redCard") else "yellow_card",
                }
            )
    return goals, cards


def _normalise_competition(
    event: Dict[str, Any],
    competition: Dict[str, Any],
    summary: Dict[str, Any] | None = None,
) -> Dict[str, Any] | None:
    competitors = competition.get("competitors") or []
    home = next((item for item in competitors if item.get("homeAway") == "home"), None)
    away = next((item for item in competitors if item.get("homeAway") == "away"), None)
    if not home or not away:
        return None

    home_team = _team_name(home.get("team") or {})
    away_team = _team_name(away.get("team") or {})
    home_stats = _stat_map(home)
    away_stats = _stat_map(away)
    team_names_by_id = {_team_id(home): home_team, _team_id(away): away_team}
    goals, cards = _normalise_details(competition.get("details") or [], team_names_by_id)
    lineups = _normalise_summary_lineups(summary)
    home_lineup = next((lineup for lineup in lineups if lineup.get("side") == "home"), None)
    away_lineup = next((lineup for lineup in lineups if lineup.get("side") == "away"), None)
    venue = competition.get("venue") or event.get("venue") or {}
    address = venue.get("address") or {}
    venue_name = venue.get("fullName") or venue.get("displayName") or "待确认球场"
    city = address.get("city")
    country = address.get("country")
    venue_display = "，".join(part for part in [venue_name, city or country] if part)
    group = _extract_group(competition.get("altGameNote"))
    stage = _extract_stage(event, competition)

    return {
        "id": _safe_int(event.get("id")),
        "espn_event_id": str(event.get("id") or ""),
        "home_team": home_team,
        "away_team": away_team,
        "group": None if stage else group,
        "round": None if stage else (1 if group else None),
        "stage": stage,
        "match_date": _to_iso_shanghai(competition.get("date") or event.get("date")),
        "venue": venue_display,
        "status": _normalise_status(competition),
        "home_score": _safe_int(home.get("score")),
        "away_score": _safe_int(away.get("score")),
        "home_formation": (home_lineup or {}).get("formation"),
        "away_formation": (away_lineup or {}).get("formation"),
        "report": {
            "attendance": _safe_int(competition.get("attendance")),
            "referee": "待官方确认",
            "player_of_match": "待官方确认",
            "lineups": lineups,
            "goals": goals,
            "cards": cards,
            "stats": {
                "possession_home": _safe_float(home_stats.get("possessionPct")),
                "possession_away": _safe_float(away_stats.get("possessionPct")),
                "shots_home": _safe_int(home_stats.get("totalShots")),
                "shots_away": _safe_int(away_stats.get("totalShots")),
                "shots_on_target_home": _safe_int(home_stats.get("shotsOnTarget")),
                "shots_on_target_away": _safe_int(away_stats.get("shotsOnTarget")),
                "xg_home": 0,
                "xg_away": 0,
                "corners_home": _safe_int(home_stats.get("wonCorners")),
                "corners_away": _safe_int(away_stats.get("wonCorners")),
                "fouls_home": _safe_int(home_stats.get("foulsCommitted")),
                "fouls_away": _safe_int(away_stats.get("foulsCommitted")),
                "yellow_cards_home": sum(1 for card in cards if card["team"] == home_team and card["type"] == "yellow_card"),
                "yellow_cards_away": sum(1 for card in cards if card["team"] == away_team and card["type"] == "yellow_card"),
                "passes_home": 0,
                "passes_away": 0,
            },
            "notes": _event_notes(event),
            "source_urls": _event_links(event),
        },
    }


def normalise_espn_scoreboard(
    raw_feed: Dict[str, Any],
    fetched_at: str | None = None,
    summary_by_event_id: Mapping[str, Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    matches: List[Dict[str, Any]] = []
    summary_by_event_id = summary_by_event_id or {}
    for event in raw_feed.get("events") or []:
        for competition in event.get("competitions") or []:
            summary = summary_by_event_id.get(str(event.get("id") or ""))
            match = _normalise_competition(event, competition, summary)
            if match:
                matches.append(match)
    return {
        "source": "espn_scoreboard",
        "last_updated": fetched_at or _now().replace(microsecond=0).isoformat(),
        "matches": matches,
    }


def _scoreboard_url(date_value: str) -> str:
    return ESPN_SCOREBOARD_URL + "?" + urllib.parse.urlencode({"dates": date_value})


def _summary_url(event_id: str) -> str:
    return ESPN_SUMMARY_URL + "?" + urllib.parse.urlencode({"event": event_id})


def _read_json_url(url: str) -> Dict[str, Any]:
    with urllib.request.urlopen(url, timeout=int(os.getenv("ESPN_SCOREBOARD_TIMEOUT_SECONDS", "8"))) as response:
        return json.loads(response.read().decode("utf-8"))


def _parse_scoreboard_date(value: str | None) -> datetime.date | None:
    if not value:
        return None
    try:
        return datetime.strptime(value.strip(), "%Y%m%d").date()
    except ValueError:
        return None


def _date_values() -> list[str]:
    configured = os.getenv("ESPN_SCOREBOARD_DATES")
    if configured:
        return [item.strip() for item in configured.split(",") if item.strip()]
    today = _now().date()
    days_forward = max(_safe_int(os.getenv("ESPN_SCOREBOARD_DAYS_FORWARD"), 14), 0)
    start_date = _parse_scoreboard_date(os.getenv("ESPN_SCOREBOARD_START_DATE", "20260611"))
    if start_date:
        max_days = max(_safe_int(os.getenv("ESPN_SCOREBOARD_MAX_DAYS"), 60), 1)
        end_date = min(today + timedelta(days=days_forward), start_date + timedelta(days=max_days - 1))
        if end_date >= start_date:
            return [
                (start_date + timedelta(days=offset)).strftime("%Y%m%d")
                for offset in range((end_date - start_date).days + 1)
            ]

    days_back = max(_safe_int(os.getenv("ESPN_SCOREBOARD_DAYS_BACK"), 14), 0)
    return [
        (today + timedelta(days=offset)).strftime("%Y%m%d")
        for offset in range(-days_back, days_forward + 1)
    ]


def _should_fetch_summary(event: Dict[str, Any]) -> bool:
    enabled = os.getenv("ESPN_SUMMARY_LINEUPS_ENABLED", "true").strip().lower()
    if enabled in {"0", "false", "no", "off"}:
        return False

    competitions = event.get("competitions") or []
    competition = competitions[0] if competitions else {}
    status_type = ((competition.get("status") or {}).get("type") or {})
    state = status_type.get("state")
    if competition.get("recent") or state == "in":
        return True

    parsed = _parse_datetime(competition.get("date") or event.get("date"))
    if not parsed:
        return False
    now = _now()
    hours_before = max(_safe_int(os.getenv("ESPN_SUMMARY_LINEUP_HOURS_BEFORE"), 3), 0)
    hours_after = max(_safe_int(os.getenv("ESPN_SUMMARY_LINEUP_HOURS_AFTER"), 36), 0)
    return now - timedelta(hours=hours_after) <= parsed <= now + timedelta(hours=hours_before)


def _summary_payloads(raw_feed: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    event_ids = [
        str(event.get("id") or "")
        for event in raw_feed.get("events") or []
        if event.get("id") and _should_fetch_summary(event)
    ]
    if not event_ids:
        return {}

    max_workers = max(_safe_int(os.getenv("ESPN_SUMMARY_MAX_WORKERS"), 4), 1)
    max_workers = min(max_workers, len(event_ids))
    payloads: Dict[str, Dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_read_json_url, _summary_url(event_id)): event_id for event_id in event_ids}
        for future in as_completed(futures):
            event_id = futures[future]
            try:
                payloads[event_id] = future.result()
            except Exception:
                continue
    return payloads


def fetch_espn_scoreboard_feed() -> Dict[str, Any]:
    combined_matches: list[dict[str, Any]] = []
    fetched_at = _now().replace(microsecond=0).isoformat()
    date_values = _date_values()
    max_workers = max(_safe_int(os.getenv("ESPN_SCOREBOARD_MAX_WORKERS"), 6), 1)
    max_workers = min(max_workers, max(len(date_values), 1))
    errors: list[str] = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_read_json_url, _scoreboard_url(date_value)): date_value
            for date_value in date_values
        }
        for future in as_completed(futures):
            date_value = futures[future]
            try:
                raw = future.result()
            except Exception as exc:
                errors.append(f"{date_value}: {exc}")
                continue
            feed = normalise_espn_scoreboard(
                raw,
                fetched_at=fetched_at,
                summary_by_event_id=_summary_payloads(raw),
            )
            combined_matches.extend(feed.get("matches", []))

    if errors and not combined_matches:
        raise RuntimeError("ESPN scoreboard fetch failed: " + "; ".join(errors[:3]))

    by_event_id = {match.get("espn_event_id") or match.get("id"): match for match in combined_matches}
    return {
        "source": "espn_scoreboard",
        "last_updated": fetched_at,
        "matches": list(by_event_id.values()),
        "source_errors": errors,
    }
