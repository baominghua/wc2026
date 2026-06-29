from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable


API_FOOTBALL_BASE_URL = "https://v3.football.api-sports.io"
SHANGHAI_TZ = timezone(timedelta(hours=8))

COMPLETED_STATUS = {"FT", "AET", "PEN"}
LIVE_STATUS = {"1H", "HT", "2H", "ET", "BT", "P", "SUSP", "INT", "LIVE"}

TEAM_NAME_TO_CN = {
    "Algeria": "阿尔及利亚",
    "Argentina": "阿根廷",
    "Australia": "澳大利亚",
    "Austria": "奥地利",
    "Belgium": "比利时",
    "Bosnia and Herzegovina": "波黑",
    "Brazil": "巴西",
    "Canada": "加拿大",
    "Cape Verde": "佛得角",
    "Colombia": "哥伦比亚",
    "Costa Rica": "哥斯达黎加",
    "Croatia": "克罗地亚",
    "Curacao": "库拉索",
    "Czech Republic": "捷克",
    "Czechia": "捷克",
    "DR Congo": "民主刚果",
    "Ecuador": "厄瓜多尔",
    "Egypt": "埃及",
    "England": "英格兰",
    "France": "法国",
    "Germany": "德国",
    "Ghana": "加纳",
    "Haiti": "海地",
    "Iran": "伊朗",
    "Iraq": "伊拉克",
    "Ivory Coast": "科特迪瓦",
    "Japan": "日本",
    "Jordan": "约旦",
    "Korea Republic": "韩国",
    "Mexico": "墨西哥",
    "Morocco": "摩洛哥",
    "Netherlands": "荷兰",
    "New Zealand": "新西兰",
    "Norway": "挪威",
    "Panama": "巴拿马",
    "Paraguay": "巴拉圭",
    "Portugal": "葡萄牙",
    "Qatar": "卡塔尔",
    "Saudi Arabia": "沙特阿拉伯",
    "Scotland": "苏格兰",
    "Senegal": "塞内加尔",
    "South Africa": "南非",
    "Spain": "西班牙",
    "Sweden": "瑞典",
    "Switzerland": "瑞士",
    "Tunisia": "突尼斯",
    "Turkey": "土耳其",
    "Türkiye": "土耳其",
    "United States": "美国",
    "USA": "美国",
    "Uruguay": "乌拉圭",
    "Uzbekistan": "乌兹别克斯坦",
}


def api_football_enabled() -> bool:
    enabled = os.getenv("API_FOOTBALL_ENABLED", "true").lower() not in {"0", "false", "no"}
    return enabled and bool(os.getenv("API_FOOTBALL_KEY"))


def _now() -> datetime:
    return datetime.now(SHANGHAI_TZ)


def _now_iso() -> str:
    return _now().replace(microsecond=0).isoformat()


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(str(value or "").replace("%", "")))
    except (TypeError, ValueError):
        return default


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(str(value or "").replace("%", ""))
    except (TypeError, ValueError):
        return default


def _safe_str(value: Any) -> str:
    return str(value or "").strip()


def _team_name(value: Any) -> str:
    name = _safe_str(value)
    return TEAM_NAME_TO_CN.get(name, name)


def _api_get(path: str, params: Dict[str, Any] | None = None) -> Dict[str, Any]:
    key = os.getenv("API_FOOTBALL_KEY")
    if not key:
        raise RuntimeError("API_FOOTBALL_KEY is not configured")
    base_url = os.getenv("API_FOOTBALL_BASE_URL", API_FOOTBALL_BASE_URL).rstrip("/")
    query = urllib.parse.urlencode({k: v for k, v in (params or {}).items() if v is not None})
    url = f"{base_url}{path}"
    if query:
        url = f"{url}?{query}"
    request = urllib.request.Request(url, headers={"x-apisports-key": key})
    with urllib.request.urlopen(request, timeout=int(os.getenv("API_FOOTBALL_TIMEOUT_SECONDS", "12"))) as response:
        return json.loads(response.read().decode("utf-8"))


def _league_params() -> Dict[str, Any]:
    return {
        "league": os.getenv("API_FOOTBALL_LEAGUE_ID", "1"),
        "season": os.getenv("API_FOOTBALL_SEASON", "2026"),
    }


