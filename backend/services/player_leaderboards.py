from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Iterable


COUNTED_SCORING_TYPES = {"goal", "penalty", "stoppage_time_goal"}


def _safe_str(value: Any) -> str:
    return str(value or "").strip()


def _player_key(team: str, name: str) -> str:
    return f"{team}:{name}".lower()


def _new_player(name: str, team: str, position: str = "球员") -> Dict[str, Any]:
    return {
        "name": name,
        "flagCode": "",
        "country": team,
        "team": team,
        "position": position,
        "tournaments": [2026],
        "goals": 0,
        "assists": 0,
        "appearances": 1,
        "yellowCards": 0,
        "redCards": 0,
        "minutesPlayed": 90,
        "yearlyStats": {
            2026: {
                "goals": 0,
                "assists": 0,
                "appearances": 1,
                "yellowCards": 0,
                "redCards": 0,
            }
        },
    }


def _ensure_player(players: Dict[str, Dict[str, Any]], name: str, team: str, position: str = "球员") -> Dict[str, Any]:
    key = _player_key(team, name)
    if key not in players:
        players[key] = _new_player(name=name, team=team, position=position)
    return players[key]


def _is_countable_match(match: Dict[str, Any]) -> bool:
    return match.get("status") in {"completed", "live"}


def _normalise_goal_type(value: Any) -> str:
    return _safe_str(value or "goal").lower()


def _match_event_key(match: Dict[str, Any], item: Dict[str, Any], event_type: str) -> tuple[str, str, str, str, str, str]:
    return (
        _safe_str(match.get("id")),
        event_type,
        _safe_str(item.get("minute")),
        _safe_str(item.get("team")).lower(),
        _safe_str(item.get("player")).lower(),
        _safe_str(item.get("type")).lower(),
    )


def build_player_leaderboards(matches: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    """Build authoritative 2026 player leaderboards from merged live matches.

    The input is expected to be the same merged match payload returned by
    merge_live_matches(): official/live feed data should already have priority
    over public backfills and static schedule rows.
    """
    players: Dict[str, Dict[str, Any]] = {}
    completed_match_count = 0
    goal_event_count = 0
    assist_event_count = 0
    seen_goal_events: set[tuple[str, str, str, str, str, str]] = set()
    seen_card_events: set[tuple[str, str, str, str, str, str]] = set()

    for match in matches:
        if not _is_countable_match(match):
            continue
        report = match.get("report") if isinstance(match.get("report"), dict) else {}
        completed_match_count += 1

        for goal in report.get("goals") or []:
            if not isinstance(goal, dict):
                continue
            goal_key = _match_event_key(match, goal, "goal")
            if goal_key in seen_goal_events:
                continue
            seen_goal_events.add(goal_key)
            goal_type = _normalise_goal_type(goal.get("type"))
            if goal_type == "own_goal":
                continue
            if goal_type not in COUNTED_SCORING_TYPES:
                continue

            team = _safe_str(goal.get("team"))
            scorer_name = _safe_str(goal.get("player"))
            if scorer_name:
                scorer = _ensure_player(players, scorer_name, team)
                scorer["goals"] += 1
                scorer["yearlyStats"][2026]["goals"] += 1
                goal_event_count += 1

            assist_name = _safe_str(goal.get("assist"))
            if assist_name:
                assister = _ensure_player(players, assist_name, team)
                assister["assists"] += 1
                assister["yearlyStats"][2026]["assists"] += 1
                assist_event_count += 1

        for card in report.get("cards") or []:
            if not isinstance(card, dict):
                continue
            card_key = _match_event_key(match, card, "card")
            if card_key in seen_card_events:
                continue
            seen_card_events.add(card_key)
            player_name = _safe_str(card.get("player"))
            if not player_name:
                continue
            team = _safe_str(card.get("team"))
            player = _ensure_player(players, player_name, team)
            card_type = _safe_str(card.get("type")).lower()
            if card_type == "red_card":
                player["redCards"] += 1
                player["yearlyStats"][2026]["redCards"] += 1
            elif card_type == "yellow_card":
                player["yellowCards"] += 1
                player["yearlyStats"][2026]["yellowCards"] += 1

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
        "summary": {
            "completed_match_count": completed_match_count,
            "goal_event_count": goal_event_count,
            "assist_event_count": assist_event_count,
            "player_count": len(all_players),
        },
        "players": deepcopy(all_players),
        "players_by_name": {player["name"]: deepcopy(player) for player in all_players},
        "scorers": deepcopy(scorers),
        "assists": deepcopy(assists),
    }
