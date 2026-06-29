from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional


DEFAULT_PRE_WORLD_CUP_HISTORY_PATH = (
    Path(__file__).resolve().parents[1] / "data" / "pre_worldcup_official_matches.json"
)


def _rows_from_payload(payload: Any) -> List[Dict[str, Any]]:
    rows = payload.get("matches") if isinstance(payload, Mapping) else payload
    if not isinstance(rows, list):
        return []
    return [dict(item) for item in rows if isinstance(item, Mapping)]


def load_pre_world_cup_official_matches(path: Optional[Any] = None) -> List[Dict[str, Any]]:
    configured = path or os.environ.get("PRE_WORLD_CUP_OFFICIAL_MATCHES_PATH")
    source_path = Path(configured) if configured else DEFAULT_PRE_WORLD_CUP_HISTORY_PATH
    if not source_path.exists():
        return []
    try:
        payload = json.loads(source_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return _rows_from_payload(payload)
