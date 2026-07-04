#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Metric aggregation and CSV/JSON export for v3 experiment wrapper."""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from statistics import mean, median, pstdev
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple
import csv
import json
import math


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        result = float(value)
        if math.isnan(result) or math.isinf(result):
            return default
        return result
    except Exception:
        return default


def safe_div(num: float, den: float, default: float = 0.0) -> float:
    return default if den == 0 else num / den


def numeric_values(rows: Sequence[Dict[str, Any]], key: str) -> List[float]:
    values: List[float] = []
    for row in rows:
        value = row.get(key)
        if value in (None, ""):
            continue
        try:
            f = float(value)
            if not math.isnan(f) and not math.isinf(f):
                values.append(f)
        except Exception:
            continue
    return values


def summarize(values: Sequence[float], prefix: str) -> Dict[str, Any]:
    vals = [float(v) for v in values if not math.isnan(float(v)) and not math.isinf(float(v))]
    if not vals:
        return {
            f"{prefix}_n": 0,
            f"{prefix}_mean": "",
            f"{prefix}_std": "",
            f"{prefix}_median": "",
            f"{prefix}_min": "",
            f"{prefix}_max": "",
        }
    return {
        f"{prefix}_n": len(vals),
        f"{prefix}_mean": mean(vals),
        f"{prefix}_std": pstdev(vals) if len(vals) > 1 else 0.0,
        f"{prefix}_median": median(vals),
        f"{prefix}_min": min(vals),
        f"{prefix}_max": max(vals),
    }


