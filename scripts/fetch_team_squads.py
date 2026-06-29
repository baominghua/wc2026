from __future__ import annotations

import html
import json
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SOURCE_URL = "https://en.wikipedia.org/w/index.php?title=2026_FIFA_World_Cup_squads&action=raw"
SOURCE_PAGE_URL = "https://en.wikipedia.org/wiki/2026_FIFA_World_Cup_squads"
SOURCE_NAME = "Wikipedia - 2026 FIFA World Cup squads"

SOURCE_TEAM_CODES = {
    "Czech Republic": "CZE",
    "Mexico": "MEX",
    "South Africa": "RSA",
    "South Korea": "KOR",
    "Bosnia and Herzegovina": "BIH",
    "Canada": "CAN",
    "Qatar": "QAT",
    "Switzerland": "SUI",
    "Brazil": "BRA",
    "Haiti": "HAI",
    "Morocco": "MAR",
    "Scotland": "SCO",
    "Australia": "AUS",
    "Paraguay": "PAR",
    "Turkey": "TUR",
    "United States": "USA",
    "Cura\u00e7ao": "CUW",
    "Curacao": "CUW",
    "Ecuador": "ECU",
    "Germany": "GER",
    "Ivory Coast": "CIV",
    "Japan": "JPN",
    "Netherlands": "NED",
    "Sweden": "SWE",
    "Tunisia": "TUN",
    "Belgium": "BEL",
    "Egypt": "EGY",
    "Iran": "IRN",
    "New Zealand": "NZL",
    "Cape Verde": "CPV",
    "Saudi Arabia": "KSA",
    "Spain": "ESP",
    "Uruguay": "URU",
    "France": "FRA",
    "Iraq": "IRQ",
    "Norway": "NOR",
    "Senegal": "SEN",
    "Algeria": "ALG",
    "Argentina": "ARG",
    "Austria": "AUT",
    "Jordan": "JOR",
    "Colombia": "COL",
    "DR Congo": "COD",
    "Portugal": "POR",
    "Uzbekistan": "UZB",
    "Croatia": "CRO",
    "England": "ENG",
    "Ghana": "GHA",
    "Panama": "PAN",
}

POSITION_KEYS = {
    "GK": "goalkeepers",
    "DF": "defenders",
    "MF": "midfielders",
    "FW": "forwards",
}

BANNED_BY_CODE = {
    "FRA": {"Olivier Giroud", "Antoine Griezmann", "Giroud", "Griezmann"},
}


