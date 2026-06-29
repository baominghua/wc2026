from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
SQUAD_PATH = ROOT / "data" / "team_squads.json"

POSITION_GROUPS = ("goalkeepers", "defenders", "midfielders", "forwards")


def _norm(value: Any) -> str:
    return str(value or "").strip().casefold()


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


@lru_cache(maxsize=1)
def load_team_squads() -> dict[str, Any]:
    if not SQUAD_PATH.exists():
        return {"teams": {}}
    return json.loads(SQUAD_PATH.read_text(encoding="utf-8"))


def all_team_squads() -> dict[str, Mapping[str, Any]]:
    teams = load_team_squads().get("teams", {})
    return teams if isinstance(teams, dict) else {}


def get_team_squad(team: Any) -> Mapping[str, Any] | None:
    text = str(team or "").strip()
    if not text:
        return None
    squads = all_team_squads()
    code = text.upper()
    if code in squads:
        return squads[code]
    normalized = _norm(text)
    for squad in squads.values():
        if normalized in {
            _norm(squad.get("team")),
            _norm(squad.get("source_team_name")),
            _norm(squad.get("code")),
        }:
            return squad
    return None


def _players_by_group(squad: Mapping[str, Any], group: str) -> list[Mapping[str, Any]]:
    positions = squad.get("positions")
    if isinstance(positions, Mapping) and isinstance(positions.get(group), list):
        players = positions.get(group) or []
    else:
        players = [player for player in squad.get("players", []) if player.get("position_group") == group]
    return sorted(
        [player for player in players if isinstance(player, Mapping) and player.get("name")],
        key=lambda player: (-_to_int(player.get("caps")), -_to_int(player.get("goals")), _to_int(player.get("number"), 99)),
    )


def _formation_counts(formation: str) -> tuple[int, int, int]:
    numbers = [_to_int(part) for part in str(formation or "").split("-") if _to_int(part) > 0]
    if sum(numbers) != 10 or not numbers:
        return 4, 5, 1
    if len(numbers) == 3:
        return numbers[0], numbers[1], numbers[2]
    return numbers[0], sum(numbers[1:-1]), numbers[-1]


def squad_lineup(team: Any, formation: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    squad = get_team_squad(team)
    if not squad:
        return (), ()

    defenders_needed, midfielders_needed, forwards_needed = _formation_counts(formation)
    grouped = {group: _players_by_group(squad, group) for group in POSITION_GROUPS}
    starters: list[Mapping[str, Any]] = []
    if grouped["goalkeepers"]:
        starters.append(grouped["goalkeepers"][0])
    starters.extend(grouped["defenders"][:defenders_needed])
    starters.extend(grouped["midfielders"][:midfielders_needed])
    starters.extend(grouped["forwards"][:forwards_needed])

    starter_names = {player.get("name") for player in starters}
    if len(starters) < 11:
        for player in sorted(
            [player for player in squad.get("players", []) if player.get("name") not in starter_names],
            key=lambda player: (-_to_int(player.get("caps")), -_to_int(player.get("goals")), _to_int(player.get("number"), 99)),
        ):
            starters.append(player)
            starter_names.add(player.get("name"))
            if len(starters) >= 11:
                break

    bench = [player.get("name") for player in squad.get("players", []) if player.get("name") not in starter_names]
    return tuple(str(player.get("name")) for player in starters[:11]), tuple(str(name) for name in bench if name)


def squad_player_projections(team: Any) -> tuple[dict[str, Any], ...]:
    squad = get_team_squad(team)
    if not squad:
        return ()

    forwards = _players_by_group(squad, "forwards")
    midfielders = _players_by_group(squad, "midfielders")
    defenders = _players_by_group(squad, "defenders")
    candidates = [
        *(("FW", player) for player in forwards[:3]),
        *(("MF", player) for player in midfielders[:2]),
        *(("DF", player) for player in defenders[:1]),
    ]
    shares = (0.28, 0.22, 0.16, 0.10, 0.08, 0.06)
    projections: list[dict[str, Any]] = []
    for index, (position, player) in enumerate(candidates[:4]):
        goals = _to_int(player.get("goals"))
        caps = _to_int(player.get("caps"))
        if position == "FW":
            role = "终结候选"
            metric = f"官方26人名单前锋，国家队 {caps} 场 {goals} 球"
        elif position == "MF":
            role = "组织/二线"
            metric = f"官方26人名单中场，国家队 {caps} 场 {goals} 球"
        else:
            role = "定位球/后点"
            metric = f"官方26人名单后卫，国家队 {caps} 场 {goals} 球"
        projections.append(
            {
                "name": str(player.get("name")),
                "position": position,
                "role": role,
                "attack_share": shares[index],
                "key_metric": metric,
            }
        )
    return tuple(projections)
