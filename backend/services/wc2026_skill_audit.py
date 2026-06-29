from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple


DRAW_SCORES = ("0-0", "1-1", "2-2")
TEMPLATE_SCORES = {"2-0", "2-1", "1-2", "0-2"}


def _num(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _trim_sentence(value: str) -> str:
    return str(value).strip().rstrip("。；; ")


def _join_sentence_items(items: Iterable[str], limit: int = 2) -> str:
    return "；".join(_trim_sentence(item) for item in list(items)[:limit] if _trim_sentence(item))


def _unique_scores(prediction: Dict[str, Any]) -> List[str]:
    scores: List[str] = []
    primary = prediction.get("predicted_score")
    if primary:
        scores.append(str(primary))
    for item in prediction.get("possible_scores") or []:
        score = item.get("score") if isinstance(item, dict) else None
        if score and str(score) not in scores:
            scores.append(str(score))
    return scores[:3]


def _parse_score(score: str) -> Tuple[int, int] | None:
    try:
        home, away = str(score).replace(":", "-").split("-")[:2]
        return int(home), int(away)
    except (TypeError, ValueError):
        return None


def _favorite(prediction: Dict[str, Any]) -> Tuple[str, float, Dict[str, float]]:
    values = {
        "home": _num(prediction.get("home_win_probability")),
        "draw": _num(prediction.get("draw_probability")),
        "away": _num(prediction.get("away_win_probability")),
    }
    side = max(values, key=values.get)
    return side, values[side], values


def _knockout_layer(prediction: Dict[str, Any]) -> Dict[str, float]:
    decision = prediction.get("knockout_decision")
    decision_map = decision if isinstance(decision, Mapping) else {}
    regular_draw = _num(
        decision_map.get("regular_time_draw_probability"),
        _num(prediction.get("extra_time_probability")),
    )
    penalty = _num(decision_map.get("penalty_probability"), _num(prediction.get("penalty_probability")))
    extra_decisive = _num(
        decision_map.get("extra_time_decisive_probability"),
        max(0.0, regular_draw - penalty),
    )
    return {
        "regular_time_home_win_probability": _num(decision_map.get("regular_time_home_win_probability")),
        "regular_time_draw_probability": regular_draw,
        "regular_time_away_win_probability": _num(decision_map.get("regular_time_away_win_probability")),
        "extra_time_probability": _num(decision_map.get("extra_time_probability"), regular_draw),
        "extra_time_decisive_probability": max(0.0, extra_decisive),
        "penalty_probability": min(regular_draw, max(0.0, penalty)),
        "advancement_home_probability": _num(
            decision_map.get("advancement_home_probability"),
            _num(prediction.get("home_win_probability")),
        ),
        "advancement_away_probability": _num(
            decision_map.get("advancement_away_probability"),
            _num(prediction.get("away_win_probability")),
        ),
    }


def _team_for_side(match: Dict[str, Any], side: str) -> str:
    if side == "home":
        return str(match.get("home_team") or "主队")
    if side == "away":
        return str(match.get("away_team") or "客队")
    return "平局"


def _evidence_status(prediction: Dict[str, Any], match: Dict[str, Any]) -> Dict[str, Any]:
    market = prediction.get("market_calibration") or {}
    market_odds = prediction.get("market_odds") or {}
    has_xg = prediction.get("xg_home") is not None and prediction.get("xg_away") is not None
    missing: List[str] = []
    proxy: List[str] = ["FIFA排名/Elo实力", "模型xG比分矩阵", "赛程与比赛阶段"]
    status = "partial"
    data_quality = "C"

    if market.get("applied"):
        status = "partial-high"
        data_quality = "B"
        proxy.append("赛前市场共识校准")
    elif has_xg:
        status = "partial"
        data_quality = "B"
    else:
        status = "partial"
        data_quality = "C"
        missing.append("缺少可用xG矩阵，只能按基础实力和比分分布降级处理")

    if not match.get("group") and not match.get("stage"):
        missing.append("小组积分上下文未传入，战意判断只按赛程阶段处理")
    if not market.get("applied"):
        status_text = str(market_odds.get("status") or market.get("level") or "")
        if status_text == "historical_prior":
            missing.append("实时赔率 key 未配置；已使用 Football-Data 历史赔率样本低权重参考，不做硬校准")
        elif status_text in {"disabled", "not_configured", "unsupported_provider"}:
            missing.append("实时赔率源待配置或关闭；本场只用公开赛果、历史赔率样本与模型矩阵做风险参考")
        else:
            missing.append("实时赔率未匹配到本场；仅作为风险提示，不做硬校准")

    return {
        "status": status,
        "data_quality": data_quality,
        "missing_information": missing,
        "proxy_evidence_used": proxy,
        "confidence_adjustment": "降一档处理，比分池优先覆盖比赛形态" if status == "partial" else "可做正式分析，但仍保留赛前阵容/盘口风险提示",
    }


def _classify_match(prediction: Dict[str, Any]) -> Dict[str, str]:
    home = _num(prediction.get("home_win_probability"))
    draw = _num(prediction.get("draw_probability"))
    away = _num(prediction.get("away_win_probability"))
    if prediction.get("is_knockout") or prediction.get("knockout_decision"):
        draw = max(draw, _knockout_layer(prediction)["regular_time_draw_probability"])
    home_xg = _num(prediction.get("xg_home"))
    away_xg = _num(prediction.get("xg_away"))
    total_xg = home_xg + away_xg
    favorite_side, favorite_prob, _values = _favorite(prediction)
    win_diff = abs(home - away)

    primary = "Unknown"
    secondary = "证据不足，降低精确比分置信度"
    label = "证据不足"
    reasoning: List[str] = []

    if favorite_side in {"home", "away"} and favorite_prob >= 0.61 and win_diff >= 0.25:
        primary = "A"
        label = "A 强队突破"
        secondary = "领先后可能继续冲净胜球"
        reasoning.append("胜率和实力差已经拉开，先按强队能破局处理")
    elif favorite_side in {"home", "away"} and (draw >= 0.25 or favorite_prob < 0.56):
        primary = "B"
        label = "B 热门受阻"
        secondary = "窄胜或平局需要进比分池"
        reasoning.append("热门优势没有完全打穿，平局/低比分需要保护")

    if total_xg >= 3.05 and min(home_xg, away_xg) >= 0.82:
        if primary == "A":
            primary = "A/C"
            label = "A/C 强队突破 + 对攻风险"
        elif primary == "Unknown":
            primary = "C"
            label = "C 开放对攻"
        else:
            primary = "C"
            label = "C 开放对攻"
        secondary = "双方进球与 2-1/1-2/2-2 形态要保留"
        reasoning.append("总xG和弱侧xG都不低，比赛更像有来回的开放局")

    if total_xg <= 2.55 or draw >= 0.31:
        if primary not in {"A", "A/C"}:
            primary = "D"
            label = "D 低比分/平局保护"
            secondary = "0-0、1-1、1-0 形态优先检查"
            reasoning.append("总进球或平局概率提示低节奏风险")

    if not reasoning:
        reasoning.append("当前主要依据来自模型胜平负、xG 和比分矩阵")

    return {
        "primary": primary,
        "label": label,
        "secondary_risk": secondary,
        "reasoning": "；".join(reasoning[:3]),
    }


def _total_range(home_xg: float, away_xg: float, match_type: str) -> str:
    total = home_xg + away_xg
    if match_type in {"A", "A/C"} and total >= 3.25:
        return "3-6"
    if total < 2.55:
        return "0-3"
    if total < 3.25:
        return "2-4"
    return "3-6"


def _draw_candidate(home_xg: float, away_xg: float) -> str:
    total = home_xg + away_xg
    if total >= 3.35 and min(home_xg, away_xg) >= 1.15:
        return "2-2"
    if total <= 2.25:
        return "0-0"
    return "1-1"


def _overflow_candidates(favorite_side: str) -> List[str]:
    if favorite_side == "away":
        return ["0-3", "1-3", "1-4", "0-4", "1-5"]
    return ["3-0", "3-1", "4-1", "4-0", "5-0", "5-1"]


def _build_score_pool(
    prediction: Dict[str, Any],
    match: Dict[str, Any],
    evidence: Dict[str, Any],
    match_type: Dict[str, str],
) -> Dict[str, Any]:
    home_xg = _num(prediction.get("xg_home"))
    away_xg = _num(prediction.get("xg_away"))
    draw = _num(prediction.get("draw_probability"))
    favorite_side, favorite_prob, values = _favorite(prediction)
    scores = _unique_scores(prediction)
    if not scores:
        scores = ["1-1"]

    primary_type = match_type["primary"]
    action = "keep"
    reasons: List[str] = []
    risk_flags: List[str] = []
    secondary_scores: List[str] = []

    is_knockout = bool(match.get("stage") or prediction.get("is_knockout"))
    knockout_layer = _knockout_layer(prediction) if is_knockout else {}
    regular_time_draw = _num(knockout_layer.get("regular_time_draw_probability"))
    is_group_match = bool(match.get("group") or (match.get("round") and not match.get("stage")))
    match_round = int(match.get("round") or 0)
    has_draw_score = any(score in DRAW_SCORES for score in scores)
    needs_draw = (
        is_group_match
        and evidence["status"] == "partial"
        and primary_type not in {"A", "A/C"}
        and (draw >= 0.22 or favorite_prob < 0.58 or match_round in {1, 3})
    )
    if needs_draw and not has_draw_score:
        draw_score = _draw_candidate(home_xg, away_xg)
        if len(scores) >= 3:
            scores = scores[:2] + [draw_score]
        else:
            scores.append(draw_score)
        action = "draw_protection"
        reasons.append(f"证据为 partial，且热门没有完全拉开，把 {draw_score} 放进Top3防平局")
        risk_flags.append("平局保护：热门优势不足或小组赛语境下，不能只给顺胜比分")

    needs_knockout_draw = (
        is_knockout
        and not has_draw_score
        and regular_time_draw >= 0.22
        and primary_type not in {"A"}
    )
    if needs_knockout_draw:
        draw_score = _draw_candidate(home_xg, away_xg)
        if len(scores) >= 3:
            scores = scores[:2] + [draw_score]
        else:
            scores.append(draw_score)
        action = "draw_protection" if action == "keep" else f"{action}+draw_protection"
        reasons.append(f"淘汰赛90分钟平局约{regular_time_draw:.0%}，把 {draw_score} 放进Top3防加时")
        risk_flags.append("加时风险：淘汰赛不输出赛果平局，但90分钟平局必须进入比分池")

    if primary_type in {"A", "A/C"} and favorite_side in {"home", "away"}:
        overflow = next((score for score in _overflow_candidates(favorite_side) if score not in scores), None)
        if overflow:
            secondary_scores.append(overflow)
            action = "overflow_watch" if action == "keep" else f"{action}+overflow_watch"
            team = _team_for_side(match, favorite_side)
            reasons.append(f"{team} 属于强队突破方向，{overflow} 只作为大胜溢出风险，不替代第一比分")
            risk_flags.append(f"大胜溢出：若早进球或对手被迫压上，{overflow} 需要在次级池观察")

    if prediction.get("predicted_score") in TEMPLATE_SCORES:
        risk_flags.append("模板比分偏置：首选落在2-0/2-1簇，复盘时要单独检查是否漏了1-1或3-1")

    btts = "yes" if min(home_xg, away_xg) >= 0.9 and home_xg + away_xg >= 2.65 else "lean-no"

    return {
        "score_pool_top3": scores[:3],
        "secondary_scores": secondary_scores[:4],
        "score_adjustment": {
            "action": action,
            "reasons": reasons,
        },
        "risk_flags": risk_flags,
        "total_goals_range": _total_range(home_xg, away_xg, primary_type),
        "btts_view": btts,
        "probability_range": {
            "home": _prob_range(values["home"]),
            "draw": _prob_range(values["draw"]),
            "away": _prob_range(values["away"]),
        },
    }


def _prob_range(value: float) -> Dict[str, float]:
    spread = 0.045 if value < 0.62 else 0.06
    return {
        "p10": round(max(0.01, value - spread), 3),
        "p50": round(value, 3),
        "p90": round(min(0.96, value + spread), 3),
    }


def _group_motivation(match: Dict[str, Any], group_context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    match_round = int(match.get("round") or 0)
    is_knockout = bool(match.get("stage"))
    home = str(match.get("home_team") or "主队")
    away = str(match.get("away_team") or "客队")
    home_points = None
    away_points = None
    home_rank = None
    away_rank = None
    home_gd = None
    away_gd = None
    if group_context:
        home_context = group_context.get("home") or {}
        away_context = group_context.get("away") or {}
        home_points = home_context.get("points")
        away_points = away_context.get("points")
        home_rank = home_context.get("rank")
        away_rank = away_context.get("rank")
        home_gd = home_context.get("goal_diff")
        away_gd = away_context.get("goal_diff")

    draw_value = match_round >= 3
    notes: List[str] = []
    strategy_notes: List[str] = []
    if is_knockout:
        draw_value = False
        notes.append("淘汰赛不再按小组积分计算战意，先读取小组赛全阶段表现，再单独评估90分钟打平后的加时/点球")
    elif match_round >= 3:
        notes.append("第三轮优先看出线安全线、名次路径、轮换风险和潜在淘汰赛对手，不再只按上一场复盘下结论")
    elif match_round == 2:
        notes.append("第二轮开始积分形势会改变风险偏好，领先方未必全程强攻")
    elif match_round == 1:
        if str(match.get("status") or "") == "completed":
            notes.append("本场首轮真实结果已纳入复盘样本，不再按结果未知处理")
        else:
            notes.append("首轮真实样本已纳入模型参考；本场若仍未开赛，只把临场首发和盘口当作待确认变量")

    if home_points is not None and away_points is not None:
        if not is_knockout:
            draw_value = draw_value or (int(home_points) >= 3 and int(away_points) >= 3)
        notes.append(f"当前积分参考：{home} {home_points}分，{away} {away_points}分")
        if not is_knockout and match_round >= 3:
            if int(home_points) >= 6 or int(away_points) >= 6:
                strategy_notes.append("已有球队接近锁定出线或小组第一，第三轮轮换、控节奏和保护核心球员概率上升")
            if int(home_points) >= 4 and int(away_points) >= 4:
                strategy_notes.append("双方都接近出线区，平局/不败价值高；若第一/第二路径对手差异清晰，路径选择只做低权重修正")
            if min(int(home_points), int(away_points)) <= 1:
                strategy_notes.append("低分方安全线不足，必须争胜或抢净胜球，比赛更容易被带向开放节奏")

    return {
        "round": match_round,
        "stage": match.get("stage"),
        "draw_value": bool(draw_value),
        "home_points": home_points,
        "away_points": away_points,
        "home_rank": home_rank,
        "away_rank": away_rank,
        "home_goal_diff": home_gd,
        "away_goal_diff": away_gd,
        "notes": notes,
        "strategy_notes": strategy_notes,
    }


def _macro_takeaways(match: Dict[str, Any], score_pool: Dict[str, Any], group_motivation: Dict[str, Any]) -> List[str]:
    takeaways: List[str] = []
    if match.get("stage"):
        takeaways.append("淘汰赛特点：90分钟平局不再作为赛果输出，必须拆到加时和点球决胜层。")
    elif group_motivation["round"] >= 3:
        takeaways.append("第三轮特点：平局价值比前两轮更高，很多队拿1分就可能走第二名或最佳第三路径。")
    if score_pool["score_adjustment"]["action"].startswith("draw_protection"):
        takeaways.append("最不稳方向：热门窄胜局，如果迟迟没有早球，1-1 会比 2-0 更贴近比赛形态。")
    if "overflow_watch" in score_pool["score_adjustment"]["action"]:
        takeaways.append("保留大胜溢出：强队若先破局，对手后段压上会把 3-1、4-1 这类比分抬进次级风险。")
    if not takeaways:
        takeaways.append("当前模型与复核观点方向基本一致，重点看临场阵容和市场是否出现反向信号。")
    return takeaways


def _review_layer(prediction: Dict[str, Any], match: Dict[str, Any], group_motivation: Dict[str, Any]) -> Dict[str, Any]:
    home = str(match.get("home_team") or "主队")
    away = str(match.get("away_team") or "客队")
    match_round = int(match.get("round") or 0)
    is_knockout = bool(match.get("stage") or prediction.get("is_knockout"))
    review_adjustment = prediction.get("review_adjustment")
    review_context: Mapping[str, Any] = {}
    if isinstance(review_adjustment, Mapping):
        raw_context = review_adjustment.get("review_context")
        if isinstance(raw_context, Mapping):
            review_context = raw_context

    mode = str(review_context.get("mode") or "")
    team_notes = [str(item) for item in review_context.get("team_review_notes") or [] if item]
    strategy_notes = [str(item) for item in review_context.get("strategy_notes") or [] if item]
    knockout_path_notes = [str(item) for item in review_context.get("knockout_path_notes") or [] if item]
    red_card_notes = [str(item) for item in review_context.get("red_card_notes") or [] if item]
    fallback_notes = [str(item) for item in review_context.get("fallback_notes") or [] if item]
    adjustment_reasons = []
    if isinstance(review_adjustment, Mapping):
        adjustment_reasons = [str(item) for item in review_adjustment.get("reasons") or [] if item]

    if is_knockout and mode == "knockout_group_stage_review":
        primary_notes = team_notes or strategy_notes
        paragraph = (
            f"{home} vs {away}：淘汰赛单场简析先读取小组赛全阶段表现，"
            "再把90分钟、加时和点球拆开。"
        )
        if primary_notes:
            paragraph += f"{_join_sentence_items(primary_notes)}。"
        if adjustment_reasons:
            paragraph += f"模型把{_join_sentence_items(adjustment_reasons)}作为状态校准，不再套用小组赛平局动机。"
        source_label = "淘汰赛全小组赛复盘"
    elif is_knockout:
        notes = team_notes or fallback_notes or [
            "小组赛全阶段样本不足时，先按Elo/FIFA排名、xG矩阵和球队特征库兜底，再把加时/点球作为单独风险层。"
        ]
        paragraph = (
            f"{home} vs {away}：淘汰赛预测先按小组赛全阶段和当前模型兜底复核，"
            f"{notes[0]}90分钟打平后再进入加时/点球，不把赛果平局直接当最终结果。"
        )
        source_label = "淘汰赛全小组赛复盘"
    elif match_round >= 3 and mode == "third_round_group_strategy":
        primary_notes = strategy_notes or team_notes or [str(item) for item in group_motivation.get("strategy_notes") or [] if item]
        paragraph = (
            f"{home} vs {away}：第三轮单场简析先看出线形势、名次路径和潜在淘汰赛对手。"
        )
        if primary_notes:
            paragraph += f"{_join_sentence_items(primary_notes)}。"
        if knockout_path_notes:
            paragraph += f"路径复核：{_trim_sentence(knockout_path_notes[0])}。"
        if adjustment_reasons:
            paragraph += f" 模型只把{_join_sentence_items(adjustment_reasons)}作为低权重校准，不直接假设球队主动挑对手。"
        source_label = "第三轮战意与路径复核"
    elif match_round >= 2 and mode == "actual_first_round_review" and team_notes:
        paragraph = (
            f"{home} vs {away}：这场先结合上一轮真实复盘看。"
            f"{'；'.join(team_notes[:2])}。"
        )
        if adjustment_reasons:
            paragraph += f"模型已经把{'；'.join(adjustment_reasons[:2])}纳入校准，所以第二轮不只看纸面实力。"
        elif group_motivation.get("notes"):
            paragraph += f"{group_motivation['notes'][0]}。"
        source_label = "上一轮真实复盘"
    elif match_round >= 2:
        notes = fallback_notes or [
            "当前没有匹配到两队完整上一轮复盘，按当前模型回测纪律兜底：先看赛果方向，再看首选比分、Top3比分池、总进球和双方进球。"
        ]
        round_label = "第三轮" if match_round >= 3 else "第二轮"
        prior_label = "前两轮" if match_round >= 3 else "首轮"
        paragraph = (
            f"{home} vs {away}：{round_label}应该参考{prior_label}，但暂时没有足够的同队复盘样本。"
            f"{notes[0]}这意味着本场不会因为一场缺失样本就硬改强弱，只把平局保护和大胜溢出放进风险判断。"
        )
        source_label = "模拟回测复盘兜底"
    elif str(match.get("status") or "") == "completed":
        paragraph = (
            f"{home} vs {away}：本场首轮真实结果已进入复盘样本，后续再预测同组第二轮时会读取这场表现，"
            "不会再按赛前基线处理。"
        )
        source_label = "首轮真实赛果"
    else:
        paragraph = (
            f"{home} vs {away}：首轮比赛先以基础实力、xG矩阵和赛程语境为主，"
            "真实赛后复盘出来后再回写到第二轮和第三轮。"
        )
        source_label = "赛前模型基线"

    red_card_note = ""
    if red_card_notes:
        red_card_note = f"同时复盘池标记了红牌异常：{red_card_notes[0]}，这类大比分不能直接等同于常规攻防强度。"

    return {
        "source": source_label,
        "mode": mode or "model_baseline",
        "paragraph": paragraph,
        "team_notes": team_notes,
        "strategy_notes": strategy_notes,
        "knockout_path_notes": knockout_path_notes,
        "red_card_notes": red_card_notes,
        "fallback_notes": fallback_notes,
        "red_card_note": red_card_note,
    }


def _brief(
    prediction: Dict[str, Any],
    match: Dict[str, Any],
    match_type: Dict[str, str],
    score_pool: Dict[str, Any],
    group_motivation: Dict[str, Any],
    review_layer: Dict[str, Any],
) -> Dict[str, Any]:
    home = str(match.get("home_team") or "主队")
    away = str(match.get("away_team") or "客队")
    first = str(prediction.get("predicted_score") or score_pool["score_pool_top3"][0])
    home_xg = _num(prediction.get("xg_home"))
    away_xg = _num(prediction.get("xg_away"))
    home_p = _num(prediction.get("home_win_probability"))
    draw_p = _num(prediction.get("draw_probability"))
    away_p = _num(prediction.get("away_win_probability"))
    favorite_side, _favorite_prob, _values = _favorite(prediction)
    favorite = _team_for_side(match, favorite_side)
    pool = " / ".join(score_pool["score_pool_top3"])
    secondary = " / ".join(score_pool["secondary_scores"])
    is_knockout = bool(match.get("stage") or prediction.get("is_knockout"))
    knockout_layer = _knockout_layer(prediction) if is_knockout else {}
    regular_draw = _num(knockout_layer.get("regular_time_draw_probability"))
    extra_decisive = _num(knockout_layer.get("extra_time_decisive_probability"))
    penalty = _num(knockout_layer.get("penalty_probability"))

    opener = str(review_layer.get("paragraph") or "")
    if is_knockout:
        model_view = (
            f"模型层面90分钟首选 {first}，晋级概率约 {home} {home_p:.0%} / {away} {away_p:.0%}，"
            f"90分钟平局约 {regular_draw:.0%}，加时决胜约 {extra_decisive:.0%}，点球决胜约 {penalty:.0%}；"
            f"xG 为 {home_xg:.2f}-{away_xg:.2f}，比赛类型先按{match_type['label']}处理。"
        )
    else:
        model_view = (
            f"模型层面首选 {first}，胜平负中位约 {home_p:.0%}/{draw_p:.0%}/{away_p:.0%}，"
            f"xG 为 {home_xg:.2f}-{away_xg:.2f}，比赛类型先按{match_type['label']}处理。"
        )
    shape = (
        f"Top3 比分池给 {pool}。"
        if score_pool["score_adjustment"]["action"] == "keep"
        else f"Top3 调整为 {pool}，核心原因是：{'；'.join(score_pool['score_adjustment']['reasons'])}。"
    )
    if secondary:
        shape += f" 次级风险保留 {secondary}。"

    pressure = ""
    if is_knockout:
        pressure = "淘汰赛没有最终平局，90分钟平局只代表进入加时/点球的路径风险；主选比分和晋级概率要分开读。"
    elif group_motivation["draw_value"]:
        pressure = "小组形势里平局价值不低，领先方或强队已基本占位时，后段未必一直强行打穿。"
    elif favorite_side in {"home", "away"}:
        pressure = f"{favorite} 是主方向，但第一比分不能和覆盖池混为一谈；主选负责精确命中，Top3 负责描述比赛形态。"
    else:
        pressure = "这场胜平负没有明显拉开，第一比分置信度应降一档，重点看比分池覆盖。"

    red_card_note = str(review_layer.get("red_card_note") or "")
    paragraphs = [opener, model_view + shape, pressure]
    if red_card_note:
        paragraphs.append(red_card_note)

    bullets = [
        f"复盘来源：{review_layer.get('source') or '赛前模型基线'}",
        f"比赛类型：{match_type['label']}，副风险：{match_type['secondary_risk']}",
        f"总进球区间：{score_pool['total_goals_range']}，双方进球：{'倾向是' if score_pool['btts_view'] == 'yes' else '偏否'}",
        f"最大风险：{score_pool['risk_flags'][0] if score_pool['risk_flags'] else '临场阵容/盘口反向变化'}",
    ]
    if is_knockout:
        bullets[2] = f"决胜层：90分钟平局 {regular_draw:.0%}，加时决胜 {extra_decisive:.0%}，点球决胜 {penalty:.0%}"

    return {
        "title": f"单场简析：{home} vs {away}",
        "paragraphs": paragraphs,
        "bullets": bullets,
    }


def build_skill_audit(
    prediction: Dict[str, Any],
    match: Optional[Dict[str, Any]] = None,
    group_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build a WC2026 prediction review for one model prediction."""
    match_payload = dict(match or {})
    match_payload.setdefault("home_team", prediction.get("home_team") or "主队")
    match_payload.setdefault("away_team", prediction.get("away_team") or "客队")

    evidence = _evidence_status(prediction, match_payload)
    match_type = _classify_match(prediction)
    score_pool = _build_score_pool(prediction, match_payload, evidence, match_type)
    group_motivation = _group_motivation(match_payload, group_context)
    macro = _macro_takeaways(match_payload, score_pool, group_motivation)
    review_layer = _review_layer(prediction, match_payload, group_motivation)
    brief = _brief(prediction, match_payload, match_type, score_pool, group_motivation, review_layer)
    knockout_decision = _knockout_layer(prediction) if (match_payload.get("stage") or prediction.get("is_knockout")) else None

    return {
        "workflow": "WC2026 prediction review",
        "evidence_status": evidence["status"],
        "data_quality": evidence["data_quality"],
        "missing_information": evidence["missing_information"],
        "proxy_evidence_used": evidence["proxy_evidence_used"],
        "confidence_adjustment": evidence["confidence_adjustment"],
        "match_type": match_type,
        "probability_range": score_pool["probability_range"],
        "first_score_pick": str(prediction.get("predicted_score") or score_pool["score_pool_top3"][0]),
        "score_pool_top3": score_pool["score_pool_top3"],
        "secondary_scores": score_pool["secondary_scores"],
        "score_adjustment": score_pool["score_adjustment"],
        "total_goals_range": score_pool["total_goals_range"],
        "btts_view": score_pool["btts_view"],
        "risk_flags": score_pool["risk_flags"],
        "group_motivation": group_motivation,
        "macro_takeaways": macro,
        "review_layer": review_layer,
        "knockout_decision": knockout_decision,
        "single_match_brief": brief,
        "recordkeeping": {
            "freeze_before_kickoff": ["first_score_pick", "score_pool_top3", "total_goals_range", "btts_view", "evidence_status"],
            "fill_after_match": ["actual_score", "red_cards", "penalties", "late_goals", "score_pool_hit", "miss_attribution"],
        },
    }