def _read_url(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "wc2026-squad-refresh/2.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


def _team_names_by_code() -> dict[str, str]:
    text = (ROOT / "frontend" / "src" / "services" / "wc2026-data.ts").read_text(encoding="utf-8")
    names: dict[str, str] = {}
    for match in re.finditer(r"name:\s*'([^']+)'.*?code:\s*'([A-Z]+)'", text):
        names[match.group(2)] = match.group(1)
    if len(names) < 48:
        raise RuntimeError(f"Expected at least 48 teams in wc2026-data.ts, found {len(names)}")
    return names


def _split_top_level(value: str) -> list[str]:
    parts: list[str] = []
    buf: list[str] = []
    brace_depth = 0
    bracket_depth = 0
    i = 0
    while i < len(value):
        if value.startswith("{{", i):
            brace_depth += 1
            buf.append("{{")
            i += 2
            continue
        if value.startswith("}}", i):
            brace_depth = max(0, brace_depth - 1)
            buf.append("}}")
            i += 2
            continue
        if value.startswith("[[", i):
            bracket_depth += 1
            buf.append("[[")
            i += 2
            continue
        if value.startswith("]]", i):
            bracket_depth = max(0, bracket_depth - 1)
            buf.append("]]")
            i += 2
            continue
        char = value[i]
        if char == "|" and brace_depth == 0 and bracket_depth == 0:
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(char)
        i += 1
    parts.append("".join(buf))
    return parts


def _clean_wikitext(value: str) -> str:
    value = re.sub(r"<ref.*?</ref>", "", value, flags=re.S)
    value = re.sub(r"<[^>]+>", "", value)

    def link_repl(match: re.Match[str]) -> str:
        inner = match.group(1)
        if "|" in inner:
            return inner.split("|")[-1]
        return inner

    previous = None
    while previous != value:
        previous = value
        value = re.sub(r"\[\[([^\]]+)\]\]", link_repl, value)
    value = re.sub(r"\{\{[^{}]*\}\}", "", value)
    value = value.replace("'''", "").replace("''", "")
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def _parse_template_fields(line: str) -> dict[str, str]:
    prefix = "{{nat fs g player|"
    body = line.strip()[len(prefix) :]
    if body.endswith("}}"):
        body = body[:-2]
    fields: dict[str, str] = {}
    for part in _split_top_level(body):
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        fields[key.strip()] = _clean_wikitext(value.strip())
    return fields


def _section_headings(raw: str) -> list[re.Match[str]]:
    return list(re.finditer(r"(?m)^===(?!=)(.+?)(?<!\=)===$", raw))


def parse_squads(raw: str) -> dict[str, Any]:
    team_names = _team_names_by_code()
    squads: dict[str, Any] = {}
    headings = _section_headings(raw)

    for index, heading in enumerate(headings):
        source_team_name = heading.group(1).strip()
        code = SOURCE_TEAM_CODES.get(source_team_name)
        if not code:
            continue
        next_start = headings[index + 1].start() if index + 1 < len(headings) else len(raw)
        section = raw[heading.end() : next_start]
        positions = {value: [] for value in POSITION_KEYS.values()}
        players: list[dict[str, str]] = []

        coach_match = re.search(r"Coach:\s*(.+)", section)
        announcement_match = re.search(r"\n\n([^\n]*?(?:announced|named)[^\n]*?squad[^\n]*?)\n", section, re.I)

        for line in section.splitlines():
            if not line.strip().startswith("{{nat fs g player|"):
                continue
            fields = _parse_template_fields(line)
            position = fields.get("pos", "")
            player = {
                "number": fields.get("no", ""),
                "position": position,
                "position_group": POSITION_KEYS.get(position, "outfield"),
                "name": fields.get("name", ""),
                "club": fields.get("club", ""),
                "club_country": fields.get("clubnat", ""),
                "caps": fields.get("caps", ""),
                "goals": fields.get("goals", ""),
            }
            if not player["name"]:
                continue
            players.append(player)
            if player["position_group"] in positions:
                positions[player["position_group"]].append(player)

        squads[code] = {
            "code": code,
            "team": team_names.get(code, source_team_name),
            "source_team_name": source_team_name,
            "coach": _clean_wikitext(coach_match.group(1)) if coach_match else "",
            "announcement": _clean_wikitext(announcement_match.group(1)) if announcement_match else "",
            "status": "official_final_squad",
            "source_name": SOURCE_NAME,
            "source_url": SOURCE_PAGE_URL,
            "positions": positions,
            "players": players,
            "player_count": len(players),
        }

    missing = sorted(set(SOURCE_TEAM_CODES.values()) - set(squads))
    bad_counts = {code: squad["player_count"] for code, squad in squads.items() if squad["player_count"] != 26}
    banned_hits: dict[str, list[str]] = {}
    for code, banned in BANNED_BY_CODE.items():
        squad = squads.get(code)
        if not squad:
            continue
        names = {player["name"] for player in squad["players"]}
        hits = sorted(name for name in names if name in banned or any(bad in name for bad in banned))
        if hits:
            banned_hits[code] = hits

    if missing or bad_counts or banned_hits:
        raise RuntimeError(f"Squad parse failed, missing={missing}, bad_counts={bad_counts}, banned_hits={banned_hits}")

    return {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "source_name": SOURCE_NAME,
        "source_url": SOURCE_PAGE_URL,
        "teams": squads,
    }


def _write_frontend_ts(payload: dict[str, Any]) -> None:
    out_path = ROOT / "frontend" / "src" / "services" / "team-squads-data.ts"
    serialized = json.dumps(payload, ensure_ascii=False, indent=2)
    out_path.write_text(
        "// Generated by scripts/fetch_team_squads.py. Do not edit by hand.\n"
        f"export const TEAM_SQUADS_DATA = {serialized} as const;\n",
        encoding="utf-8",
    )


def main() -> None:
    payload = parse_squads(_read_url(SOURCE_URL))
    backend_path = ROOT / "backend" / "data" / "team_squads.json"
    backend_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _write_frontend_ts(payload)
    print(f"updated {len(payload['teams'])} teams from {SOURCE_NAME}")


if __name__ == "__main__":
    main()
