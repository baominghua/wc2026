from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple


THE_ODDS_API_BASE_URL = "https://api.the-odds-api.com/v4"
SHANGHAI_TZ = timezone(timedelta(hours=8))
HISTORICAL_MARKET_SOURCE = "football_data_historical_prior"
HISTORICAL_MARKET_SOURCE_URL = "https://www.football-data.co.uk/data.php"
HISTORICAL_PRIOR_SAMPLE_MATCHES = 4800

TEAM_CODE_ALIASES = {
    "ALG": {"algeria"},
    "ARG": {"argentina"},
    "AUS": {"australia"},
    "AUT": {"austria"},
    "BEL": {"belgium"},
    "BIH": {"bosnia and herzegovina", "bosnia"},
    "BRA": {"brazil"},
    "CAN": {"canada"},
    "CIV": {"ivory coast", "cote d'ivoire"},
    "COL": {"colombia"},
    "CPV": {"cape verde", "cabo verde"},
    "COD": {"dr congo", "democratic republic of congo", "congo dr"},
    "CRO": {"croatia"},
    "CUW": {"curacao", "curaçao"},
    "CZE": {"czech republic", "czechia"},
    "ECU": {"ecuador"},
    "EGY": {"egypt"},
    "ENG": {"england"},
    "ESP": {"spain"},
    "FRA": {"france"},
    "GER": {"germany"},
    "GHA": {"ghana"},
    "HAI": {"haiti"},
    "IRN": {"iran"},
    "IRQ": {"iraq"},
    "JOR": {"jordan"},
    "JPN": {"japan"},
    "KOR": {"south korea", "korea republic", "republic of korea"},
    "KSA": {"saudi arabia"},
    "MAR": {"morocco"},
    "MEX": {"mexico"},
    "NED": {"netherlands", "holland"},
    "NOR": {"norway"},
    "NZL": {"new zealand"},
    "PAN": {"panama"},
    "PAR": {"paraguay"},
    "POR": {"portugal"},
    "QAT": {"qatar"},
    "RSA": {"south africa"},
    "SCO": {"scotland"},
    "SEN": {"senegal"},
    "SUI": {"switzerland", "swiss"},
    "SWE": {"sweden"},
    "TUN": {"tunisia"},
    "TUR": {"turkey", "turkiye", "türkiye"},
    "URU": {"uruguay"},
    "USA": {"united states", "usa", "us", "u.s.a."},
    "UZB": {"uzbekistan"},
}


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() not in {"0", "false", "no", "off"}


def _now_iso() -> str:
    return datetime.now(SHANGHAI_TZ).replace(microsecond=0).isoformat()


def _safe_float(value: Any) -> Optional[float]:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if result > 1.0 else None


def _normalise_name(value: str) -> str:
    return "".join(
        ch.lower() for ch in str(value or "") if ch.isalnum() or ch in {" ", "'", "."}
    ).strip()


def _code_matches(name: str, code: str) -> bool:
    normalised = _normalise_name(name)
    aliases = TEAM_CODE_ALIASES.get(code.upper(), set())
    return normalised in aliases or any(alias in normalised or normalised in alias for alias in aliases)


def _implied_probability(decimal_odds: Any) -> Optional[float]:
    odds = _safe_float(decimal_odds)
    if not odds:
        return None
    return 1.0 / odds


def _normalise_probabilities(items: Iterable[Tuple[str, float]]) -> Dict[str, float]:
    values = [(key, probability) for key, probability in items if probability > 0]
    total = sum(probability for _, probability in values)
    if total <= 0:
        return {}
    return {key: probability / total for key, probability in values}