def _normalise_fixture_status(short_status: str | None) -> str:
    short = _safe_str(short_status).upper()
    if short in COMPLETED_STATUS:
        return "completed"
    if short in LIVE_STATUS:
        return "live"
    return "upcoming"


def _normalise_match_date(value: str | None) -> str | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return value
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(SHANGHAI_TZ).replace(microsecond=0).isoformat()


def _event_type(event: Dict[str, Any]) -> str:
    event_type = _safe_str(event.get("type")).lower()
    detail = _safe_str(event.get("detail")).lower()
    comments = _safe_str(event.get("comments")).lower()
    joined = f"{detail} {comments}"
    if event_type == "card":
        return "red_card" if "red" in joined else "yellow_card"
    if "own" in joined:
        return "own_goal"
    if "penalty" in joined:
        return "penalty"
    return "goal"


def _normalise_events(events: Iterable[Dict[str, Any]]) -> tuple[list[Dict[str, Any]], list[Dict[str, Any]]]:
    goals: list[Dict[str, Any]] = []
    cards: list[Dict[str, Any]] = []
    for event in events:
        event_type = _safe_str(event.get("type")).lower()
        team = _team_name(((event.get("team") or {}).get("name")))
        player = _safe_str((event.get("player") or {}).get("name"))
        minute = _safe_int((event.get("time") or {}).get("elapsed"))
        normalised_type = _event_type(event)
        if event_type == "goal":
            goal = {
                "minute": minute,
                "team": team,
                "player": player,
                "type": normalised_type,
            }
            assist = _safe_str((event.get("assist") or {}).get("name"))
            if assist:
                goal["assist"] = assist
            goals.append(goal)
        elif event_type == "card":
            cards.append(
                {
                    "minute": minute,
                    "team": team,
                    "player": player,
                    "type": normalised_type,
                }
            )
    return goals, cards


def _stats_value(stats: list[Dict[str, Any]], label: str, default: int | float = 0) -> int | float:
    item = next((entry for entry in stats if entry.get("type") == label), None)
    value = (item or {}).get("value")
    if isinstance(default, float):
        return _safe_float(value, default)
    return _safe_int(value, int(default))


def _normalise_statistics(payload: Dict[str, Any]) -> Dict[str, Any]:
    response = payload.get("response") or []
    if len(response) < 2:
        return {}
    home_stats = response[0].get("statistics") or []
    away_stats = response[1].get("statistics") or []
    return {
        "possession_home": _stats_value(home_stats, "Ball Possession", 0.0),
        "possession_away": _stats_value(away_stats, "Ball Possession", 0.0),
        "shots_home": _stats_value(home_stats, "Total Shots"),
        "shots_away": _stats_value(away_stats, "Total Shots"),
        "shots_on_target_home": _stats_value(home_stats, "Shots on Goal"),
        "shots_on_target_away": _stats_value(away_stats, "Shots on Goal"),
        "corners_home": _stats_value(home_stats, "Corner Kicks"),
        "corners_away": _stats_value(away_stats, "Corner Kicks"),
        "fouls_home": _stats_value(home_stats, "Fouls"),
        "fouls_away": _stats_value(away_stats, "Fouls"),
        "yellow_cards_home": _stats_value(home_stats, "Yellow Cards"),
        "yellow_cards_away": _stats_value(away_stats, "Yellow Cards"),
    }


def _normalise_lineups(payload: Dict[str, Any]) -> list[Dict[str, Any]]:
    lineups = []
    for item in payload.get("response") or []:
        lineups.append(
            {
                "team": _team_name(((item.get("team") or {}).get("name"))),
                "formation": item.get("formation"),
                "startXI": [
                    {
                        "name": ((player.get("player") or {}).get("name")),
                        "number": ((player.get("player") or {}).get("number")),
                        "pos": ((player.get("player") or {}).get("pos")),
                    }
                    for player in item.get("startXI") or []
                ],
                "substitutes": [
                    {
                        "name": ((player.get("player") or {}).get("name")),
                        "number": ((player.get("player") or {}).get("number")),
                        "pos": ((player.get("player") or {}).get("pos")),
                    }
                    for player in item.get("substitutes") or []
                ],
            }
        )
    return lineups


