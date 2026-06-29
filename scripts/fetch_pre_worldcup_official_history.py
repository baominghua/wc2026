from __future__ import annotations

import json
import sys
import time
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple


ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = ROOT / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from services.prediction_model import TEAM_ALIASES  # noqa: E402


USER_AGENT = "Mozilla/5.0 (compatible; wc2026-data-maintenance/1.0)"
FOTMOB_TEAM_URL = "https://www.fotmob.com/api/data/teams?id={team_id}"
FOTMOB_LEAGUE_URL = "https://www.fotmob.com/api/data/leagues?id={league_id}"
FOTMOB_MATCH_URL = "https://www.fotmob.com/api/data/matchDetails?matchId={match_id}"
WORLD_CUP_START_UTC = "2026-06-11T00:00:00Z"

OFFICIAL_LEAGUES = [
    10195,  # World Cup Qualification UEFA
    10196,  # World Cup Qualification CAF
    10197,  # World Cup Qualification AFC
    10198,  # World Cup Qualification CONCACAF
    10199,  # World Cup Qualification CONMEBOL
    10200,  # World Cup Qualification OFC
    10201,  # World Cup Qualification Inter-Confederation Playoff
    298,  # CONCACAF Gold Cup
    289,  # Africa Cup of Nations
    10242,  # FIFA Arab Cup
]

STAT_KEY_MAP = {
    "total_shots": ("shots_home", "shots_away"),
    "ShotsOnTarget": ("shots_on_target_home", "shots_on_target_away"),
    "corners": ("corners_home", "corners_away"),
    "yellow_cards": ("yellow_cards_home", "yellow_cards_away"),
    "red_cards": ("red_cards_home", "red_cards_away"),
    "fouls": ("fouls_committed_home", "fouls_committed_away"),
}

CORE_TECHNICAL_KEYS = {
    "shots_home",
    "shots_away",
    "shots_on_target_home",
    "shots_on_target_away",
    "corners_home",
    "corners_away",
    "yellow_cards_home",
    "yellow_cards_away",
}


def _get_json(url: str, retries: int = 3) -> Dict[str, Any]:
    last_error: Optional[BaseException] = None
    for attempt in range(retries):
        try:
            request = urllib.request.Request(
                url,
                headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
            )
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except BaseException as exc:  # pragma: no cover - network retry guard
            last_error = exc
            time.sleep(0.7 + attempt * 0.8)
    raise RuntimeError(f"Failed to fetch {url}: {last_error}")