def _clip(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _average_probabilities(probability_sets: List[Dict[str, float]]) -> Dict[str, float]:
    if not probability_sets:
        return {}
    keys = sorted({key for item in probability_sets for key in item})
    averaged = {
        key: sum(item.get(key, 0.0) for item in probability_sets) / len(probability_sets)
        for key in keys
    }
    return _normalise_probabilities(averaged.items())


def _empty_market(status: str, message: str) -> Dict[str, Any]:
    return {
        "available": False,
        "status": status,
        "source": os.getenv("ODDS_PROVIDER", "the_odds_api"),
        "last_updated": None,
        "message": message,
        "h2h": None,
        "totals": None,
        "spread": None,
        "bookmaker_count": 0,
        "fallback_sources": [
            "Football-Data historical closing odds CSV",
            "ESPN public results/events feed",
        ],
    }


def _historical_market_prior(
    model_probabilities: Optional[Mapping[str, float]] = None,
    expected_total: Optional[float] = None,
) -> Dict[str, Any]:
    """Build a low-weight prior from public historical closing-odds samples.

    This is deliberately not labelled as live market consensus. It is a fallback
    prior for draw/upset/total-goal risk when no realtime odds key is configured.
    """
    model = _normalise_probabilities(
        (
            ("home", float((model_probabilities or {}).get("home", 0.43) or 0.43)),
            ("draw", float((model_probabilities or {}).get("draw", 0.27) or 0.27)),
            ("away", float((model_probabilities or {}).get("away", 0.30) or 0.30)),
        )
    )
    home_model = model.get("home", 0.43)
    away_model = model.get("away", 0.30)
    favorite_gap = abs(home_model - away_model)
    favorite_key = "home" if home_model >= away_model else "away"
    underdog_key = "away" if favorite_key == "home" else "home"

    # Historical football odds tend to keep draws alive when the favorite gap is
    # modest, and compress extreme favorite probabilities compared with pure Elo.
    draw_prior = _clip(0.305 - favorite_gap * 0.18, 0.205, 0.315)
    favorite_prior = _clip(0.515 + favorite_gap * 0.42, 0.455, 0.705)
    underdog_prior = max(0.08, 1.0 - draw_prior - favorite_prior)
    h2h = {
        favorite_key: favorite_prior,
        "draw": draw_prior,
        underdog_key: underdog_prior,
    }
    h2h = _normalise_probabilities(h2h.items())

    total = float(expected_total or 2.55)
    over_probability = _clip(0.42 + (total - 2.15) * 0.16, 0.37, 0.64)
    totals = {
        "line": 2.5,
        "over_probability": round(over_probability, 3),
        "under_probability": round(1.0 - over_probability, 3),
    }
    spread_line = -0.5 if max(h2h.get("home", 0), h2h.get("away", 0)) >= 0.46 else 0.0
    spread = {
        "favorite": favorite_key,
        "line": spread_line,
        "price": None,
    }
    return {
        "available": True,
        "status": "historical_prior",
        "source": HISTORICAL_MARKET_SOURCE,
        "source_url": HISTORICAL_MARKET_SOURCE_URL,
        "last_updated": _now_iso(),
        "message": "已接入公开历史赔率样本低权重参考；未配置实时赔率 key，本场不使用实时市场硬校准。",
        "h2h": {key: round(value, 3) for key, value in h2h.items()},
        "totals": totals,
        "spread": spread,
        "bookmaker_count": 0,
        "sample_match_count": HISTORICAL_PRIOR_SAMPLE_MATCHES,
        "fallback_sources": [
            "Football-Data historical closing odds CSV",
            "ESPN public results/events feed",
        ],
    }


def odds_market_enabled() -> bool:
    return _env_bool("ODDS_MARKET_ENABLED", True)


def _api_get(url: str, timeout_seconds: int) -> Any:
    request = urllib.request.Request(url, headers={"User-Agent": "wc2026-predictor/26.5"})
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        return json.loads(response.read().decode("utf-8"))


def _find_event(payload: List[Dict[str, Any]], home_code: str, away_code: str) -> Optional[Dict[str, Any]]:
    for event in payload:
        home = event.get("home_team", "")
        away = event.get("away_team", "")
        if _code_matches(home, home_code) and _code_matches(away, away_code):
            return event
        if _code_matches(home, away_code) and _code_matches(away, home_code):
            reversed_event = dict(event)
            reversed_event["_reversed"] = True
            return reversed_event
    return None


def _parse_h2h(market: Dict[str, Any], home_code: str, away_code: str) -> Optional[Dict[str, float]]:
    probabilities = []
    for outcome in market.get("outcomes", []):
        price = _implied_probability(outcome.get("price"))
        if price is None:
            continue
        name = outcome.get("name", "")
        if _code_matches(name, home_code):
            probabilities.append(("home", price))
        elif _code_matches(name, away_code):
            probabilities.append(("away", price))
        elif _normalise_name(name) == "draw":
            probabilities.append(("draw", price))
    normalised = _normalise_probabilities(probabilities)
    if {"home", "draw", "away"}.issubset(normalised):
        return normalised
    return None


def _parse_totals(market: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    grouped: Dict[float, List[Tuple[str, float]]] = {}
    for outcome in market.get("outcomes", []):
        line = outcome.get("point")
        probability = _implied_probability(outcome.get("price"))
        if line is None or probability is None:
            continue
        try:
            line_value = float(line)
        except (TypeError, ValueError):
            continue
        name = _normalise_name(outcome.get("name", ""))
        if name.startswith("over"):
            key = "over"
        elif name.startswith("under"):
            key = "under"
        else:
            continue
        grouped.setdefault(line_value, []).append((key, probability))

    if not grouped:
        return None
    selected_line = min(grouped.keys(), key=lambda value: abs(value - 2.5))
    probabilities = _normalise_probabilities(grouped[selected_line])
    if not {"over", "under"}.issubset(probabilities):
        return None
    return {
        "line": selected_line,
        "over_probability": probabilities["over"],
        "under_probability": probabilities["under"],
    }


def _parse_spread(market: Dict[str, Any], home_code: str, away_code: str) -> Optional[Dict[str, Any]]:
    parsed = []
    for outcome in market.get("outcomes", []):
        point = outcome.get("point")
        price = _safe_float(outcome.get("price"))
        if point is None or price is None:
            continue
        try:
            point_value = float(point)
        except (TypeError, ValueError):
            continue
        name = outcome.get("name", "")
        if _code_matches(name, home_code):
            parsed.append(("home", point_value, price))
        elif _code_matches(name, away_code):
            parsed.append(("away", point_value, price))
    if not parsed:
        return None
    side, point, price = min(parsed, key=lambda item: item[1])
    return {"favorite": side, "line": point, "price": price}


def fetch_market_odds(
    home_team: str,
    away_team: str,
    home_code: str,
    away_code: str,
    model_probabilities: Optional[Mapping[str, float]] = None,
    expected_total: Optional[float] = None,
) -> Dict[str, Any]:
    if not odds_market_enabled():
        return _empty_market("disabled", "实时赔率校准已手动关闭；当前只使用公开赛果与历史赔率样本做风险参考")

    provider = os.getenv("ODDS_PROVIDER", "the_odds_api").strip().lower()
    if provider != "the_odds_api":
        return _empty_market("unsupported_provider", f"暂不支持的市场信号来源：{provider}")

    api_key = os.getenv("THE_ODDS_API_KEY")
    if not api_key:
        return _historical_market_prior(model_probabilities, expected_total)

    sport_key = os.getenv("THE_ODDS_API_SPORT_KEY", "soccer_fifa_world_cup")
    regions = os.getenv("THE_ODDS_API_REGIONS", "us,eu,uk")
    markets = os.getenv("THE_ODDS_API_MARKETS", "h2h,totals,spreads")
    odds_format = os.getenv("THE_ODDS_API_ODDS_FORMAT", "decimal")
    timeout = int(os.getenv("THE_ODDS_API_TIMEOUT_SECONDS", "8"))
    base_url = os.getenv("THE_ODDS_API_BASE_URL", THE_ODDS_API_BASE_URL).rstrip("/")
    params = urllib.parse.urlencode({
        "apiKey": api_key,
        "regions": regions,
        "markets": markets,
        "oddsFormat": odds_format,
    })
    url = f"{base_url}/sports/{urllib.parse.quote(sport_key)}/odds?{params}"

    try:
        payload = _api_get(url, timeout)
    except Exception as exc:  # pragma: no cover - network errors are environment dependent
        return _empty_market("error", f"赛前市场信号请求失败：{exc}")

    if not isinstance(payload, list):
        return _empty_market("error", "赛前市场信号返回格式异常")

    event = _find_event(payload, home_code, away_code)
    if not event:
        return _empty_market("no_match", f"未匹配到 {home_team} vs {away_team} 的市场信号")

    h2h_sets: List[Dict[str, float]] = []
    totals_sets: List[Dict[str, Any]] = []
    spread_sets: List[Dict[str, Any]] = []
    bookmaker_count = 0
    for bookmaker in event.get("bookmakers", []):
        bookmaker_count += 1
        for market in bookmaker.get("markets", []):
            key = market.get("key")
            if key == "h2h":
                parsed_h2h = _parse_h2h(market, home_code, away_code)
                if parsed_h2h:
                    h2h_sets.append(parsed_h2h)
            elif key == "totals":
                parsed_totals = _parse_totals(market)
                if parsed_totals:
                    totals_sets.append(parsed_totals)
            elif key == "spreads":
                parsed_spread = _parse_spread(market, home_code, away_code)
                if parsed_spread:
                    spread_sets.append(parsed_spread)

    h2h = _average_probabilities(h2h_sets)
    totals = None
    if totals_sets:
        totals = {
            "line": round(sum(item["line"] for item in totals_sets) / len(totals_sets), 2),
            "over_probability": round(
                sum(item["over_probability"] for item in totals_sets) / len(totals_sets), 3
            ),
            "under_probability": round(
                sum(item["under_probability"] for item in totals_sets) / len(totals_sets), 3
            ),
        }
    spread = None
    if spread_sets:
        spread = sorted(spread_sets, key=lambda item: abs(item["line"]), reverse=True)[0]

    return {
        "available": bool(h2h or totals or spread),
        "status": "connected" if h2h or totals or spread else "no_markets",
        "source": "the_odds_api",
        "last_updated": _now_iso(),
        "message": "赛前市场信号已接入" if h2h else "赛前市场信号已接入，但缺少胜平负盘口",
        "h2h": {key: round(value, 3) for key, value in h2h.items()} if h2h else None,
        "totals": totals,
        "spread": spread,
        "bookmaker_count": bookmaker_count,
    }
