from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional

from services.schedule import load_schedule_matches


PredictionProvider = Callable[[Dict[str, Any]], Optional[Dict[str, Any]]]
WORLD_CUP_2026_START = datetime(2026, 6, 11, tzinfo=timezone.utc)
PROFILE_AVERAGE_KEYS = [
    "points",
    "goals_for",
    "goals_against",
    "goal_diff",
    "shots_for",
    "shots_against",
    "shots_on_target_for",
    "shots_on_target_against",
    "corners_for",
    "corners_against",
    "yellow_cards_for",
    "yellow_cards_against",
]
OFFICIAL_COMPETITION_KEYWORDS = (
    "qualifying",
    "qualification",
    "qualifier",
    "nations league",
    "copa america",
    "euro",
    "asian cup",
    "afcon",
    "gold cup",
    "concacaf",
    "conmebol",
    "uefa",
    "afc",
    "caf",
    "ofc",
    "fifa",
    "预选",
    "欧国联",
    "美洲杯",
    "欧洲杯",
    "亚洲杯",
    "非洲杯",
    "金杯赛",
    "正式",
)
FRIENDLY_COMPETITION_KEYWORDS = ("friendly", "friendlies", "友谊")


METRIC_DEFINITIONS = {
    "outcome_top1": "赛果1选：模型赛果概率最高的一项必须等于真实赛果。",
    "outcome_top2": "赛果2选：真实赛果必须落在模型赛果概率前两项内。",
    "outcome_top3": "赛果3选：真实赛果落在胜/平/负三项候选内；该项通常接近全包，仅作口径对照。",
    "score_top1": "比分1选：模型主预测比分必须精确等于真实比分。",
    "score_top2": "比分2选：真实比分必须落在模型前两个比分候选内。",
    "score_top3": "比分3选：真实比分必须落在模型前三个比分候选内。",
    "total_goals_range_hit": "总进球区间：真实总进球必须落在模型给出的总进球区间内。",
    "btts_hit": "双方进球：模型双方进球判断必须与真实双方是否都有进球一致。",
    "upset_hit": "冷门命中：模型冷门参考方向与真实赛果一致，且不同于模型赛果首选。",
}

METRIC_DEFINITIONS.update(
    {
        "outcome_top1": "\u8d5b\u679c1\u9009\uff1a\u6a21\u578b\u8d5b\u679c\u6982\u7387\u6700\u9ad8\u7684\u4e00\u9879\u5fc5\u987b\u7b49\u4e8e\u771f\u5b9e\u8d5b\u679c\u3002",
        "outcome_top2": "\u8d5b\u679c2\u9009\uff1a\u771f\u5b9e\u8d5b\u679c\u5fc5\u987b\u843d\u5728\u6a21\u578b\u8d5b\u679c\u6982\u7387\u524d\u4e24\u9879\u5185\u3002",
        "outcome_top3": "\u8d5b\u679c3\u9009\uff1a\u771f\u5b9e\u8d5b\u679c\u843d\u5728\u80dc/\u5e73/\u8d1f\u4e09\u9879\u5019\u9009\u5185\uff1b\u8be5\u9879\u901a\u5e38\u63a5\u8fd1\u5168\u5305\uff0c\u4ec5\u4f5c\u53e3\u5f84\u5bf9\u7167\u3002",
        "score_top1": "\u6bd4\u52061\u9009\uff08\u7d2f\u8ba1\u65e7\u53e3\u5f84\uff09\uff1a\u4e3b\u9884\u6d4b\u6bd4\u5206\u5fc5\u987b\u7cbe\u786e\u7b49\u4e8e\u771f\u5b9e\u6bd4\u5206\u3002",
        "score_top2": "\u6bd4\u52062\u9009\uff08\u7d2f\u8ba1\u65e7\u53e3\u5f84\uff09\uff1a\u771f\u5b9e\u6bd4\u5206\u843d\u5728\u524d\u4e24\u4e2a\u6bd4\u5206\u5019\u9009\u5185\u3002",
        "score_top3": "\u6bd4\u52063\u9009\uff08\u7d2f\u8ba1\u65e7\u53e3\u5f84\uff09\uff1a\u771f\u5b9e\u6bd4\u5206\u843d\u5728\u524d\u4e09\u4e2a\u6bd4\u5206\u5019\u9009\u5185\u3002",
        "score_pick1": "\u9996\u9009\u6bd4\u5206\uff1a\u4ec5\u8ba1\u7b2c1\u4e2a\u7cbe\u786e\u6bd4\u5206\u662f\u5426\u547d\u4e2d\u3002",
        "score_pick2": "\u7b2c\u4e8c\u6bd4\u5206\uff1a\u4ec5\u8ba1\u7b2c2\u4e2a\u7cbe\u786e\u6bd4\u5206\u662f\u5426\u547d\u4e2d\uff0c\u4e0d\u4e0e\u5176\u4ed6\u69fd\u4f4d\u91cd\u590d\u8ba1\u6570\u3002",
        "score_pick3": "\u7b2c\u4e09\u6bd4\u5206\uff1a\u4ec5\u8ba1\u7b2c3\u4e2a\u7cbe\u786e\u6bd4\u5206\u662f\u5426\u547d\u4e2d\uff0c\u4e0d\u4e0e\u5176\u4ed6\u69fd\u4f4d\u91cd\u590d\u8ba1\u6570\u3002",
        "wdl_hit": "\u80dc\u5e73\u8d1f\u547d\u4e2d\uff1a\u6a21\u578b\u80dc/\u5e73/\u8d1f\u4e3b\u65b9\u5411\u5fc5\u987b\u4e0e\u771f\u5b9e\u8d5b\u679c\u4e00\u81f4\u3002",
        "upset_hit": "\u51b7\u95e8\u65b9\u5411\u547d\u4e2d\uff1a\u51b7\u95e8\u53c2\u8003\u65b9\u5411\u4e0e\u771f\u5b9e\u8d5b\u679c\u4e00\u81f4\uff0c\u4e14\u4e0d\u540c\u4e8e\u6a21\u578b\u8d5b\u679c\u9996\u9009\u3002",
        "upset_score_hit": "\u51b7\u95e8\u6bd4\u5206\uff1a\u51b7\u95e8\u6bd4\u5206\u53ea\u5728\u4e0d\u4e0e\u524d\u4e09\u4e2a\u6bd4\u5206\u91cd\u590d\u65f6\u72ec\u7acb\u8ba1\u6570\u3002",
        "score_pool_hit": "\u603b\u547d\u4e2d\u7387\uff1a\u771f\u5b9e\u6bd4\u5206\u547d\u4e2d1\u9009/2\u9009/3\u9009/\u51b7\u95e8\u6bd4\u5206\u4efb\u4e00\u9879\uff0c\u56db\u9879\u4e92\u65a5\u540e\u7edf\u8ba1\u3002",
        "total_goals_range_hit": "\u603b\u8fdb\u7403\u533a\u95f4\uff1a\u771f\u5b9e\u603b\u8fdb\u7403\u5fc5\u987b\u843d\u5728\u6a21\u578b\u7ed9\u51fa\u7684\u603b\u8fdb\u7403\u533a\u95f4\u5185\u3002",
        "btts_hit": "\u53cc\u65b9\u8fdb\u7403\uff1a\u6a21\u578bBTTS\u5224\u65ad\u5fc5\u987b\u4e0e\u771f\u5b9e\u53cc\u65b9\u662f\u5426\u90fd\u6709\u8fdb\u7403\u4e00\u81f4\u3002",
    }
)