def _should_fetch_details(match_date: str | None, status: str) -> bool:
    if status not in {"completed", "live"}:
        return False
    if os.getenv("API_FOOTBALL_FETCH_DETAILS", "true").lower() in {"0", "false", "no"}:
        return False
    try:
        parsed = datetime.fromisoformat(str(match_date).replace("Z", "+00:00"))
    except ValueError:
        return False
    now = _now()
    days_back = max(_safe_int(os.getenv("API_FOOTBALL_DETAIL_DAYS_BACK"), 7), 0)
    days_forward = max(_safe_int(os.getenv("API_FOOTBALL_DETAIL_DAYS_FORWARD"), 1), 0)
    return now - timedelta(days=days_back) <= parsed.astimezone(SHANGHAI_TZ) <= now + timedelta(days=days_forward)


def _fixture_to_match(item: Dict[str, Any]) -> Dict[str, Any]:
    fixture = item.get("fixture") or {}
    teams = item.get("teams") or {}
    goals = item.get("goals") or {}
    league = item.get("league") or {}
    status = _normalise_fixture_status(((fixture.get("status") or {}).get("short")))
    fixture_id = _safe_int(fixture.get("id"))
    match_date = _normalise_match_date(fixture.get("date"))
    venue = fixture.get("venue") or {}
    match = {
        "id": fixture_id,
        "api_football_fixture_id": fixture_id,
        "home_team": _team_name(((teams.get("home") or {}).get("name"))),
        "away_team": _team_name(((teams.get("away") or {}).get("name"))),
        "group": None,
        "stage": league.get("round"),
        "round": None,
        "match_date": match_date,
        "venue": ", ".join(part for part in [venue.get("name"), venue.get("city")] if part),
        "status": status,
        "home_score": goals.get("home") if goals.get("home") is not None else None,
        "away_score": goals.get("away") if goals.get("away") is not None else None,
        "report": {
            "attendance": 0,
            "referee": fixture.get("referee") or "待官方确认",
            "player_of_match": "待官方确认",
            "lineups": [],
            "goals": [],
            "cards": [],
            "stats": {},
            "notes": ["API-Football official feed"],
        },
    }
    if _should_fetch_details(match_date, status):
        events = _api_get("/fixtures/events", {"fixture": fixture_id})
        goals_list, cards = _normalise_events(events.get("response") or [])
        match["report"]["goals"] = goals_list
        match["report"]["cards"] = cards
        match["report"]["stats"] = _normalise_statistics(_api_get("/fixtures/statistics", {"fixture": fixture_id}))
        match["report"]["lineups"] = _normalise_lineups(_api_get("/fixtures/lineups", {"fixture": fixture_id}))
    return match


def fetch_api_football_match_feed() -> Dict[str, Any]:
    payload = _api_get("/fixtures", {**_league_params(), "timezone": "Asia/Shanghai"})
    return {
        "source": "api_football",
        "last_updated": _now_iso(),
        "matches": [_fixture_to_match(item) for item in payload.get("response") or []],
    }


def _new_player(name: str, team: str, position: str = "Player") -> Dict[str, Any]:
    return {
        "name": name,
        "flagCode": "",
        "country": team,
        "team": team,
        "position": position or "Player",
        "tournaments": [2026],
        "goals": 0,
        "assists": 0,
        "appearances": 0,
        "yellowCards": 0,
        "redCards": 0,
        "minutesPlayed": 0,
        "yearlyStats": {
            2026: {
                "goals": 0,
                "assists": 0,
                "appearances": 0,
                "yellowCards": 0,
                "redCards": 0,
            }
        },
    }


def _player_key(team: str, name: str) -> str:
    return f"{team}:{name}".lower()


def _merge_player(players: Dict[str, Dict[str, Any]], entry: Dict[str, Any]) -> Dict[str, Any] | None:
    stats = (entry.get("statistics") or [{}])[0]
    player = entry.get("player") or {}
    name = _safe_str(player.get("name"))
    if not name:
        return None
    team = _team_name(((stats.get("team") or {}).get("name")))
    games = stats.get("games") or {}
    goals = stats.get("goals") or {}
    cards = stats.get("cards") or {}
    key = _player_key(team, name)
    current = players.setdefault(key, _new_player(name, team, _safe_str(games.get("position"))))
    current["position"] = _safe_str(games.get("position")) or current["position"]
    current["appearances"] = max(current["appearances"], _safe_int(games.get("appearences")))
    current["minutesPlayed"] = max(current["minutesPlayed"], _safe_int(games.get("minutes")))
    current["goals"] = max(current["goals"], _safe_int(goals.get("total")))
    current["assists"] = max(current["assists"], _safe_int(goals.get("assists")))
    current["yellowCards"] = max(current["yellowCards"], _safe_int(cards.get("yellow")))
    current["redCards"] = max(current["redCards"], _safe_int(cards.get("red")))
    current["yearlyStats"][2026].update(
        {
            "goals": current["goals"],
            "assists": current["assists"],
            "appearances": current["appearances"],
            "yellowCards": current["yellowCards"],
            "redCards": current["redCards"],
        }
    )
    return current


