from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime, timedelta, timezone
from html import unescape
from pathlib import Path
from typing import Any, Dict, List
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


TRANSFERMARKT_BASE_URL = "https://www.transfermarkt.us"
TRANSFERMARKT_PARTICIPANTS_URL = "https://www.transfermarkt.us/world-cup/teilnehmer/pokalwettbewerb/FIWC"
HISTORICAL_INJURY_CSV_URL = (
    "https://raw.githubusercontent.com/salimt/football-datasets/main/"
    "datalake/transfermarkt/player_injuries/player_injuries.csv"
)
SHANGHAI_TZ = timezone(timedelta(hours=8))
CACHE_SECONDS = int(os.getenv("PUBLIC_INJURY_CACHE_SECONDS", "1800"))
REQUEST_TIMEOUT_SECONDS = int(os.getenv("PUBLIC_INJURY_TIMEOUT_SECONDS", "6"))

_FETCH_CACHE: dict[str, tuple[float, Dict[str, Any]]] = {}


def _now_iso() -> str:
    return datetime.now(SHANGHAI_TZ).replace(microsecond=0).isoformat()


def _sources_path() -> Path:
    return Path(__file__).resolve().parent.parent / "data" / "public_injury_sources.json"


def _read_sources() -> Dict[str, Any]:
    with _sources_path().open("r", encoding="utf-8") as file:
        return json.load(file)


def public_injury_sources_enabled() -> bool:
    raw = os.getenv("PUBLIC_INJURY_SOURCES_ENABLED", "true").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def _clean_html(value: str) -> str:
    text = re.sub(r"<script\b[^>]*>.*?</script>", " ", value, flags=re.I | re.S)
    text = re.sub(r"<style\b[^>]*>.*?</style>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    text = unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _fetch_html(url: str) -> str:
    request = Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def _table_after_heading(html: str, heading: str, until_heading: str | None = None) -> str:
    heading_match = re.search(
        rf"<h2[^>]*>\s*{re.escape(heading)}\s*</h2>",
        html,
        flags=re.I | re.S,
    )
    if not heading_match:
        return ""
    section = html[heading_match.end() :]
    if until_heading:
        next_match = re.search(
            rf"<h2[^>]*>\s*{re.escape(until_heading)}\s*</h2>",
            section,
            flags=re.I | re.S,
        )
        if next_match:
            section = section[: next_match.start()]
    return section


def _player_rows(table_html: str) -> List[str]:
    matches = list(re.finditer(r"<tr\s+class=\"(?:odd|even)\"[^>]*>", table_html, re.I | re.S))
    rows: List[str] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(table_html)
        rows.append(table_html[match.start() : end])
    return rows


def _parse_player_row(row_html: str) -> Dict[str, str] | None:
    player_match = re.search(
        r"<a\s+title=\"([^\"]+)\"\s+href=\"/[^\"]+/profil/spieler/(\d+)\"",
        row_html,
        flags=re.I | re.S,
    )
    if not player_match:
        return None

    tail = row_html.split("</table>", 1)[-1] if "</table>" in row_html else row_html
    cells = [_clean_html(cell) for cell in re.findall(r"<td[^>]*>(.*?)</td>", tail, re.I | re.S)]
    reason = cells[1] if len(cells) > 1 else ""
    since = cells[2] if len(cells) > 2 else ""
    expected_return = cells[3] if len(cells) > 3 else ""
    missed_matches = cells[4] if len(cells) > 4 else ""

    return {
        "name": _clean_html(player_match.group(1)),
        "player_id": player_match.group(2),
        "reason": reason,
        "since": since,
        "expected_return": expected_return,
        "missed_matches": missed_matches,
    }


def parse_transfermarkt_injury_page(html: str) -> Dict[str, List[Dict[str, str]]]:
    injury_table = _table_after_heading(html, "Suspensions and injuries", "Risk of suspension")
    risk_table = _table_after_heading(html, "Risk of suspension")
    return {
        "unavailable": [
            player
            for row in _player_rows(injury_table)
            for player in [_parse_player_row(row)]
            if player is not None
        ],
        "card_risk": [
            player
            for row in _player_rows(risk_table)
            for player in [_parse_player_row(row)]
            if player is not None
        ],
    }


def _player_label(player: Dict[str, str]) -> str:
    reason = player.get("reason", "").strip()
    if reason:
        return f"{player['name']}（{reason}）"
    return player["name"]


def _injury_url(team_info: Dict[str, Any]) -> str:
    return f"{TRANSFERMARKT_BASE_URL}/{team_info['path']}/sperrenundverletzungen/verein/{team_info['team_id']}"


def fetch_transfermarkt_team_status(team_name: str) -> Dict[str, Any] | None:
    if not public_injury_sources_enabled():
        return None

    sources = _read_sources()
    team_info = sources.get("teams", {}).get(team_name)
    if not team_info:
        return {
            "team": team_name,
            "unavailable_players": [],
            "doubtful_players": [],
            "card_risk_players": [],
            "source": "transfermarkt_public",
            "source_url": TRANSFERMARKT_PARTICIPANTS_URL,
            "last_updated": _now_iso(),
            "note": "公开伤停源暂未匹配到该队，保留人工复核",
            "error": "team_not_mapped",
        }

    url = _injury_url(team_info)
    cached = _FETCH_CACHE.get(url)
    if cached and time.time() - cached[0] < CACHE_SECONDS:
        return dict(cached[1])

    try:
        parsed = parse_transfermarkt_injury_page(_fetch_html(url))
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        return {
            "team": team_name,
            "unavailable_players": [],
            "doubtful_players": [],
            "card_risk_players": [],
            "source": "transfermarkt_public",
            "source_url": url,
            "last_updated": _now_iso(),
            "note": "公开伤停源暂时读取失败，保留人工复核",
            "error": str(exc),
        }

    unavailable = [_player_label(player) for player in parsed["unavailable"]]
    card_risk = [_player_label(player) for player in parsed["card_risk"]]
    note = (
        f"公开源当前记录缺阵/停赛 {len(unavailable)} 人，停赛风险 {len(card_risk)} 人"
        if unavailable or card_risk
        else "公开源暂无伤病、停赛或停赛风险记录"
    )
    result = {
        "team": team_name,
        "unavailable_players": unavailable,
        "doubtful_players": [],
        "card_risk_players": card_risk,
        "source": "transfermarkt_public",
        "source_url": url,
        "last_updated": _now_iso(),
        "note": note,
        "provider_team_name": team_info["name_en"],
    }
    _FETCH_CACHE[url] = (time.time(), dict(result))
    return result


def get_public_match_injury_feed(home_team: str, away_team: str, match_date: str | None = None) -> Dict[str, Any] | None:
    if not public_injury_sources_enabled():
        return None

    home_status = fetch_transfermarkt_team_status(home_team)
    away_status = fetch_transfermarkt_team_status(away_team)
    if not home_status and not away_status:
        return None

    last_updated = _now_iso()
    teams: Dict[str, Any] = {}
    if home_status:
        teams[home_team] = home_status
        last_updated = str(home_status.get("last_updated") or last_updated)
    if away_status:
        teams[away_team] = away_status
        last_updated = str(away_status.get("last_updated") or last_updated)

    return {
        "source": "transfermarkt_public",
        "source_url": TRANSFERMARKT_PARTICIPANTS_URL,
        "historical_injury_csv_url": HISTORICAL_INJURY_CSV_URL,
        "last_updated": last_updated,
        "match_date": match_date,
        "message": "已读取公开伤停页；作为赛前风险提示，关键缺阵仍建议人工复核",
        "teams": teams,
    }