def _safe_int(value: Any) -> Optional[int]:
    try:
        if value is None or value == "":
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _round_rate(hits: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round(hits / total, 4)


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
    return parsed


def _is_completed(match: Mapping[str, Any]) -> bool:
    return (
        match.get("status") == "completed"
        and _safe_int(match.get("home_score")) is not None
        and _safe_int(match.get("away_score")) is not None
    )


def _outcome(home_score: int, away_score: int) -> str:
    if home_score > away_score:
        return "home"
    if home_score < away_score:
        return "away"
    return "draw"


def _outcome_label(outcome: str, match: Mapping[str, Any]) -> str:
    if outcome == "home":
        return str(match.get("home_team") or "home")
    if outcome == "away":
        return str(match.get("away_team") or "away")
    return "平局"


def _prediction_outcome_order(prediction: Mapping[str, Any]) -> List[str]:
    rows = [
        ("home", _safe_float(prediction.get("home_win_probability"))),
        ("draw", _safe_float(prediction.get("draw_probability"))),
        ("away", _safe_float(prediction.get("away_win_probability"))),
    ]
    return [key for key, _ in sorted(rows, key=lambda item: item[1], reverse=True)]


def _score_candidates(prediction: Mapping[str, Any]) -> List[str]:
    scores: List[str] = []
    predicted_score = prediction.get("predicted_score")
    if predicted_score:
        scores.append(str(predicted_score))
    for item in prediction.get("possible_scores") or []:
        if isinstance(item, Mapping) and item.get("score"):
            score = str(item["score"])
            if score not in scores:
                scores.append(score)
    return scores[:3]


def _score_slot_candidates(prediction: Mapping[str, Any]) -> List[Dict[str, str]]:
    slots: List[Dict[str, str]] = []
    seen = set()
    for index, score in enumerate(_score_candidates(prediction), start=1):
        if score in seen:
            continue
        seen.add(score)
        slots.append({"slot": f"score_pick{index}", "score": score})

    upset = prediction.get("upset_prediction") if isinstance(prediction.get("upset_prediction"), Mapping) else {}
    upset_score = str(upset.get("score") or "")
    if upset_score and upset_score not in seen:
        slots.append({"slot": "upset_score_hit", "score": upset_score})
    return slots


def _predicted_total_goals_range(prediction: Mapping[str, Any]) -> str:
    audit = prediction.get("skill_audit") if isinstance(prediction.get("skill_audit"), Mapping) else {}
    audit_range = str(audit.get("total_goals_range") or "")
    if audit_range:
        return audit_range

    total_prediction = prediction.get("total_goals_prediction")
    expected_total = None
    if isinstance(total_prediction, Mapping):
        expected_total = _safe_float(total_prediction.get("expected_total"), default=-1.0)
    if expected_total is None or expected_total < 0:
        expected_total = _safe_float(prediction.get("xg_home")) + _safe_float(prediction.get("xg_away"))

    if expected_total < 2.55:
        return "0-3"
    if expected_total < 3.25:
        return "2-4"
    return "3-6"


def _total_goals_range_hit(total_range: str, actual_total: int) -> bool:
    parts = str(total_range or "").replace(":", "-").split("-")
    if len(parts) < 2:
        return False
    low = _safe_int(parts[0])
    high = _safe_int(parts[1])
    if low is None or high is None:
        return False
    return low <= actual_total <= high


def _predicted_btts_view(prediction: Mapping[str, Any]) -> str:
    audit = prediction.get("skill_audit") if isinstance(prediction.get("skill_audit"), Mapping) else {}
    audit_btts = str(audit.get("btts_view") or "")
    if audit_btts:
        return audit_btts

    home_xg = _safe_float(prediction.get("xg_home"))
    away_xg = _safe_float(prediction.get("xg_away"))
    return "yes" if min(home_xg, away_xg) >= 0.9 and home_xg + away_xg >= 2.65 else "lean-no"


def _prediction_for_match(
    match: Mapping[str, Any],
    predictions_by_match: Optional[Mapping[int, Dict[str, Any]]],
    predictor: Optional[PredictionProvider],
) -> Optional[Dict[str, Any]]:
    match_id = _safe_int(match.get("id"))
    if match_id is not None and predictions_by_match and match_id in predictions_by_match:
        return deepcopy(predictions_by_match[match_id])
    if predictor:
        return predictor(dict(match))
    return None


def _report(match: Mapping[str, Any]) -> Mapping[str, Any]:
    report = match.get("report") if isinstance(match.get("report"), Mapping) else {}
    return report


def _stats(match: Mapping[str, Any]) -> Mapping[str, Any]:
    report = _report(match)
    stats = report.get("stats") if isinstance(report.get("stats"), Mapping) else {}
    return stats


def _stat(stats: Mapping[str, Any], *names: str) -> Optional[float]:
    for name in names:
        if name in stats:
            value = stats.get(name)
            if value is None or value == "":
                return None
            return _safe_float(value)
    return None


def _events_from_match(match: Mapping[str, Any], key: str) -> List[Mapping[str, Any]]:
    report = _report(match)
    rows: List[Mapping[str, Any]] = []
    report_rows = report.get(key)
    if isinstance(report_rows, list):
        rows.extend(item for item in report_rows if isinstance(item, Mapping))
    top_level_rows = match.get(key)
    if isinstance(top_level_rows, list):
        for item in top_level_rows:
            if isinstance(item, Mapping) and item not in rows:
                rows.append(item)
    return rows


def _event_side(event: Mapping[str, Any], match: Mapping[str, Any]) -> Optional[str]:
    team = "".join(str(event.get("team") or "").lower().split())
    home = "".join(str(match.get("home_team") or "").lower().split())
    away = "".join(str(match.get("away_team") or "").lower().split())
    if team and team == home:
        return "home"
    if team and team == away:
        return "away"
    return None


def _is_red_card(card: Mapping[str, Any]) -> bool:
    text = " ".join(
        str(card.get(key) or "")
        for key in ("type", "card_type", "detail", "description", "text")
    ).lower()
    return "red" in text or "\u7ea2\u724c" in text


def _red_card_context(match: Mapping[str, Any]) -> Dict[str, Any]:
    stats = _stats(match)
    home_red_stat = _safe_int(
        _stat(
            stats,
            "red_cards_home",
            "home_red_cards",
            "redCardsHome",
            "homeRedCards",
        )
    ) or 0
    away_red_stat = _safe_int(
        _stat(
            stats,
            "red_cards_away",
            "away_red_cards",
            "redCardsAway",
            "awayRedCards",
        )
    ) or 0
    events: List[Dict[str, Any]] = []
    home_red_events = 0
    away_red_events = 0
    for card in _events_from_match(match, "cards"):
        if not _is_red_card(card):
            continue
        side = _event_side(card, match)
        if side == "home":
            home_red_events += 1
        elif side == "away":
            away_red_events += 1
        events.append(
            {
                "minute": _safe_int(card.get("minute")),
                "team": str(card.get("team") or ""),
                "player": str(card.get("player") or ""),
                "side": side,
            }
        )

    home_red = max(home_red_stat, home_red_events)
    away_red = max(away_red_stat, away_red_events)
    return {
        "home": home_red,
        "away": away_red,
        "total": home_red + away_red + sum(1 for event in events if not event.get("side")),
        "events": events,
    }


def _goals_after_red_card(match: Mapping[str, Any], red_events: List[Mapping[str, Any]]) -> int:
    minute_events = [event for event in red_events if _safe_int(event.get("minute")) is not None]
    if not minute_events:
        return 0
    first_red = min(minute_events, key=lambda event: _safe_int(event.get("minute")) or 0)
    first_minute = _safe_int(first_red.get("minute")) or 0
    red_sides = {str(event.get("side")) for event in red_events if event.get("side")}
    goals_after = 0
    for goal in _events_from_match(match, "goals"):
        goal_minute = _safe_int(goal.get("minute"))
        goal_side = _event_side(goal, match)
        if goal_minute is None or goal_minute <= first_minute:
            continue
        if not red_sides or goal_side not in red_sides:
            goals_after += 1
    return goals_after


def _red_card_variance_note(match: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
    context = _red_card_context(match)
    if not context["total"]:
        return None

    home_score = _safe_int(match.get("home_score")) or 0
    away_score = _safe_int(match.get("away_score")) or 0
    home_team = str(match.get("home_team") or "home")
    away_team = str(match.get("away_team") or "away")
    actual_total = home_score + away_score
    score_shape = "大比分" if actual_total >= 4 or abs(home_score - away_score) >= 3 else "比分走势"
    event_bits = []
    for event in context["events"][:3]:
        team = event.get("team") or (home_team if event.get("side") == "home" else away_team if event.get("side") == "away" else "\u672a\u6807\u8bb0\u7403\u961f")
        minute = f"\u7b2c{event['minute']}\u5206\u949f" if event.get("minute") is not None else "\u6bd4\u8d5b\u4e2d"
        player = f"{event['player']} " if event.get("player") else ""
        event_bits.append(f"{team}{minute}{player}\u5403\u5230\u7ea2\u724c")

    if not event_bits:
        count_bits = []
        if context["home"]:
            count_bits.append(f"{home_team}{context['home']}\u5f20")
        if context["away"]:
            count_bits.append(f"{away_team}{context['away']}\u5f20")
        event_bits.append("\u7ea2\u724c\u7edf\u8ba1\uff1a" + "\u3001".join(count_bits))

    goals_after = _goals_after_red_card(match, context["events"])
    events_text = "\uff1b".join(event_bits)
    after_text = (
        f"\u7ea2\u724c\u540e\u5bf9\u624b\u53c8\u6253\u8fdb{goals_after}\u7403\uff0c"
        if goals_after
        else "\u5373\u4f7f\u7f3a\u5c11\u5b8c\u6574\u8fdb\u7403\u65f6\u95f4\u7ebf\uff0c"
    )
    return {
        "type": "red_card_turning_point",
        "title": "\u7ea2\u724c\u6539\u53d8\u6bd4\u8d5b\u7ed3\u6784",
        "detail": (
            f"{events_text}\uff0c{after_text}"
            f"\u6700\u7ec8\u6bd4\u5206\u5f62\u6210 {home_score}-{away_score}\u3002"
            f"\u8fd9\u7c7b\u7ea2\u724c\u5f71\u54cd\u4e0b\u7684{score_shape}\u5e94\u4f18\u5148\u62c6\u5206\u4e3a\u7eaa\u5f8b\u4e8b\u4ef6\u3001\u4eba\u6570\u52a3\u52bf\u548c\u9632\u7ebf\u7a7a\u95f4\u653e\u5927\uff0c"
            "\u4e0d\u80fd\u7b80\u5355\u628a\u7ea2\u724c\u540e\u7684\u8282\u594f\u5931\u8861\u5168\u90e8\u5b66\u6210\u7403\u961f\u771f\u5b9e\u5b9e\u529b\u4e0b\u6ed1\u3002"
        ),
    }


def _variance_notes(match: Mapping[str, Any], prediction: Mapping[str, Any], actual_outcome: str) -> List[Dict[str, Any]]:
    home_score = _safe_int(match.get("home_score")) or 0
    away_score = _safe_int(match.get("away_score")) or 0
    predicted_order = _prediction_outcome_order(prediction)
    notes: List[Dict[str, Any]] = []

    if predicted_order and predicted_order[0] != actual_outcome:
        notes.append(
            {
                "type": "outcome_miss",
                "title": "赛果方向偏差",
                "detail": (
                    f"模型首选结果是{_outcome_label(predicted_order[0], match)}，"
                    f"实际赛果是{_outcome_label(actual_outcome, match)}。"
                    "下次需要降低单一方向的置信度，并结合临场状态波动重新校准。"
                ),
            }
        )

    stats = _stats(match)
    red_card_note = _red_card_variance_note(match)
    if red_card_note:
        notes.append(red_card_note)

    home_xg = _stat(stats, "xg_home", "home_xg")
    away_xg = _stat(stats, "xg_away", "away_xg")
    if home_xg is not None and away_xg is not None:
        home_finishing_gap = home_score - home_xg
        away_finishing_gap = away_score - away_xg
        if abs(home_finishing_gap) >= 1.0 or abs(away_finishing_gap) >= 1.0:
            notes.append(
                {
                    "type": "finishing_variance",
                    "title": "终结效率偏差",
                    "detail": (
                        f"{match.get('home_team')} 进球/xG 为 {home_score}/{home_xg:.2f}，"
                        f"{match.get('away_team')} 进球/xG 为 {away_score}/{away_xg:.2f}。"
                        "实际把握机会效率明显偏离预期，下次需要提高终结波动和门将表现权重。"
                    ),
                }
            )

    possession_home = _stat(stats, "possession_home", "home_possession")
    possession_away = _stat(stats, "possession_away", "away_possession")
    shots_home = _stat(stats, "shots_home", "home_shots")
    shots_away = _stat(stats, "shots_away", "away_shots")
    has_possession = possession_home is not None and possession_away is not None
    has_shots = shots_home is not None and shots_away is not None
    if (has_possession and abs(possession_home - possession_away) >= 12) or (
        has_shots and abs(shots_home - shots_away) >= 6
    ):
        possession_text = (
            f"{possession_home:.0f}-{possession_away:.0f}" if has_possession else "暂无完整数据"
        )
        shots_text = f"{shots_home:.0f}-{shots_away:.0f}" if has_shots else "暂无完整数据"
        notes.append(
            {
                "type": "match_control",
                "title": "场面控制偏差",
                "detail": (
                    f"控球率为 {possession_text}，"
                    f"射门数为 {shots_text}。"
                    "下次需要提高压迫强度、转换质量和持续进攻威胁的权重。"
                ),
            }
        )

    corners_home = _stat(stats, "corners_home", "home_corners")
    corners_away = _stat(stats, "corners_away", "away_corners")
    if corners_home is not None and corners_away is not None and corners_home + corners_away >= 9:
        notes.append(
            {
                "type": "set_piece_pressure",
                "title": "定位球压力偏高",
                "detail": (
                    f"角球数为 {corners_home:.0f}-{corners_away:.0f}。"
                    "下次角球与定位球预期应上调，同时关注防守端送角球风险。"
                ),
            }
        )

    yellow_home = _stat(stats, "yellow_cards_home", "home_yellow_cards")
    yellow_away = _stat(stats, "yellow_cards_away", "away_yellow_cards")
    if yellow_home is not None and yellow_away is not None and yellow_home + yellow_away >= 5:
        notes.append(
            {
                "type": "card_discipline",
                "title": "纪律风险偏高",
                "detail": (
                    f"黄牌数为 {yellow_home:.0f}-{yellow_away:.0f}。"
                    "下次首发与停赛分析需提前标记对抗强度和累计黄牌风险。"
                ),
            }
        )

    if not notes:
        notes.append(
            {
                "type": "within_expected_range",
                "title": "结果接近模型区间",
                "detail": "实际结果靠近模型主要分布，只需要轻微校准，重点观察下一场状态延续性。",
            }
        )
    return notes


def _next_adjustments(match: Mapping[str, Any]) -> Dict[str, Dict[str, float]]:
    home = str(match.get("home_team") or "home")
    away = str(match.get("away_team") or "away")
    home_score = _safe_int(match.get("home_score")) or 0
    away_score = _safe_int(match.get("away_score")) or 0
    stats = _stats(match)
    home_xg = _stat(stats, "xg_home", "home_xg") or float(home_score)
    away_xg = _stat(stats, "xg_away", "away_xg") or float(away_score)
    home_attack = _clamp((home_score - home_xg) * 0.025 + (home_score - away_score) * 0.012, -0.08, 0.10)
    home_defense = _clamp((away_xg - away_score) * 0.018, -0.05, 0.06)
    away_attack = _clamp((away_score - away_xg) * 0.025 + (away_score - home_score) * 0.012, -0.08, 0.10)
    away_defense = _clamp((home_xg - home_score) * 0.018, -0.05, 0.06)
    if _red_card_context(match)["total"]:
        # Red-card scorelines are structurally distorted, so do not overfit the
        # next-match team strength deltas to the post-card collapse.
        home_attack *= 0.6
        home_defense *= 0.6
        away_attack *= 0.6
        away_defense *= 0.6

    return {
        home: {
            "attack_delta": round(home_attack, 4),
            "defense_delta": round(home_defense, 4),
        },
        away: {
            "attack_delta": round(away_attack, 4),
            "defense_delta": round(away_defense, 4),
        },
    }


def _review_lessons(variance_notes: Iterable[Mapping[str, Any]]) -> List[str]:
    note_types = {str(note.get("type") or "") for note in variance_notes}
    lessons: List[str] = []
    if "red_card_turning_point" in note_types:
        lessons.extend(
            [
                "\u51fa\u73b0\u7ea2\u724c\u6216\u5c11\u6253\u4e00\u4eba\u7684\u6bd4\u8d5b\uff0c\u5927\u6bd4\u5206\u8981\u62c6\u6210\u7eaa\u5f8b\u4e8b\u4ef6\u5f71\u54cd\u548c\u771f\u5b9e\u653b\u9632\u8868\u73b0\u4e24\u90e8\u5206\uff0c\u907f\u514d\u628a\u7ea2\u724c\u540e\u7684\u5d29\u76d8\u5168\u90e8\u8ba1\u5165\u57fa\u7840\u5b9e\u529b\u3002",
                "\u540e\u7eed\u8d5b\u524d\u9884\u6d4b\u9700\u8981\u72ec\u7acb\u6807\u8bb0\u7ea2\u724c\u505c\u8d5b\u3001\u7d2f\u8ba1\u9ec4\u724c\u548c\u9ad8\u538b\u5bf9\u6297\u98ce\u9669\uff0c\u8fd9\u4e9b\u4f1a\u76f4\u63a5\u6539\u53d8\u4e0b\u4e00\u573a\u7684\u9635\u5bb9\u548c\u6bd4\u8d5b\u8282\u594f\u3002",
            ]
        )
    lessons.extend(
        [
            "第二轮及后续预测优先读取已完赛真实表现，再叠加赛前基础实力。",
            "如果积分形势让平局对双方都有利，平局概率只做保守上调，避免过度修正。",
            "冷门参考必须贴近主概率分布和相邻比分，避免给出脱离比赛预期的大偏差比分。",
        ]
    )
    return lessons


def generate_match_review(match: Dict[str, Any], prediction: Dict[str, Any]) -> Dict[str, Any]:
    home_score = _safe_int(match.get("home_score"))
    away_score = _safe_int(match.get("away_score"))
    if home_score is None or away_score is None:
        raise ValueError("match review requires a completed match with scores")

    actual_outcome = _outcome(home_score, away_score)
    outcome_order = _prediction_outcome_order(prediction)
    score_candidates = _score_candidates(prediction)
    score_slots = _score_slot_candidates(prediction)
    score_slot_hits = {
        slot["slot"]: slot["score"] == f"{home_score}-{away_score}"
        for slot in score_slots
    }
    actual_score = f"{home_score}-{away_score}"
    actual_total_goals = home_score + away_score
    predicted_total_range = _predicted_total_goals_range(prediction)
    predicted_btts = _predicted_btts_view(prediction)
    actual_btts = home_score > 0 and away_score > 0
    upset = prediction.get("upset_prediction") if isinstance(prediction.get("upset_prediction"), Mapping) else {}
    upset_outcome = str(upset.get("outcome") or "")
    variance_notes = _variance_notes(match, prediction, actual_outcome)

    return {
        "match_id": match.get("id"),
        "home_team": match.get("home_team"),
        "away_team": match.get("away_team"),
        "group": match.get("group"),
        "round": match.get("round"),
        "stage": match.get("stage"),
        "match_date": match.get("match_date"),
        "venue": match.get("venue"),
        "actual": {
            "score": actual_score,
            "outcome": actual_outcome,
            "outcome_label": _outcome_label(actual_outcome, match),
        },
        "prediction": {
            "score": prediction.get("predicted_score"),
            "score_candidates": score_candidates,
            "score_slots": score_slots,
            "outcome_order": outcome_order,
            "probabilities": {
                "home": _safe_float(prediction.get("home_win_probability")),
                "draw": _safe_float(prediction.get("draw_probability")),
                "away": _safe_float(prediction.get("away_win_probability")),
            },
            "upset": deepcopy(upset) if isinstance(upset, Mapping) else None,
            "total_goals": deepcopy(prediction.get("total_goals_prediction")),
            "total_goals_range": predicted_total_range,
            "btts_view": predicted_btts,
            "xg_home": prediction.get("xg_home"),
            "xg_away": prediction.get("xg_away"),
            "factors": list(prediction.get("factors") or [])[:8],
        },
        "accuracy": {
            "outcome_top1": actual_outcome in outcome_order[:1],
            "outcome_top2": actual_outcome in outcome_order[:2],
            "outcome_top3": actual_outcome in outcome_order[:3],
            "wdl_hit": actual_outcome in outcome_order[:1],
            "score_top1": actual_score in score_candidates[:1],
            "score_top2": actual_score in score_candidates[:2],
            "score_top3": actual_score in score_candidates[:3],
            "upset_hit": bool(upset_outcome and upset_outcome == actual_outcome and outcome_order and outcome_order[0] != actual_outcome),
            "score_pick1": bool(score_slot_hits.get("score_pick1")),
            "score_pick2": bool(score_slot_hits.get("score_pick2")),
            "score_pick3": bool(score_slot_hits.get("score_pick3")),
            "upset_score_hit": bool(score_slot_hits.get("upset_score_hit")),
            "score_pool_hit": any(score_slot_hits.values()),
            "total_goals_range_hit": _total_goals_range_hit(predicted_total_range, actual_total_goals),
            "btts_hit": (predicted_btts == "yes") == actual_btts,
        },
        "variance_notes": variance_notes,
        "lessons": _review_lessons(variance_notes),
        "next_adjustments": _next_adjustments(match),
        "data_source": {
            "match": match.get("live_source") or "merged_public_feed",
            "status": match.get("data_status") or "completed",
            "last_updated": match.get("last_updated"),
        },
    }


def build_prediction_audit(
    matches: Iterable[Dict[str, Any]],
    predictions_by_match: Optional[Mapping[int, Dict[str, Any]]] = None,
    predictor: Optional[PredictionProvider] = None,
    evaluation_mode: str = "pre_match_snapshot",
    source_policy: Optional[str] = None,
) -> Dict[str, Any]:
    match_list = list(matches)
    rows: List[Dict[str, Any]] = []
    completed_count = 0
    missing_prediction_matches: List[Dict[str, Any]] = []
    schedule_total = len(load_schedule_matches())
    tournament_matches = [match for match in match_list if _is_current_world_cup_match(match)]
    total_matches = schedule_total or len(tournament_matches)
    for match in tournament_matches:
        if not _is_completed(match):
            continue
        completed_count += 1
        prediction = _prediction_for_match(match, predictions_by_match, predictor)
        if not prediction:
            home_score = _safe_int(match.get("home_score"))
            away_score = _safe_int(match.get("away_score"))
            missing_prediction_matches.append(
                {
                    "match_id": match.get("id"),
                    "home_team": match.get("home_team"),
                    "away_team": match.get("away_team"),
                    "actual_score": f"{home_score}-{away_score}" if home_score is not None and away_score is not None else "",
                    "match_date": match.get("match_date"),
                    "reason": "缺少赛前预测快照，不能纳入真实准确率统计",
                }
            )
            continue
        rows.append(generate_match_review(match, prediction))

    summary_keys = [
        "outcome_top1",
        "outcome_top2",
        "outcome_top3",
        "wdl_hit",
        "score_top1",
        "score_top2",
        "score_top3",
        "upset_hit",
        "score_pick1",
        "score_pick2",
        "score_pick3",
        "upset_score_hit",
        "score_pool_hit",
        "total_goals_range_hit",
        "btts_hit",
    ]
    summary = {
        "completed_matches": completed_count,
        "total_matches": total_matches,
        "reviewed_matches": len(rows),
        "missing_prediction_count": len(missing_prediction_matches),
    }
    for key in summary_keys:
        hits = sum(1 for row in rows if row["accuracy"].get(key))
        name = {
            "upset_hit": "upset",
            "wdl_hit": "wdl",
            "upset_score_hit": "upset_score",
            "score_pool_hit": "score_pool",
            "total_goals_range_hit": "total_goals_range",
            "btts_hit": "btts",
        }.get(key, key)
        summary[f"{name}_hits"] = hits
        summary[f"{name}_accuracy"] = _round_rate(hits, len(rows))
    summary["score_total_hits"] = summary.get("score_pool_hits", 0)
    summary["score_total_accuracy"] = summary.get("score_pool_accuracy", 0.0)

    return {
        "summary": summary,
        "rows": rows,
        "missing_prediction_matches": missing_prediction_matches,
        "evaluation_mode": evaluation_mode,
        "metric_definitions": METRIC_DEFINITIONS,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_policy": source_policy
        or "仅使用赛前预测快照与公开/免费赛果数据；缺少赛前快照的完赛比赛只列为缺失样本，不纳入准确率分母。",
    }


def _standings(matches: Iterable[Mapping[str, Any]], group: str, before: Optional[datetime]) -> Dict[str, Dict[str, int]]:
    table: Dict[str, Dict[str, int]] = defaultdict(lambda: {"played": 0, "points": 0, "gf": 0, "ga": 0, "gd": 0})
    for match in matches:
        if match.get("group") != group or not _is_completed(match):
            continue
        match_time = _parse_datetime(match.get("match_date"))
        if before and match_time and match_time >= before:
            continue
        home = str(match.get("home_team") or "")
        away = str(match.get("away_team") or "")
        home_score = _safe_int(match.get("home_score")) or 0
        away_score = _safe_int(match.get("away_score")) or 0
        if not home or not away:
            continue
        table[home]["played"] += 1
        table[away]["played"] += 1
        table[home]["gf"] += home_score
        table[home]["ga"] += away_score
        table[away]["gf"] += away_score
        table[away]["ga"] += home_score
        if home_score > away_score:
            table[home]["points"] += 3
        elif home_score < away_score:
            table[away]["points"] += 3
        else:
            table[home]["points"] += 1
            table[away]["points"] += 1
    for item in table.values():
        item["gd"] = item["gf"] - item["ga"]
    return dict(table)


def _ranked_standings(table: Mapping[str, Mapping[str, int]]) -> List[str]:
    return [
        team
        for team, _row in sorted(
            table.items(),
            key=lambda item: (
                -int(item[1].get("points", 0)),
                -int(item[1].get("gd", 0)),
                -int(item[1].get("gf", 0)),
                str(item[0]),
            ),
        )
    ]


def _team_group_rank(team: str, table: Mapping[str, Mapping[str, int]]) -> Optional[int]:
    for index, ranked_team in enumerate(_ranked_standings(table), start=1):
        if _same_team(team, ranked_team):
            return index
    return None


def _team_group_matches(
    team: str,
    completed_before: Iterable[Mapping[str, Any]],
    group: Any,
) -> List[Mapping[str, Any]]:
    samples = [
        match
        for match in completed_before
        if group
        and match.get("group") == group
        and _is_current_world_cup_match(match)
        and _is_completed(match)
        and (_same_team(team, match.get("home_team")) or _same_team(team, match.get("away_team")))
    ]
    samples.sort(key=lambda item: _parse_datetime(item.get("match_date")) or datetime.min.replace(tzinfo=timezone.utc))
    return samples


def _team_group_review_note(team: str, samples: List[Mapping[str, Any]], match_round: int) -> Optional[str]:
    if not samples:
        return None

    total_points = 0
    goals_for = 0
    goals_against = 0
    latest_for = 0
    latest_against = 0
    latest_opponent = ""
    latest_result = "打平"
    for match in samples:
        home = str(match.get("home_team") or "")
        away = str(match.get("away_team") or "")
        home_score = _safe_int(match.get("home_score")) or 0
        away_score = _safe_int(match.get("away_score")) or 0
        if _same_team(team, home):
            team_for, team_against, opponent = home_score, away_score, away
        elif _same_team(team, away):
            team_for, team_against, opponent = away_score, home_score, home
        else:
            continue
        goals_for += team_for
        goals_against += team_against
        if team_for > team_against:
            total_points += 3
            result = "赢球"
        elif team_for < team_against:
            result = "输球"
        else:
            total_points += 1
            result = "打平"
        latest_for, latest_against, latest_opponent, latest_result = team_for, team_against, opponent, result

    if match_round >= 3:
        return (
            f"{team}小组前{len(samples)}轮累计{total_points}分，进失球{goals_for}-{goals_against}；"
            f"最近一场{latest_for}-{latest_against}{latest_opponent}{latest_result}，"
            "第三轮重点转向出线安全线、名次路径和轮换风险"
        )
    return _team_round_review_note(samples[-1], team)


def _team_group_stage_review_note(team: str, samples: List[Mapping[str, Any]]) -> Optional[str]:
    if not samples:
        return None

    total_points = 0
    goals_for = 0
    goals_against = 0
    latest_for = 0
    latest_against = 0
    latest_opponent = ""
    latest_result = "打平"
    for match in samples:
        home = str(match.get("home_team") or "")
        away = str(match.get("away_team") or "")
        home_score = _safe_int(match.get("home_score")) or 0
        away_score = _safe_int(match.get("away_score")) or 0
        if _same_team(team, home):
            team_for, team_against, opponent = home_score, away_score, away
        elif _same_team(team, away):
            team_for, team_against, opponent = away_score, home_score, home
        else:
            continue
        goals_for += team_for
        goals_against += team_against
        if team_for > team_against:
            total_points += 3
            result = "赢球"
        elif team_for < team_against:
            result = "输球"
        else:
            total_points += 1
            result = "打平"
        latest_for, latest_against, latest_opponent, latest_result = team_for, team_against, opponent, result

    return (
        f"{team}小组赛全阶段累计{total_points}分，进失球{goals_for}-{goals_against}；"
        f"最近一场{latest_for}-{latest_against}{latest_opponent}{latest_result}，"
        "淘汰赛重点转向90分钟控制、加时体能和点球风险"
    )


def _third_round_team_strategy(team: str, table: Mapping[str, Mapping[str, int]]) -> Optional[str]:
    row = None
    table_key = None
    for key, value in table.items():
        if _same_team(team, key):
            table_key = key
            row = value
            break
    if not row:
        return None

    points = int(row.get("points", 0))
    gd = int(row.get("gd", 0))
    rank = _team_group_rank(table_key or team, table) or 0
    prefix = f"{team}{points}分排名第{rank}，净胜球{gd:+d}"
    if rank == 1 and points >= 6:
        return (
            f"{prefix}，小组第一主动权很高；第三轮轮换、控节奏和保护黄牌/伤停权重上升，"
            "除非潜在淘汰赛路径差异非常明确，否则不宜硬追大胜。"
        )
    if rank <= 2 and points >= 4:
        return (
            f"{prefix}，已接近出线但第一/第二路径未定；优先稳住不败，"
            "再根据同组实时比分和潜在淘汰赛对手调整进取心。"
        )
    if points == 3:
        return (
            f"{prefix}，仍在出线边缘；第三轮会更重视抢分和净胜球，"
            "但如果实时比分让平局足够安全，后段也可能降速。"
        )
    return (
        f"{prefix}，安全线不足；第三轮必须主动争胜或抢净胜球，"
        "进攻投入提高，同时被反击打穿的风险也同步上升。"
    )


def _third_round_team_strategy_state(team: str, table: Mapping[str, Mapping[str, int]]) -> Optional[Dict[str, Any]]:
    row = None
    table_key = None
    for key, value in table.items():
        if _same_team(team, key):
            table_key = key
            row = value
            break
    if not row:
        return None
    points = int(row.get("points", 0))
    rank = _team_group_rank(table_key or team, table) or 0
    if rank == 1 and points >= 6:
        status = "locked_first"
    elif rank <= 2 and points >= 4:
        status = "near_qualified"
    elif points <= 1:
        status = "must_win"
    elif points == 3 or rank >= 3:
        status = "edge"
    else:
        status = "unknown"
    return {
        "team": team,
        "points": points,
        "rank": rank,
        "goal_diff": int(row.get("gd", 0)),
        "goals_for": int(row.get("gf", 0)),
        "goals_against": int(row.get("ga", 0)),
        "status": status,
    }


def _third_round_knockout_path_notes(
    home: str,
    away: str,
    table: Mapping[str, Mapping[str, int]],
) -> List[str]:
    if not table:
        return [
            "潜在淘汰赛路径尚未完全锁定，默认不假设主动挑对手；只有第一/第二对应强弱差清晰时，才把路径选择作为低权重变量。"
        ]
    home_rank = _team_group_rank(home, table)
    away_rank = _team_group_rank(away, table)
    home_points = int(table.get(home, {}).get("points", 0)) if home in table else 0
    away_points = int(table.get(away, {}).get("points", 0)) if away in table else 0
    notes = [
        "潜在淘汰赛路径尚未完全锁定，默认不假设主动挑对手；只有第一/第二对应强弱差清晰时，才把路径选择作为低权重变量。"
    ]
    if home_rank and away_rank and home_rank <= 2 and away_rank <= 2 and home_points >= 4 and away_points >= 4:
        notes.append(
            "双方都在出线区并可能争第一/第二路径，领先方更可能先稳不败；若同组另一场实时比分改变名次收益，临场进取心需要动态上调。"
        )
    elif max(home_points, away_points) >= 6 and min(home_points, away_points) <= 3:
        notes.append(
            "一方接近锁定路径、另一方仍需抢分时，锁定方轮换概率更高，低分方更容易把比赛带向开放节奏。"
        )
    return notes


def _team_form_delta(
    team: str,
    matches: Iterable[Mapping[str, Any]],
    before: Optional[datetime],
    current_world_cup_group_only: bool = False,
) -> float:
    deltas: List[float] = []
    for match in matches:
        if not _is_completed(match):
            continue
        if current_world_cup_group_only and not (match.get("group") and not match.get("stage") and _is_current_world_cup_match(match)):
            continue
        match_time = _parse_datetime(match.get("match_date"))
        if before and match_time and match_time >= before:
            continue
        home = str(match.get("home_team") or "")
        away = str(match.get("away_team") or "")
        home_score = _safe_int(match.get("home_score")) or 0
        away_score = _safe_int(match.get("away_score")) or 0
        if _same_team(team, home):
            deltas.append((home_score - away_score) * 0.018)
        elif _same_team(team, away):
            deltas.append((away_score - home_score) * 0.018)
    if not deltas:
        return 0.0
    return round(_clamp(sum(deltas[-3:]) / min(len(deltas), 3), -0.055, 0.055), 4)


def _canonical_team_name(value: Any) -> str:
    text = str(value or "")
    try:
        from services.prediction_model import TEAM_ALIASES

        return str(TEAM_ALIASES.get(text, text))
    except Exception:
        return text


def _same_team(left: Any, right: Any) -> bool:
    return _canonical_team_name(left).casefold() == _canonical_team_name(right).casefold()


def _competition_text(match: Mapping[str, Any]) -> str:
    values = [
        match.get("competition"),
        match.get("tournament"),
        match.get("league"),
        match.get("event"),
        match.get("competition_name"),
    ]
    return " ".join(str(value or "") for value in values).strip().casefold()


def _is_current_world_cup_match(match: Mapping[str, Any]) -> bool:
    text = _competition_text(match)
    if "qualif" in text or "预选" in text:
        return False
    if match.get("group") or match.get("stage"):
        return True
    match_time = _parse_datetime(match.get("match_date"))
    if not match_time or match_time < WORLD_CUP_2026_START:
        return False
    if _safe_int(match.get("round")) is not None and not text:
        return True
    return "world cup" in text or "世界杯" in text or "fifa" in text


def _is_pre_world_cup_official_match(match: Mapping[str, Any]) -> bool:
    if _is_current_world_cup_match(match):
        return False
    match_time = _parse_datetime(match.get("match_date"))
    if match_time and match_time >= WORLD_CUP_2026_START:
        return False
    if match.get("is_official") is False or match.get("official") is False:
        return False
    if match.get("is_official") is True or match.get("official") is True:
        return True

    text = _competition_text(match)
    if any(keyword in text for keyword in FRIENDLY_COMPETITION_KEYWORDS):
        return False
    return any(keyword in text for keyword in OFFICIAL_COMPETITION_KEYWORDS)


def _player_names(values: Any) -> List[str]:
    players: List[str] = []
    if not isinstance(values, list):
        return players
    for item in values:
        if isinstance(item, Mapping):
            name = item.get("name") or item.get("player") or item.get("short_name") or item.get("displayName")
        else:
            name = item
        if name:
            players.append(str(name))
    return players


def _lineup_for_team(team: str, match: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
    report = _report(match)
    lineup_rows = report.get("lineups")
    if not isinstance(lineup_rows, list):
        lineup_rows = match.get("lineups")
    if not isinstance(lineup_rows, list):
        return None

    for row in lineup_rows:
        if not isinstance(row, Mapping):
            continue
        row_team = row.get("team") or row.get("team_name") or row.get("name")
        if row_team and not _same_team(row_team, team):
            continue
        if not row_team:
            side = str(row.get("side") or "").lower()
            if side == "home":
                row_team = match.get("home_team")
            elif side == "away":
                row_team = match.get("away_team")
            if not _same_team(row_team, team):
                continue

        starters = _player_names(row.get("starters") or row.get("starting_xi") or row.get("start_xi") or row.get("startXI") or row.get("lineup"))
        substitutes = _player_names(row.get("substitutes") or row.get("bench") or row.get("subs"))
        formation = str(row.get("formation") or "").strip()
        if formation or starters:
            return {
                "formation": formation,
                "starters": starters,
                "substitutes": substitutes,
                "lineup_source": "current_world_cup_official_matches",
            }
    return None


def _team_match_sample(team: str, match: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
    home = str(match.get("home_team") or "")
    away = str(match.get("away_team") or "")
    home_score = _safe_int(match.get("home_score"))
    away_score = _safe_int(match.get("away_score"))
    if home_score is None or away_score is None or not (_same_team(team, home) or _same_team(team, away)):
        return None

    is_home = _same_team(team, home)
    goals_for = home_score if is_home else away_score
    goals_against = away_score if is_home else home_score
    opponent = away if is_home else home
    points = 3 if goals_for > goals_against else 1 if goals_for == goals_against else 0
    stats = _stats(match)
    red_context = _red_card_context(match)
    side_key = "home" if is_home else "away"
    other_key = "away" if is_home else "home"
    lineup = _lineup_for_team(team, match) or {}

    return {
        "match_id": match.get("id"),
        "round": _safe_int(match.get("round")) or 0,
        "opponent": opponent,
        "score": f"{goals_for}-{goals_against}",
        "points": points,
        "goals_for": goals_for,
        "goals_against": goals_against,
        "goal_diff": goals_for - goals_against,
        "shots_for": _stat(stats, f"shots_{side_key}", f"{side_key}_shots"),
        "shots_against": _stat(stats, f"shots_{other_key}", f"{other_key}_shots"),
        "shots_on_target_for": _stat(stats, f"shots_on_target_{side_key}", f"{side_key}_shots_on_target"),
        "shots_on_target_against": _stat(stats, f"shots_on_target_{other_key}", f"{other_key}_shots_on_target"),
        "corners_for": _stat(stats, f"corners_{side_key}", f"{side_key}_corners"),
        "corners_against": _stat(stats, f"corners_{other_key}", f"{other_key}_corners"),
        "yellow_cards_for": _stat(stats, f"yellow_cards_{side_key}", f"{side_key}_yellow_cards"),
        "yellow_cards_against": _stat(stats, f"yellow_cards_{other_key}", f"{other_key}_yellow_cards"),
        "red_cards_for": red_context.get(side_key, 0),
        "red_cards_against": red_context.get(other_key, 0),
        "formation": lineup.get("formation"),
        "starters": lineup.get("starters") or [],
        "substitutes": lineup.get("substitutes") or [],
        "lineup_source": lineup.get("lineup_source"),
    }


def _avg(samples: List[Mapping[str, Any]], key: str) -> float:
    values = [_safe_float(item.get(key)) for item in samples if item.get(key) is not None]
    if not values:
        return 0.0
    return sum(values) / len(values)


def _average_profile_sample(samples: List[Mapping[str, Any]]) -> Dict[str, Any]:
    if not samples:
        return {}
    latest = samples[-1]
    averaged = {
        key: _avg(samples, key)
        for key in PROFILE_AVERAGE_KEYS
        if any(item.get(key) is not None for item in samples)
    }
    averaged.update(
        {
            "match_id": "sample_average",
            "round": _safe_int(latest.get("round")) or 0,
            "opponent": "sample_average",
            "score": "sample-average",
            "_sort_time": latest.get("_sort_time") or datetime.min.replace(tzinfo=timezone.utc),
        }
    )
    return averaged


def _team_recent_profile(
    team: str,
    matches: Iterable[Mapping[str, Any]],
    before: Optional[datetime],
    use_world_cup_all_matches: bool,
) -> Optional[Dict[str, Any]]:
    world_cup_samples: List[Dict[str, Any]] = []
    pre_world_cup_samples: List[Dict[str, Any]] = []
    for match in matches:
        if not _is_completed(match):
            continue
        match_time = _parse_datetime(match.get("match_date"))
        if before and match_time and match_time >= before:
            continue
        sample = _team_match_sample(team, match)
        if not sample:
            continue
        sample["_sort_time"] = match_time or datetime.min.replace(tzinfo=timezone.utc)
        if _is_current_world_cup_match(match):
            sample["_sample_source"] = "current_world_cup"
            world_cup_samples.append(sample)
        elif _is_pre_world_cup_official_match(match):
            sample["_sample_source"] = "pre_world_cup_official"
            pre_world_cup_samples.append(sample)

    world_cup_samples.sort(key=lambda item: item["_sort_time"])
    pre_world_cup_samples.sort(key=lambda item: item["_sort_time"])
    pre_window = pre_world_cup_samples[-3:]

    if world_cup_samples and (len(world_cup_samples) >= 3 or use_world_cup_all_matches):
        window = list(world_cup_samples)
        source_samples = list(world_cup_samples)
        label = f"本届世界杯{len(world_cup_samples)}场正式赛均值"
        source = "current_world_cup_official_matches"
        pre_sample_count = 0
    elif world_cup_samples and pre_window:
        window = [_average_profile_sample(world_cup_samples), _average_profile_sample(pre_window)]
        source_samples = sorted(world_cup_samples + pre_window, key=lambda item: item["_sort_time"])
        label = f"本届世界杯{len(world_cup_samples)}场 + 世界杯前{len(pre_window)}场正式赛均值"
        source = "world_cup_plus_pre_world_cup_official_matches"
        pre_sample_count = len(pre_window)
    elif world_cup_samples:
        window = list(world_cup_samples)
        source_samples = list(world_cup_samples)
        label = f"本届世界杯{len(world_cup_samples)}场正式赛均值（世界杯前正式赛样本缺失）"
        source = "current_world_cup_official_matches"
        pre_sample_count = 0
    elif pre_window:
        window = list(pre_window)
        source_samples = list(pre_window)
        label = f"世界杯前{len(pre_window)}场正式赛均值"
        source = "pre_world_cup_official_matches"
        pre_sample_count = len(pre_window)
    else:
        return None

    avg_points = _avg(window, "points")
    avg_goal_diff = _avg(window, "goal_diff")
    avg_goals_for = _avg(window, "goals_for")
    avg_goals_against = _avg(window, "goals_against")
    avg_shots_diff = _avg(window, "shots_for") - _avg(window, "shots_against")
    avg_sot_diff = _avg(window, "shots_on_target_for") - _avg(window, "shots_on_target_against")
    avg_corners_for = _avg(window, "corners_for")
    avg_corners_against = _avg(window, "corners_against")
    avg_yellow_for = _avg(window, "yellow_cards_for")
    avg_yellow_against = _avg(window, "yellow_cards_against")
    red_distortion = any(
        (_safe_int(item.get("red_cards_for")) or 0) or (_safe_int(item.get("red_cards_against")) or 0)
        for item in source_samples
    )

    score = (
        5.05
        + avg_points * 0.92
        + avg_goal_diff * 0.48
        + avg_sot_diff * 0.13
        + avg_shots_diff * 0.025
        - avg_goals_against * 0.16
    )
    if avg_goals_for >= 3.0:
        score += 0.35
    if red_distortion:
        score = 6.0 + (score - 6.0) * 0.72
    score = _clamp(score, 3.8, 9.4)

    latest = source_samples[-1]
    note = (
        f"{team}{label}：场均{avg_points:.1f}分，净胜球{avg_goal_diff:+.1f}，"
        f"进失球{avg_goals_for:.1f}-{avg_goals_against:.1f}，射正差{avg_sot_diff:+.1f}"
    )
    if red_distortion:
        note += "；窗口含红牌变量，状态分已做降噪"

    latest_lineup_sample = next(
        (
            item for item in reversed(source_samples)
            if item.get("formation") or item.get("starters")
        ),
        None,
    )
    if latest_lineup_sample and latest_lineup_sample.get("formation"):
        note += f"；最近实际阵型 {latest_lineup_sample.get('formation')} 已纳入下一场战术参照"

    return {
        "team": team,
        "sample_matches": len(source_samples),
        "world_cup_sample_matches": len(world_cup_samples),
        "pre_world_cup_sample_matches": pre_sample_count,
        "source": source,
        "source_label": label,
        "prop_sample_policy": "official_mean",
        "score": round(score, 1),
        "avg_points": round(avg_points, 2),
        "avg_goal_diff": round(avg_goal_diff, 2),
        "avg_goals_for": round(avg_goals_for, 2),
        "avg_goals_against": round(avg_goals_against, 2),
        "avg_shots_diff": round(avg_shots_diff, 2),
        "avg_shots_on_target_diff": round(avg_sot_diff, 2),
        "corners_for": round(avg_corners_for, 2),
        "corners_against": round(avg_corners_against, 2),
        "yellow_cards_for": round(avg_yellow_for, 2),
        "yellow_cards_against": round(avg_yellow_against, 2),
        "latest_score": f"{latest.get('score')} vs {latest.get('opponent')}",
        "red_card_distorted": red_distortion,
        "note": note,
        "latest_formation": latest_lineup_sample.get("formation") if latest_lineup_sample else None,
        "latest_starters": latest_lineup_sample.get("starters") if latest_lineup_sample else [],
        "latest_substitutes": latest_lineup_sample.get("substitutes") if latest_lineup_sample else [],
        "lineup_source": (
            latest_lineup_sample.get("lineup_source")
            if latest_lineup_sample and latest_lineup_sample.get("lineup_source")
            else "current_world_cup_official_matches"
        ),
    }


def _team_round_review_note(match: Mapping[str, Any], team: str) -> Optional[str]:
    home = str(match.get("home_team") or "")
    away = str(match.get("away_team") or "")
    home_score = _safe_int(match.get("home_score"))
    away_score = _safe_int(match.get("away_score"))
    if home_score is None or away_score is None or team not in {home, away}:
        return None

    if team == home:
        goals_for, goals_against, opponent = home_score, away_score, away
    else:
        goals_for, goals_against, opponent = away_score, home_score, home

    if goals_for > goals_against:
        result = "赢球"
        tone = "拿到3分，第二轮可以更主动地管理节奏"
    elif goals_for < goals_against:
        result = "输球"
        tone = "第二轮抢分压力更高，落后时会更早提速"
    else:
        result = "打平"
        tone = "还有抢分空间，但平局价值不能被低估"

    note = f"{team}上一轮{goals_for}-{goals_against}{opponent}{result}，{tone}"
    red_context = _red_card_context(match)
    if red_context["total"]:
        note += "；该场有红牌变量，大比分或后段失控不能完全当作常规实力变化"
    return note


def _build_review_context(
    current_match: Dict[str, Any],
    completed: List[Dict[str, Any]],
    before: Optional[datetime],
) -> Dict[str, Any]:
    home = str(current_match.get("home_team") or "")
    away = str(current_match.get("away_team") or "")
    group = current_match.get("group")
    match_round = _safe_int(current_match.get("round")) or 0
    stage = current_match.get("stage")
    is_knockout_stage = bool(stage)
    use_world_cup_all_matches = bool(stage) or match_round == 0
    completed_before = []
    for match in completed:
        match_time = _parse_datetime(match.get("match_date"))
        if before and match_time and match_time >= before:
            continue
        completed_before.append(match)

    team_notes: List[str] = []
    strategy_notes: List[str] = []
    knockout_path_notes: List[str] = []
    third_round_strategy: Dict[str, Any] = {}
    form_context: Dict[str, Any] = {}
    if is_knockout_stage:
        for side, team in (("home", home), ("away", away)):
            team_matches = [
                match for match in completed_before
                if match.get("group")
                and not match.get("stage")
                and _is_current_world_cup_match(match)
                and (
                    _same_team(team, match.get("home_team"))
                    or _same_team(team, match.get("away_team"))
                )
            ]
            note = _team_group_stage_review_note(team, team_matches)
            if note:
                team_notes.append(note)
            profile = _team_recent_profile(team, completed_before, before, True)
            if profile:
                form_context[side] = profile
    elif match_round >= 2:
        table = _standings(completed_before, str(group), before) if group else {}
        for side, team in (("home", home), ("away", away)):
            team_matches = _team_group_matches(team, completed_before, group) if group else [
                match for match in completed_before
                if _is_current_world_cup_match(match)
                and (
                    _same_team(team, match.get("home_team"))
                    or _same_team(team, match.get("away_team"))
                )
            ]
            if match_round >= 3:
                note = _team_group_review_note(team, team_matches, match_round)
                strategy_note = _third_round_team_strategy(team, table)
                if strategy_note:
                    strategy_notes.append(strategy_note)
                strategy_state = _third_round_team_strategy_state(team, table)
                if strategy_state:
                    third_round_strategy[side] = strategy_state
            else:
                first_round = next((match for match in team_matches if _safe_int(match.get("round")) == 1), None)
                latest = first_round or (team_matches[-1] if team_matches else None)
                note = _team_round_review_note(latest, team) if latest else None
            if note:
                team_notes.append(note)
            profile = _team_recent_profile(team, completed_before, before, use_world_cup_all_matches)
            if profile:
                form_context[side] = profile
        if match_round >= 3 and group:
            knockout_path_notes = _third_round_knockout_path_notes(home, away, table)
            third_round_strategy["path_weight"] = "low"
    elif use_world_cup_all_matches:
        for side, team in (("home", home), ("away", away)):
            profile = _team_recent_profile(team, completed_before, before, True)
            if profile:
                form_context[side] = profile

    same_group_completed = [
        match for match in completed_before
        if group and match.get("group") == group
    ]
    group_stage_completed = [
        match for match in completed_before
        if match.get("group") and not match.get("stage") and _is_current_world_cup_match(match)
    ]
    red_card_notes = []
    for match in completed_before:
        match_teams = {str(match.get("home_team") or ""), str(match.get("away_team") or "")}
        related = bool((group and match.get("group") == group) or home in match_teams or away in match_teams)
        if not related:
            continue
        red_context = _red_card_context(match)
        if not red_context["total"]:
            continue
        home_score = _safe_int(match.get("home_score")) or 0
        away_score = _safe_int(match.get("away_score")) or 0
        if home_score + away_score >= 4 or abs(home_score - away_score) >= 2:
            red_card_notes.append(
                f"{match.get('home_team')} {home_score}-{away_score} {match.get('away_team')} 含红牌变量，后续复盘按结构性异常处理"
            )

    if is_knockout_stage:
        mode = "knockout_group_stage_review"
        summary = "淘汰赛观点读取两队小组赛全阶段表现，并单独处理90分钟、加时和点球决胜层。"
    elif match_round >= 3 and group:
        mode = "third_round_group_strategy"
        summary = "第三轮观点优先读取小组前两轮表现、出线路径和潜在淘汰赛对手。"
    elif team_notes:
        mode = "actual_first_round_review"
        summary = "已匹配到两队上一轮真实赛果，第二轮观点优先读取真实复盘。"
    else:
        mode = "simulated_backtest_review"
        summary = "暂无两队完整上一轮复盘样本，使用当前模型回测纪律兜底。"

    fallback_notes = [
        "回测兜底先看五项：赛果方向、首选比分、Top3比分池、总进球区间、双方进球。",
        "缺少真实复盘时不硬改强弱，只把平局保护、大胜溢出和模板比分偏置写进风险池。",
    ]

    return {
        "mode": mode,
        "summary": summary,
        "completed_sample_count": len(completed_before),
        "same_group_completed_count": len(same_group_completed),
        "group_stage_completed_count": len(group_stage_completed),
        "team_review_notes": team_notes[:4],
        "strategy_notes": strategy_notes[:4],
        "knockout_path_notes": knockout_path_notes[:3],
        "third_round_strategy": third_round_strategy,
        "form_context": form_context,
        "red_card_notes": red_card_notes[:3],
        "fallback_notes": fallback_notes,
    }


def build_review_adjustment(current_match: Dict[str, Any], completed_matches: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    completed = list(completed_matches)
    home = str(current_match.get("home_team") or "")
    away = str(current_match.get("away_team") or "")
    group = current_match.get("group")
    match_round = _safe_int(current_match.get("round")) or 0
    stage = current_match.get("stage")
    is_knockout_stage = bool(stage)
    before = _parse_datetime(current_match.get("match_date"))
    reasons: List[str] = []
    draw_delta = 0.0

    home_attack_delta = _team_form_delta(home, completed, before, current_world_cup_group_only=is_knockout_stage)
    away_attack_delta = _team_form_delta(away, completed, before, current_world_cup_group_only=is_knockout_stage)
    if is_knockout_stage:
        delta_label = "小组赛全阶段状态校准"
    elif group and match_round >= 3:
        delta_label = "小组前两轮状态校准"
    else:
        delta_label = "首轮状态校准"
    if home_attack_delta:
        reasons.append(f"{home} {delta_label} {home_attack_delta:+.3f}")
    if away_attack_delta:
        reasons.append(f"{away} {delta_label} {away_attack_delta:+.3f}")

    if group and match_round >= 2:
        table = _standings(completed, str(group), before)
        home_points = table.get(home, {}).get("points", 0)
        away_points = table.get(away, {}).get("points", 0)
        after_draw_home = home_points + 1
        after_draw_away = away_points + 1
        if match_round >= 3 and min(home_points, away_points) <= 1:
            reasons.append("第三轮低分方安全线不足，平局不做硬加权；优先观察必须争胜方是否提前提速。")
        elif after_draw_home >= 4 and after_draw_away >= 4:
            draw_delta = 0.05
            if match_round >= 3:
                reasons.append("第三轮平局可让双方至少达到4分，出线位置明显改善；但名次和潜在淘汰赛路径只按低权重校准。")
            else:
                reasons.append("平局可让双方至少达到4分，出线位置明显改善，因此小幅提高平局权重。")
        elif home_points >= 3 and away_points >= 3:
            draw_delta = 0.04
            if match_round >= 3:
                reasons.append("双方前两轮都有积分，第三轮平局对出线或名次路径都有价值，因此保守提高平局权重。")
            else:
                reasons.append("双方首轮都有积分，平局对小组形势都有价值，因此保守提高平局权重。")
        elif min(after_draw_home, after_draw_away) >= 2 and match_round == 3:
            draw_delta = 0.025
            reasons.append("小组赛末轮积分压力提高双方接受平局的可能性。")

    review_context = _build_review_context(current_match, completed, before)
    return {
        "applied": bool(reasons or draw_delta),
        "home_attack_delta": home_attack_delta,
        "away_attack_delta": away_attack_delta,
        "draw_probability_delta": round(draw_delta, 4),
        "reasons": reasons,
        "source": "post_match_review_public_feed",
        "review_context": review_context,
    }
