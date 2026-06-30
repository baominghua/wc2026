from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import re
from typing import Any, Mapping


GROUP_STAGE_CUTOFF = datetime.fromisoformat("2026-06-29T00:00:00+08:00")

KNOCKOUT_STAGE_RANGES = (
    (73, 88, "Round of 32"),
    (89, 96, "Round of 16"),
    (97, 100, "Quarter-final"),
    (101, 102, "Semi-final"),
    (103, 103, "Third place"),
    (104, 104, "Final"),
)

GROUP_STAGE_MARKERS = (
    "group stage",
    "group-stage",
    "regular season",
    "league stage",
)

KNOCKOUT_PLACEHOLDER_PATTERN = re.compile(r"^([A-L][1-4]|1[A-L]|W\d+\??|L\d+\??)$")


def _has_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        stripped = value.strip()
        return bool(stripped) and stripped.lower() not in {"null", "none", "undefined"}
    return True


def _parse_datetime(value: Any) -> datetime | None:
    if not _has_value(value):
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _stage_from_match_id(value: Any) -> str | None:
    try:
        match_id = int(value)
    except (TypeError, ValueError):
        return None
    for start, end, stage in KNOCKOUT_STAGE_RANGES:
        if start <= match_id <= end:
            return stage
    return None


def _has_group(match: Mapping[str, Any]) -> bool:
    return _has_value(match.get("group"))


def _has_teams(match: Mapping[str, Any]) -> bool:
    return _has_value(match.get("home_team")) and _has_value(match.get("away_team"))


def _is_knockout_placeholder(value: Any) -> bool:
    return isinstance(value, str) and bool(KNOCKOUT_PLACEHOLDER_PATTERN.fullmatch(value.strip()))


def _has_placeholder_fixture(match: Mapping[str, Any]) -> bool:
    return _is_knockout_placeholder(match.get("home_team")) or _is_knockout_placeholder(match.get("away_team"))


def is_knockout_stage(stage: Any) -> bool:
    if not _has_value(stage):
        return False
    normalized = str(stage).strip().lower()
    return not any(marker in normalized for marker in GROUP_STAGE_MARKERS)


def infer_effective_stage(match: Mapping[str, Any]) -> str | None:
    stage = match.get("stage")
    if is_knockout_stage(stage):
        return str(stage).strip()

    if _has_group(match):
        return None

    stage_by_id = _stage_from_match_id(match.get("id"))
    if stage_by_id:
        return stage_by_id

    kickoff = _parse_datetime(match.get("match_date"))
    if kickoff and kickoff >= GROUP_STAGE_CUTOFF and _has_teams(match):
        return "Round of 32"

    return None


def normalize_match_stage(match: Mapping[str, Any]) -> dict[str, Any]:
    normalized = deepcopy(dict(match))
    effective_stage = infer_effective_stage(normalized)
    if effective_stage:
        normalized["stage"] = effective_stage
        if not _has_group(normalized):
            normalized["group"] = None
            if not _has_value(normalized.get("round")):
                normalized["round"] = None
        if _has_placeholder_fixture(normalized):
            normalized["fixture_status"] = "placeholder"
            normalized.setdefault(
                "fixture_message",
                "Knockout slot pending official confirmation; simulated bracket results are not used as real fixtures.",
            )
        else:
            normalized.setdefault("fixture_status", "confirmed")
    return normalized