def write_csv(path: Path, rows: Sequence[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        with path.open("w", encoding="utf-8", newline="") as f:
            f.write("")
        return
    fieldnames: List[str] = []
    seen = set()
    for row in rows:
        for key in row.keys():
            if key not in seen:
                fieldnames.append(key)
                seen.add(key)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def read_csv(path: Path) -> List[Dict[str, Any]]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def group_rows(rows: Iterable[Dict[str, Any]], keys: Sequence[str]) -> Dict[Tuple[Any, ...], List[Dict[str, Any]]]:
    groups: Dict[Tuple[Any, ...], List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[tuple(row.get(k, "") for k in keys)].append(row)
    return groups


def coordination_streaks(flags: Sequence[int]) -> List[int]:
    streaks: List[int] = []
    current = 0
    for flag in flags:
        if int(flag):
            current += 1
        elif current:
            streaks.append(current)
            current = 0
    if current:
        streaks.append(current)
    return streaks


def recovery_after_defection(rows: Sequence[Dict[str, Any]]) -> float:
    if len(rows) < 2:
        return 0.0
    opportunities = 0
    recoveries = 0
    for prev, cur in zip(rows[:-1], rows[1:]):
        prev_bad = int(prev.get("mutual_defection_flag", 0)) or int(prev.get("unilateral_exploitation_flag", 0))
        if prev_bad:
            opportunities += 1
            if int(cur.get("mutual_cooperation_flag", 0)):
                recoveries += 1
    return safe_div(recoveries, opportunities)


def episode_general_metrics(rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    if not rows:
        return {}
    last = rows[-1]
    result: Dict[str, Any] = {
        "total_payoff_1": safe_float(last.get("cumulative_payoff_1")),
        "total_payoff_2": safe_float(last.get("cumulative_payoff_2")),
        "pair_total_payoff": safe_float(last.get("cumulative_payoff_1")) + safe_float(last.get("cumulative_payoff_2")),
        "avg_payoff_1": mean(numeric_values(rows, "payoff_1")) if numeric_values(rows, "payoff_1") else 0.0,
        "avg_payoff_2": mean(numeric_values(rows, "payoff_2")) if numeric_values(rows, "payoff_2") else 0.0,
        "avg_pair_payoff": mean(numeric_values(rows, "pair_payoff")) if numeric_values(rows, "pair_payoff") else 0.0,
    }
    for idx in (1, 2):
        for metric in ("mood", "wellbeing", "fatigue", "overall_state", "resources"):
            vals = numeric_values(rows, f"{metric}_{idx}")
            result[f"mean_{metric}_{idx}"] = mean(vals) if vals else ""
            result[f"final_{metric}_{idx}"] = safe_float(last.get(f"{metric}_{idx}"), 0.0)
        neg_vals = numeric_values(rows, f"negative_state_flag_{idx}")
        result[f"negative_state_share_{idx}"] = mean(neg_vals) if neg_vals else 0.0
    third = max(1, len(rows) // 3)
    first = rows[:third]
    last_third = rows[-third:]
    result["payoff_1_first_third"] = sum(numeric_values(first, "payoff_1"))
    result["payoff_1_last_third"] = sum(numeric_values(last_third, "payoff_1"))
    result["payoff_1_delta_last_minus_first_third"] = result["payoff_1_last_third"] - result["payoff_1_first_third"]
    result["overall_state_1_first_third_mean"] = mean(numeric_values(first, "overall_state_1")) if numeric_values(first, "overall_state_1") else ""
    result["overall_state_1_last_third_mean"] = mean(numeric_values(last_third, "overall_state_1")) if numeric_values(last_third, "overall_state_1") else ""
    if result["overall_state_1_first_third_mean"] != "" and result["overall_state_1_last_third_mean"] != "":
        result["overall_state_1_delta_last_minus_first_third"] = result["overall_state_1_last_third_mean"] - result["overall_state_1_first_third_mean"]
    else:
        result["overall_state_1_delta_last_minus_first_third"] = ""
    return result


def game_specific_metrics(rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    if not rows:
        return {}
    game = str(rows[0].get("game_name", "")).lower()
    result: Dict[str, Any] = {}
    if "prison" in game:
        result.update({
            "pd_cooperation_rate_1": mean(numeric_values(rows, "cooperation_flag_1")) if numeric_values(rows, "cooperation_flag_1") else 0.0,
            "pd_cooperation_rate_2": mean(numeric_values(rows, "cooperation_flag_2")) if numeric_values(rows, "cooperation_flag_2") else 0.0,
            "pd_mutual_cooperation_rate": mean(numeric_values(rows, "mutual_cooperation_flag")) if numeric_values(rows, "mutual_cooperation_flag") else 0.0,
            "pd_unilateral_exploitation_rate": mean(numeric_values(rows, "unilateral_exploitation_flag")) if numeric_values(rows, "unilateral_exploitation_flag") else 0.0,
            "pd_mutual_defection_rate": mean(numeric_values(rows, "mutual_defection_flag")) if numeric_values(rows, "mutual_defection_flag") else 0.0,
            "pd_recovery_after_defection_proxy": recovery_after_defection(rows),
        })
    elif "battle" in game:
        flags = [int(safe_float(r.get("agreement_flag"), 0.0)) for r in rows]
        streaks = coordination_streaks(flags)
        opera = sum(int(safe_float(r.get("opera_coordination_flag"), 0.0)) for r in rows)
        fight = sum(int(safe_float(r.get("fight_coordination_flag"), 0.0)) for r in rows)
        coord_total = opera + fight
        result.update({
            "bos_agreement_rate": safe_div(sum(flags), len(flags)),
            "bos_coordination_streak_mean": mean(streaks) if streaks else 0.0,
            "bos_coordination_streak_max": max(streaks) if streaks else 0,
            "bos_coordination_imbalance": safe_div(abs(opera - fight), coord_total),
            "bos_fair_turn_taking_index": 1.0 - safe_div(abs(opera - fight), coord_total),
        })
    elif "ultimatum" in game:
        offers = numeric_values(rows, "offer")
        accepted = numeric_values(rows, "accepted_flag")
        result.update({
            "ug_acceptance_rate": mean(accepted) if accepted else 0.0,
            "ug_mean_offer": mean(offers) if offers else 0.0,
            "ug_offer_std": pstdev(offers) if len(offers) > 1 else 0.0,
            "ug_fair_offer_rate": safe_div(sum(1 for x in offers if 4.0 <= x <= 6.0), len(offers)),
            "ug_proposer_responder_inequality": mean([abs(safe_float(r.get("payoff_1")) - safe_float(r.get("payoff_2"))) for r in rows]) if rows else 0.0,
        })
        for b in ("very_low", "low", "fair", "generous", "very_generous"):
            bucket = [r for r in rows if r.get("offer_bin") == b]
            result[f"ug_acceptance_rate_bin_{b}"] = mean(numeric_values(bucket, "accepted_flag")) if bucket else ""
            result[f"ug_offer_count_bin_{b}"] = len(bucket)
    return result


def action_rate_metric_name(game_name: str) -> str:
    g = game_name.lower()
    if "prison" in g:
        return "cooperation_flag_1"
    if "battle" in g:
        return "agreement_flag"
    if "ultimatum" in g:
        return "fairness_proxy"
    return "pair_payoff"


def compute_adaptation_rows(round_rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    groups = group_rows(round_rows, ["scenario_name", "condition_id", "episode_id"])
    out: List[Dict[str, Any]] = []
    for _, rows in groups.items():
        rows = sorted(rows, key=lambda r: int(safe_float(r.get("round_id"), 0)))
        if not rows:
            continue
        third = max(1, len(rows) // 3)
        first = rows[:third]
        last = rows[-third:]
        metric = action_rate_metric_name(str(rows[0].get("game_name", "")))
        first_metric_vals = numeric_values(first, metric)
        last_metric_vals = numeric_values(last, metric)
        first_metric = mean(first_metric_vals) if first_metric_vals else 0.0
        last_metric = mean(last_metric_vals) if last_metric_vals else 0.0
        first_payoff = sum(numeric_values(first, "payoff_1"))
        last_payoff = sum(numeric_values(last, "payoff_1"))
        out.append({
            "scenario_name": rows[0].get("scenario_name"),
            "condition_id": rows[0].get("condition_id"),
            "condition_label": rows[0].get("condition_label"),
            "game_name": rows[0].get("game_name"),
            "run_profile": rows[0].get("run_profile"),
            "episode_id": rows[0].get("episode_id"),
            "random_seed": rows[0].get("random_seed"),
            "agent_1_type": rows[0].get("agent_1_type"),
            "agent_2_type": rows[0].get("agent_2_type"),
            "fixed_strategy_2": rows[0].get("fixed_strategy_2"),
            "metric_name": metric,
            "first_third_metric": first_metric,
            "last_third_metric": last_metric,
            "delta_metric": last_metric - first_metric,
            "first_third_payoff_1": first_payoff,
            "last_third_payoff_1": last_payoff,
            "delta_payoff_1": last_payoff - first_payoff,
            "simple_adaptation_lag_proxy": first_round_reaching_or_none(rows, metric, target=max(first_metric, last_metric)),
        })
    return out


def first_round_reaching_or_none(rows: Sequence[Dict[str, Any]], metric: str, target: float) -> Any:
    if not rows:
        return ""
    if target <= 0:
        return ""
    for row in rows:
        if safe_float(row.get(metric), 0.0) >= target:
            return row.get("round_id", "")
    return ""


def correlation(xs: Sequence[float], ys: Sequence[float]) -> Any:
    if len(xs) < 2 or len(xs) != len(ys):
        return ""
    mx, my = mean(xs), mean(ys)
    sx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    sy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if sx == 0 or sy == 0:
        return ""
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (sx * sy)


def linear_slope(values: Sequence[float]) -> Any:
    if len(values) < 2:
        return ""
    xs = list(range(1, len(values) + 1))
    mx, my = mean(xs), mean(values)
    denom = sum((x - mx) ** 2 for x in xs)
    if denom == 0:
        return ""
    return sum((x - mx) * (y - my) for x, y in zip(xs, values)) / denom


def compute_collapse_rows(round_rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    groups = group_rows(round_rows, ["scenario_name", "condition_id", "episode_id"])
    out: List[Dict[str, Any]] = []
    for _, rows in groups.items():
        rows = sorted(rows, key=lambda r: int(safe_float(r.get("round_id"), 0)))
        if not rows:
            continue
        base = {
            "scenario_name": rows[0].get("scenario_name"),
            "condition_id": rows[0].get("condition_id"),
            "condition_label": rows[0].get("condition_label"),
            "game_name": rows[0].get("game_name"),
            "run_profile": rows[0].get("run_profile"),
            "episode_id": rows[0].get("episode_id"),
            "random_seed": rows[0].get("random_seed"),
        }
        for idx in (1, 2):
            mood = numeric_values(rows, f"mood_{idx}")
            wellbeing = numeric_values(rows, f"wellbeing_{idx}")
            fatigue = numeric_values(rows, f"fatigue_{idx}")
            overall = numeric_values(rows, f"overall_state_{idx}")
            payoff = numeric_values(rows, f"payoff_{idx}")
            base.update({
                f"agent_{idx}_mood_min": min(mood) if mood else "",
                f"agent_{idx}_mood_max": max(mood) if mood else "",
                f"agent_{idx}_mood_slope": linear_slope(mood) if mood else "",
                f"agent_{idx}_wellbeing_min": min(wellbeing) if wellbeing else "",
                f"agent_{idx}_wellbeing_max": max(wellbeing) if wellbeing else "",
                f"agent_{idx}_fatigue_min": min(fatigue) if fatigue else "",
                f"agent_{idx}_fatigue_max": max(fatigue) if fatigue else "",
                f"agent_{idx}_fatigue_over_0_6_share": safe_div(sum(1 for x in fatigue if x > 0.6), len(fatigue)) if fatigue else "",
                f"agent_{idx}_overall_state_min": min(overall) if overall else "",
                f"agent_{idx}_overall_state_max": max(overall) if overall else "",
                f"agent_{idx}_overall_state_mean": mean(overall) if overall else "",
                f"agent_{idx}_payoff_overall_corr": correlation(payoff, overall) if payoff and overall else "",
            })
        out.append(base)
    return out


def compute_episode_rows(round_rows: Sequence[Dict[str, Any]], episode_infos: Optional[Sequence[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    info_map: Dict[Tuple[str, str], Dict[str, Any]] = {}
    if episode_infos:
        for info in episode_infos:
            info_map[(str(info.get("condition_id")), str(info.get("episode_id")))] = dict(info)
    groups = group_rows(round_rows, ["condition_id", "episode_id"])
    out: List[Dict[str, Any]] = []
    for (condition_id, episode_id), rows in groups.items():
        rows = sorted(rows, key=lambda r: int(safe_float(r.get("round_id"), 0)))
        first = rows[0] if rows else {}
        base = dict(info_map.get((str(condition_id), str(episode_id)), {}))
        base.update({
            "scenario_name": first.get("scenario_name", base.get("scenario_name", "")),
            "condition_id": condition_id,
            "condition_label": first.get("condition_label", base.get("condition_label", "")),
            "game_name": first.get("game_name", base.get("game_name", "")),
            "run_profile": first.get("run_profile", base.get("run_profile", "")),
            "model_mode": first.get("model_mode", base.get("model_mode", "")),
            "episode_id": episode_id,
            "random_seed": first.get("random_seed", base.get("random_seed", "")),
            "rounds": len(rows),
            "agent_1_type": first.get("agent_1_type", base.get("agent_1_type", "")),
            "agent_2_type": first.get("agent_2_type", base.get("agent_2_type", "")),
            "personality_1": first.get("personality_1", base.get("personality_1", "")),
            "personality_2": first.get("personality_2", base.get("personality_2", "")),
            "intensity_1": first.get("intensity_1", base.get("intensity_1", "")),
            "intensity_2": first.get("intensity_2", base.get("intensity_2", "")),
            "fixed_strategy_1": first.get("fixed_strategy_1", base.get("fixed_strategy_1", "")),
            "fixed_strategy_2": first.get("fixed_strategy_2", base.get("fixed_strategy_2", "")),
        })
        base.update(episode_general_metrics(rows))
        base.update(game_specific_metrics(rows))
        out.append(base)
    return out


def compute_summary_by_condition(episode_rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    group_keys = [
        "scenario_name", "game_name", "run_profile", "model_mode", "condition_id", "condition_label",
        "agent_1_type", "agent_2_type", "personality_1", "intensity_1", "fixed_strategy_1",
        "personality_2", "intensity_2", "fixed_strategy_2",
    ]
    groups = group_rows(episode_rows, group_keys)
    metrics = [
        "total_payoff_1", "total_payoff_2", "pair_total_payoff",
        "avg_payoff_1", "avg_payoff_2", "avg_pair_payoff",
        "mean_overall_state_1", "mean_overall_state_2",
        "final_overall_state_1", "final_overall_state_2",
        "negative_state_share_1", "negative_state_share_2",
        "pd_cooperation_rate_1", "pd_cooperation_rate_2", "pd_mutual_cooperation_rate",
        "pd_unilateral_exploitation_rate", "pd_mutual_defection_rate", "pd_recovery_after_defection_proxy",
        "bos_agreement_rate", "bos_coordination_streak_mean", "bos_coordination_streak_max",
        "bos_coordination_imbalance", "bos_fair_turn_taking_index",
        "ug_acceptance_rate", "ug_mean_offer", "ug_offer_std", "ug_fair_offer_rate", "ug_proposer_responder_inequality",
    ]
    out: List[Dict[str, Any]] = []
    for key, rows in groups.items():
        base = {k: v for k, v in zip(group_keys, key)}
        base["episodes_n"] = len(rows)
        for metric in metrics:
            vals = numeric_values(rows, metric)
            if vals:
                base[f"{metric}_mean"] = mean(vals)
                base[f"{metric}_std"] = pstdev(vals) if len(vals) > 1 else 0.0
                base[f"{metric}_median"] = median(vals)
            else:
                base[f"{metric}_mean"] = ""
                base[f"{metric}_std"] = ""
                base[f"{metric}_median"] = ""
        out.append(base)
    return out


def compute_summary_for_paper(summary_rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for row in summary_rows:
        game = str(row.get("game_name", ""))
        if "Prison" in game:
            game_metric_name = "mutual cooperation rate"
            game_metric = row.get("pd_mutual_cooperation_rate_mean", "")
        elif "Battle" in game:
            game_metric_name = "agreement rate"
            game_metric = row.get("bos_agreement_rate_mean", "")
        elif "Ultimatum" in game:
            game_metric_name = "acceptance rate / mean offer"
            game_metric = f"{row.get('ug_acceptance_rate_mean', '')} / {row.get('ug_mean_offer_mean', '')}"
        else:
            game_metric_name = "game-specific metric"
            game_metric = ""
        out.append({
            "scenario_name": row.get("scenario_name", ""),
            "game_name": game,
            "run_profile": row.get("run_profile", ""),
            "model_mode": row.get("model_mode", ""),
            "condition_label": row.get("condition_label", ""),
            "episodes_n": row.get("episodes_n", ""),
            "pair_total_payoff_mean": row.get("pair_total_payoff_mean", ""),
            "agent_1_payoff_mean": row.get("total_payoff_1_mean", ""),
            "agent_2_payoff_mean": row.get("total_payoff_2_mean", ""),
            "agent_1_mean_overall_state": row.get("mean_overall_state_1_mean", ""),
            "agent_2_mean_overall_state": row.get("mean_overall_state_2_mean", ""),
            "agent_1_negative_state_share": row.get("negative_state_share_1_mean", ""),
            "agent_2_negative_state_share": row.get("negative_state_share_2_mean", ""),
            "game_metric_name": game_metric_name,
            "game_metric_value": game_metric,
            "interpretation_guardrail": "Descriptive result only. reported_runs_compat diagnostics reproduce v11 status boundaries; integrated_model results are new architecture outputs.",
        })
    return out


def export_all(output_dir: Path, round_rows: Sequence[Dict[str, Any]], episode_infos: Optional[Sequence[Dict[str, Any]]] = None) -> Dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    episode_rows = compute_episode_rows(round_rows, episode_infos)
    summary_rows = compute_summary_by_condition(episode_rows)
    paper_rows = compute_summary_for_paper(summary_rows)
    adaptation_rows = compute_adaptation_rows(round_rows)
    collapse_rows = compute_collapse_rows(round_rows)

    paths = {
        "round_level": output_dir / "round_level.csv",
        "episode_level": output_dir / "episode_level.csv",
        "summary_by_condition": output_dir / "summary_by_condition.csv",
        "summary_for_paper": output_dir / "summary_for_paper.csv",
        "adaptation_summary": output_dir / "adaptation_summary.csv",
        "collapse_diagnostics": output_dir / "collapse_diagnostics.csv",
    }
    write_csv(paths["round_level"], round_rows)
    write_csv(paths["episode_level"], episode_rows)
    write_csv(paths["summary_by_condition"], summary_rows)
    write_csv(paths["summary_for_paper"], paper_rows)
    write_csv(paths["adaptation_summary"], adaptation_rows)
    write_csv(paths["collapse_diagnostics"], collapse_rows)
    return paths
