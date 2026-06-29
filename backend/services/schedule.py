from __future__ import annotations

import json
import os
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List


def _default_schedule_path() -> Path:
    return Path(__file__).resolve().parent.parent / "data" / "matches.schedule.json"


def schedule_path() -> Path:
    return Path(os.getenv("MATCH_SCHEDULE_PATH", str(_default_schedule_path())))


def load_schedule_matches() -> List[Dict[str, Any]]:
    path = schedule_path()
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as file:
        payload = json.load(file)
    matches = payload.get("matches", [])
    if not isinstance(matches, list):
        raise ValueError("schedule feed must contain a matches array")
    return [deepcopy(match) for match in matches if isinstance(match, dict)]


def schedule_matches_by_id() -> Dict[int, Dict[str, Any]]:
    matches_by_id: Dict[int, Dict[str, Any]] = {}
    for match in load_schedule_matches():
        try:
            matches_by_id[int(match["id"])] = match
        except (KeyError, TypeError, ValueError):
            continue
    return matches_by_id


def enrich_match_from_schedule(match: Dict[str, Any]) -> Dict[str, Any]:
    enriched = deepcopy(match)
    try:
        match_id = int(enriched.get("id"))
    except (TypeError, ValueError):
        return enriched

    schedule_match = schedule_matches_by_id().get(match_id)
    if not schedule_match:
        return enriched

    merged = deepcopy(schedule_match)
    for key, value in enriched.items():
        if value is not None:
            merged[key] = value
    return merged