def _to_number(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return value
    text = str(value).strip().replace("%", "")
    if " " in text:
        text = text.split(" ", 1)[0]
    try:
        parsed = float(text)
    except ValueError:
        return None
    return int(parsed) if parsed.is_integer() else parsed


def _score_pair(score: Any) -> Tuple[Optional[int], Optional[int]]:
    if not isinstance(score, str):
        return None, None
    parts = score.replace("–", "-").split("-")
    if len(parts) < 2:
        return None, None
    try:
        return int(parts[0].strip()), int(parts[1].strip().split()[0])
    except ValueError:
        return None, None


def _round_number(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _zh_name(name: Any) -> str:
    text = str(name or "")
    return TEAM_ALIASES.get(text, text)


def _world_cup_team_ids() -> List[Dict[str, Any]]:
    data = _get_json(FOTMOB_TEAM_URL.format(team_id=6706))
    teams: List[Dict[str, Any]] = []
    seen = set()
    for competition in data.get("overview", {}).get("table", []):
        for table in competition.get("data", {}).get("tables", []):
            for row in table.get("table", {}).get("all", []):
                team_id = str(row.get("id") or "")
                if not team_id or team_id in seen:
                    continue
                seen.add(team_id)
                teams.append(
                    {
                        "fotmob_team_id": team_id,
                        "name_en": row.get("name"),
                        "name_zh": _zh_name(row.get("name")),
                        "group": table.get("leagueName"),
                    }
                )
    return teams


def _candidate_matches(teams: Iterable[Mapping[str, Any]]) -> Dict[str, Dict[str, Dict[str, Any]]]:
    team_ids = {str(team["fotmob_team_id"]) for team in teams}
    by_team: Dict[str, Dict[str, Dict[str, Any]]] = {team_id: {} for team_id in team_ids}

    for league_id in OFFICIAL_LEAGUES:
        data = _get_json(FOTMOB_LEAGUE_URL.format(league_id=league_id))
        league_name = (data.get("details") or {}).get("name") or f"league-{league_id}"
        for match in (data.get("fixtures") or {}).get("allMatches") or []:
            status = match.get("status") or {}
            utc_time = str(status.get("utcTime") or "")
            if not status.get("finished") or not utc_time or utc_time >= WORLD_CUP_START_UTC:
                continue
            match_id = str(match.get("id") or "")
            if not match_id:
                continue
            home = match.get("home") or {}
            away = match.get("away") or {}
            home_id = str(home.get("id") or "")
            away_id = str(away.get("id") or "")
            home_score, away_score = _score_pair(status.get("scoreStr"))
            if home_score is None or away_score is None:
                continue

            record = {
                "match_id": match_id,
                "league_id": league_id,
                "competition": league_name,
                "match_date": utc_time,
                "round": _round_number(match.get("roundName") or match.get("round")),
                "round_label": match.get("roundName") or match.get("round"),
                "home_team_id": home_id,
                "away_team_id": away_id,
                "home_team_en": home.get("name"),
                "away_team_en": away.get("name"),
                "home_team": _zh_name(home.get("name")),
                "away_team": _zh_name(away.get("name")),
                "home_score": home_score,
                "away_score": away_score,
                "score": status.get("scoreStr"),
            }
            if home_id in by_team:
                by_team[home_id][match_id] = record
            if away_id in by_team:
                by_team[away_id][match_id] = record
    return by_team


def _flatten_stats(match_details: Mapping[str, Any]) -> Dict[str, Any]:
    periods = ((match_details.get("content") or {}).get("stats") or {}).get("Periods") or {}
    groups = ((periods.get("All") or {}).get("stats")) or []
    raw: Dict[str, List[Any]] = {}
    for group in groups:
        for item in group.get("stats") or []:
            key = item.get("key")
            values = item.get("stats")
            if key not in STAT_KEY_MAP or not isinstance(values, list) or len(values) < 2:
                continue
            normalized = [_to_number(values[0]), _to_number(values[1])]
            current = raw.get(key)
            if current is None or all(value is None for value in current):
                raw[key] = normalized
            elif any(value is not None for value in normalized) and any(value is None for value in current):
                raw[key] = normalized

    stats: Dict[str, Any] = {}
    for source_key, (home_key, away_key) in STAT_KEY_MAP.items():
        values = raw.get(source_key)
        if not values:
            continue
        home_value, away_value = values[0], values[1]
        if home_value is not None:
            stats[home_key] = home_value
        if away_value is not None:
            stats[away_key] = away_value

    if stats and "red_cards_home" not in stats:
        stats["red_cards_home"] = 0
        stats["red_cards_away"] = 0
    return stats


def _build_rows() -> Dict[str, Any]:
    teams = _world_cup_team_ids()
    by_team = _candidate_matches(teams)
    selected_by_match: Dict[str, Dict[str, Any]] = {}
    coverage = []

    for team in teams:
        team_id = str(team["fotmob_team_id"])
        candidates = sorted(
            by_team.get(team_id, {}).values(),
            key=lambda item: item["match_date"],
            reverse=True,
        )
        selected = candidates[:3]
        if len(selected) < 3:
            raise RuntimeError(f"{team['name_zh']} only has {len(selected)} official pre-World-Cup samples")
        for match in selected:
            selected_by_match.setdefault(match["match_id"], dict(match)).setdefault("selected_for_teams", [])
            selected_by_match[match["match_id"]]["selected_for_teams"].append(team["name_zh"])
        coverage.append(
            {
                "team": team["name_zh"],
                "name_en": team["name_en"],
                "fotmob_team_id": team_id,
                "sample_count": len(selected),
                "selected_match_ids": [match["match_id"] for match in selected],
            }
        )

    rows: List[Dict[str, Any]] = []
    for match_id, match in sorted(selected_by_match.items(), key=lambda item: (item[1]["match_date"], item[0])):
        details = _get_json(FOTMOB_MATCH_URL.format(match_id=match_id))
        general = details.get("general") or {}
        stats = _flatten_stats(details)
        technical_count = len(CORE_TECHNICAL_KEYS.intersection(stats.keys()))
        if CORE_TECHNICAL_KEYS.issubset(stats.keys()):
            quality = "A"
        elif stats:
            quality = "B"
        else:
            quality = "C"

        rows.append(
            {
                "id": f"fotmob-{match_id}",
                "fotmob_match_id": match_id,
                "home_team": match["home_team"],
                "away_team": match["away_team"],
                "home_team_en": match["home_team_en"],
                "away_team_en": match["away_team_en"],
                "competition": general.get("leagueName") or match["competition"],
                "league_id": match["league_id"],
                "is_official": True,
                "status": "completed",
                "home_score": match["home_score"],
                "away_score": match["away_score"],
                "match_date": match["match_date"],
                "round": match.get("round"),
                "round_label": match.get("round_label"),
                "data_quality": quality,
                "technical_stats_keys": sorted(stats.keys()),
                "technical_core_key_count": technical_count,
                "selected_for_teams": sorted(set(match.get("selected_for_teams") or [])),
                "source": "FotMob matchDetails",
                "source_url": FOTMOB_MATCH_URL.format(match_id=match_id),
                "report": {"stats": stats},
            }
        )

    technical_by_team: Dict[str, int] = defaultdict(int)
    score_by_team: Dict[str, int] = defaultdict(int)
    for row in rows:
        stats = row.get("report", {}).get("stats", {})
        has_core = CORE_TECHNICAL_KEYS.issubset(stats.keys())
        for team in (row["home_team"], row["away_team"]):
            if team in {item["name_zh"] for item in teams}:
                score_by_team[team] += 1
                if has_core:
                    technical_by_team[team] += 1

    for item in coverage:
        item["score_sample_matches"] = score_by_team[item["team"]]
        item["technical_complete_sample_matches"] = technical_by_team[item["team"]]

    return {
        "source": "FotMob matchDetails",
        "scope": "Last three official pre-World-Cup matches for all 48 project teams; friendlies excluded.",
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "official_league_ids": OFFICIAL_LEAGUES,
        "team_count": len(teams),
        "team_coverage": coverage,
        "matches": rows,
    }


def main() -> None:
    output_path = BACKEND_ROOT / "data" / "pre_worldcup_official_matches.json"
    payload = _build_rows()
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {len(payload['matches'])} matches for {payload['team_count']} teams to {output_path}")
    incomplete = [
        item
        for item in payload["team_coverage"]
        if item.get("score_sample_matches", 0) < 3 or item.get("technical_complete_sample_matches", 0) < 3
    ]
    if incomplete:
        print("teams with incomplete technical coverage:")
        for item in incomplete:
            print(
                f"- {item['team']}: score={item.get('score_sample_matches')}, "
                f"technical={item.get('technical_complete_sample_matches')}, matches={item['selected_match_ids']}"
            )


if __name__ == "__main__":
    main()
