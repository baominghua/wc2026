from __future__ import annotations

import json
import os
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Mapping, Optional


SNAPSHOT_FIELDS = {
    "home_win_probability",
    "draw_probability",
    "away_win_probability",
    "predicted_score",
    "possible_scores",
    "upset_prediction",
    "total_goals_prediction",
    "xg_home",
    "xg_away",
    "factors",
}


def _snapshot_path() -> Path:
    configured = os.environ.get("PREDICTION_SNAPSHOT_PATH")
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parents[1] / "data" / "prediction_snapshots.json"


def _parse_datetime(value: Any) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        parsed = value
    else:
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _now_utc(now: Optional[datetime]) -> datetime:
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    return current.astimezone(timezone.utc)


def _read_payload(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {"version": 1, "snapshots": {}}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"version": 1, "snapshots": {}}
    if not isinstance(payload, dict):
        return {"version": 1, "snapshots": {}}
    snapshots = payload.get("snapshots")
    if not isinstance(snapshots, dict):
        payload["snapshots"] = {}
    return payload


def _write_payload(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    tmp_path.replace(path)


def _prediction_payload(prediction: Mapping[str, Any]) -> Dict[str, Any]:
    return {key: deepcopy(prediction.get(key)) for key in SNAPSHOT_FIELDS if key in prediction}


def save_pre_match_prediction(
    match: Mapping[str, Any],
    prediction: Mapping[str, Any],
    scenario_settings: Optional[Mapping[str, Any]] = None,
    now: Optional[datetime] = None,
) -> bool:
    match_id = match.get("id")
    if match_id is None:
        return False
    kickoff = _parse_datetime(match.get("match_date"))
    if kickoff is None:
        return False
    if str(match.get("status") or "").lower() == "completed":
        return False
    saved_at = _now_utc(now)
    if saved_at >= kickoff:
        return False

    path = _snapshot_path()
    payload = _read_payload(path)
    snapshots = payload.setdefault("snapshots", {})
    snapshots[str(match_id)] = {
        "match_id": match_id,
        "home_team": match.get("home_team"),
        "away_team": match.get("away_team"),
        "match_date": match.get("match_date"),
        "saved_at": saved_at.isoformat(),
        "scenario_settings": dict(scenario_settings or {}),
        "prediction": _prediction_payload(prediction),
    }
    _write_payload(path, payload)
    return True


def load_prediction_snapshots() -> Dict[int, Dict[str, Any]]:
    payload = _read_payload(_snapshot_path())
    snapshots = payload.get("snapshots") if isinstance(payload, Mapping) else {}
    if not isinstance(snapshots, Mapping):
        return {}
    loaded: Dict[int, Dict[str, Any]] = {}
    for raw_id, snapshot in snapshots.items():
        try:
            match_id = int(raw_id)
        except (TypeError, ValueError):
            continue
        if not isinstance(snapshot, Mapping):
            continue
        prediction = snapshot.get("prediction")
        if isinstance(prediction, Mapping):
            loaded[match_id] = deepcopy(dict(prediction))
    return loaded