def normalise_api_football_leaderboards(payloads: Dict[str, Dict[str, Any]], fetched_at: str | None = None) -> Dict[str, Any]:
    players: Dict[str, Dict[str, Any]] = {}
    for name in ("topscorers", "topassists", "topyellowcards", "topredcards"):
        for entry in (payloads.get(name) or {}).get("response") or []:
            _merge_player(players, entry)

    all_players = list(players.values())
    scorers = sorted(
        (player for player in all_players if player["goals"] > 0),
        key=lambda player: (-player["goals"], -player["assists"], player["name"]),
    )
    assists = sorted(
        (player for player in all_players if player["assists"] > 0),
        key=lambda player: (-player["assists"], -player["goals"], player["name"]),
    )
    return {
        "source": "api_football",
        "last_updated": fetched_at or _now_iso(),
        "summary": {
            "completed_match_count": 0,
            "goal_event_count": sum(player["goals"] for player in all_players),
            "assist_event_count": sum(player["assists"] for player in all_players),
            "player_count": len(all_players),
        },
        "players": all_players,
        "players_by_name": {player["name"]: player for player in all_players},
        "scorers": scorers,
        "assists": assists,
    }


def fetch_api_football_leaderboards() -> Dict[str, Any]:
    fetched_at = _now_iso()
    payloads = {
        "topscorers": _api_get("/players/topscorers", _league_params()),
        "topassists": _api_get("/players/topassists", _league_params()),
        "topyellowcards": _api_get("/players/topyellowcards", _league_params()),
        "topredcards": _api_get("/players/topredcards", _league_params()),
    }
    return normalise_api_football_leaderboards(payloads, fetched_at=fetched_at)


def _normalise_injury_item(item: Dict[str, Any]) -> Dict[str, Any]:
    player = item.get("player") or {}
    team = item.get("team") or {}
    fixture = item.get("fixture") or {}
    league = item.get("league") or {}
    return {
        "team": _team_name(team.get("name")),
        "player": _safe_str(player.get("name")),
        "reason": _safe_str(player.get("reason")) or _safe_str(player.get("type")) or "unavailable",
        "type": _safe_str(player.get("type")) or "injury",
        "fixture_id": fixture.get("id"),
        "match_date": _normalise_match_date(fixture.get("date")),
        "league": league.get("name"),
        "source": "api_football_injuries",
    }


def fetch_api_football_injury_feed(match_date: str | None = None) -> Dict[str, Any]:
    params = dict(_league_params())
    if match_date:
        try:
            parsed = datetime.fromisoformat(str(match_date).replace("Z", "+00:00"))
            params["date"] = parsed.astimezone(SHANGHAI_TZ).date().isoformat()
        except ValueError:
            pass
    payload = _api_get("/injuries", params)
    teams: Dict[str, Dict[str, Any]] = {}
    for raw_item in payload.get("response") or []:
        item = _normalise_injury_item(raw_item)
        team_name = item.get("team")
        player_name = item.get("player")
        if not team_name or not player_name:
            continue
        team_status = teams.setdefault(
            team_name,
            {
                "unavailable_players": [],
                "doubtful_players": [],
                "items": [],
                "source": "api_football_injuries",
                "note": "API-Football injuries endpoint",
            },
        )
        reason_text = str(item.get("reason") or "")
        entry = f"{player_name}（{reason_text}）" if reason_text else player_name
        if "doubt" in reason_text.casefold() or "question" in reason_text.casefold():
            team_status["doubtful_players"].append(entry)
        else:
            team_status["unavailable_players"].append(entry)
        team_status["items"].append(item)

    return {
        "source": "api_football_injuries",
        "source_url": "https://www.api-football.com/documentation-v3#tag/Injuries",
        "last_updated": _now_iso(),
        "teams": teams,
    }
