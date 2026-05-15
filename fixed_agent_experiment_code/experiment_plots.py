#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Matplotlib plotting utilities for v3 experiments."""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from statistics import mean, pstdev
from typing import Any, Dict, Iterable, List, Sequence, Tuple
import math
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from experiment_metrics import read_csv, safe_float, group_rows, numeric_values


def _save(fig: Any, path: Path, save_svg: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fig.tight_layout()
    except Exception:
        pass
    fig.savefig(path, dpi=120)
    if save_svg:
        fig.savefig(path.with_suffix(".svg"))
    plt.close(fig)


def _shorten(text: Any, max_len: int = 36) -> str:
    s = str(text)
    return s if len(s) <= max_len else s[:max_len - 3] + "..."


def _metric_mean_std(rows: Sequence[Dict[str, Any]], metric: str) -> Tuple[float, float]:
    vals = numeric_values(rows, metric)
    if not vals:
        return 0.0, 0.0
    return mean(vals), (pstdev(vals) if len(vals) > 1 else 0.0)


def plot_summary_bars(summary_rows: Sequence[Dict[str, Any]], output_dir: Path, save_svg: bool = True) -> None:
    if not summary_rows:
        return
    groups = group_rows(summary_rows, ["game_name"])
    for (game_name,), rows in groups.items():
        labels = [_shorten(r.get("condition_label", r.get("condition_id", "")), 26) for r in rows]
        payoff = [safe_float(r.get("pair_total_payoff_mean"), 0.0) for r in rows]
        payoff_err = [safe_float(r.get("pair_total_payoff_std"), 0.0) for r in rows]
        overall = [safe_float(r.get("mean_overall_state_1_mean"), 0.0) for r in rows]
        overall_err = [safe_float(r.get("mean_overall_state_1_std"), 0.0) for r in rows]

        fig, ax = plt.subplots(figsize=(max(10, len(labels) * 0.45), 6))
        ax.bar(range(len(labels)), payoff, yerr=payoff_err if any(payoff_err) else None, capsize=3)
        ax.set_title(f"Pair payoff by condition — {game_name}")
        ax.set_ylabel("pair total payoff, mean ± std")
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, rotation=70, ha="right")
        ax.grid(axis="y", alpha=0.3)
        _save(fig, output_dir / f"payoff_bar_{str(game_name).replace(' ', '_')}.png", save_svg)

        fig, ax = plt.subplots(figsize=(max(10, len(labels) * 0.45), 6))
        ax.bar(range(len(labels)), overall, yerr=overall_err if any(overall_err) else None, capsize=3)
        ax.set_title(f"Agent 1 mean overall state — {game_name}")
        ax.set_ylabel("mean overall_state, mean ± std")
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, rotation=70, ha="right")
        ax.grid(axis="y", alpha=0.3)
        _save(fig, output_dir / f"overall_state_bar_{str(game_name).replace(' ', '_')}.png", save_svg)


def plot_game_specific_bars(summary_rows: Sequence[Dict[str, Any]], output_dir: Path, save_svg: bool = True) -> None:
    if not summary_rows:
        return
    metric_candidates = {
        "Prisoners Dilemma": ["pd_mutual_cooperation_rate_mean", "pd_unilateral_exploitation_rate_mean", "pd_mutual_defection_rate_mean"],
        "Battle of Sexes": ["bos_agreement_rate_mean", "bos_coordination_imbalance_mean", "bos_fair_turn_taking_index_mean"],
        "Ultimatum Game": ["ug_acceptance_rate_mean", "ug_mean_offer_mean", "ug_fair_offer_rate_mean"],
    }
    for game, metrics in metric_candidates.items():
        rows = [r for r in summary_rows if r.get("game_name") == game]
        if not rows:
            continue
        labels = [_shorten(r.get("condition_label", r.get("condition_id", "")), 24) for r in rows]
        for metric in metrics:
            vals = [safe_float(r.get(metric), 0.0) for r in rows]
            if not any(vals):
                continue
            fig, ax = plt.subplots(figsize=(max(10, len(labels) * 0.45), 6))
            ax.bar(range(len(labels)), vals)
            ax.set_title(f"{metric.replace('_mean', '')} — {game}")
            ax.set_ylabel(metric.replace("_mean", ""))
            ax.set_xticks(range(len(labels)))
            ax.set_xticklabels(labels, rotation=70, ha="right")
            ax.grid(axis="y", alpha=0.3)
            _save(fig, output_dir / f"game_metric_{game.replace(' ', '_')}_{metric.replace('_mean', '')}.png", save_svg)


def plot_episode_boxplots(episode_rows: Sequence[Dict[str, Any]], output_dir: Path, save_svg: bool = True) -> None:
    if not episode_rows:
        return
    groups = group_rows(episode_rows, ["game_name"])
    for (game_name,), rows in groups.items():
        conds = sorted(set(str(r.get("condition_label", r.get("condition_id", ""))) for r in rows))
        for metric, title in [
            ("pair_total_payoff", "Pair total payoff"),
            ("mean_overall_state_1", "Agent 1 mean overall state"),
            ("negative_state_share_1", "Agent 1 negative overall-state share"),
        ]:
            data = []
            labels = []
            for cond in conds:
                vals = [safe_float(r.get(metric), 0.0) for r in rows if str(r.get("condition_label", r.get("condition_id", ""))) == cond]
                if vals:
                    data.append(vals)
                    labels.append(_shorten(cond, 26))
            if not data:
                continue
            fig, ax = plt.subplots(figsize=(max(10, len(labels) * 0.55), 6))
            ax.boxplot(data, showfliers=False)
            ax.set_title(f"{title} — {game_name}")
            ax.set_ylabel(metric)
            ax.set_xticks(range(1, len(labels) + 1))
            ax.set_xticklabels(labels, rotation=70, ha="right")
            ax.grid(axis="y", alpha=0.3)
            _save(fig, output_dir / f"boxplot_{str(game_name).replace(' ', '_')}_{metric}.png", save_svg)


def plot_mean_timeseries(round_rows: Sequence[Dict[str, Any]], output_dir: Path, save_svg: bool = True) -> None:
    if not round_rows:
        return
    groups = group_rows(round_rows, ["game_name", "condition_label"])
    for (game_name, condition_label), rows in groups.items():
        by_round = group_rows(rows, ["round_id"])
        round_ids = sorted([int(safe_float(k[0], 0.0)) for k in by_round.keys()])
        if not round_ids:
            continue
        for idx in (1, 2):
            fig, ax = plt.subplots(figsize=(10, 6))
            for metric in ("mood", "wellbeing", "fatigue", "overall_state"):
                ys = []
                for rid in round_ids:
                    vals = numeric_values(by_round.get((str(rid),), []) or by_round.get((rid,), []), f"{metric}_{idx}")
                    # CSV read gives string keys; in-memory may keep int keys.
                    if not vals:
                        bucket = [r for r in rows if int(safe_float(r.get("round_id"), 0)) == rid]
                        vals = numeric_values(bucket, f"{metric}_{idx}")
                    ys.append(mean(vals) if vals else 0.0)
                ax.plot(round_ids, ys, label=metric)
            ax.set_title(f"Mean internal dynamics — Agent {idx}\n{game_name} | {_shorten(condition_label, 70)}")
            ax.set_xlabel("round")
            ax.set_ylabel("state value")
            ax.grid(True, alpha=0.3)
            ax.legend()
            safe_name = f"timeseries_{str(game_name).replace(' ', '_')}_{str(condition_label).replace('/', '_').replace(':', '_')}_agent{idx}"
            _save(fig, output_dir / f"{safe_name[:140]}.png", save_svg)


def plot_cumulative_payoff(round_rows: Sequence[Dict[str, Any]], output_dir: Path, save_svg: bool = True) -> None:
    if not round_rows:
        return
    groups = group_rows(round_rows, ["game_name", "condition_label"])
    for (game_name, condition_label), rows in groups.items():
        round_ids = sorted(set(int(safe_float(r.get("round_id"), 0)) for r in rows))
        fig, ax = plt.subplots(figsize=(10, 6))
        for idx in (1, 2):
            ys = []
            for rid in round_ids:
                bucket = [r for r in rows if int(safe_float(r.get("round_id"), 0)) == rid]
                vals = numeric_values(bucket, f"cumulative_payoff_{idx}")
                ys.append(mean(vals) if vals else 0.0)
            ax.plot(round_ids, ys, label=f"Agent {idx}")
        ax.set_title(f"Mean cumulative payoff\n{game_name} | {_shorten(condition_label, 70)}")
        ax.set_xlabel("round")
        ax.set_ylabel("cumulative payoff")
        ax.grid(True, alpha=0.3)
        ax.legend()
        safe_name = f"cumulative_payoff_{str(game_name).replace(' ', '_')}_{str(condition_label).replace('/', '_').replace(':', '_')}"
        _save(fig, output_dir / f"{safe_name[:140]}.png", save_svg)


def plot_adaptation(adaptation_rows: Sequence[Dict[str, Any]], output_dir: Path, save_svg: bool = True) -> None:
    if not adaptation_rows:
        return
    groups = group_rows(adaptation_rows, ["game_name", "agent_1_type", "fixed_strategy_2", "metric_name"])
    labels = []
    first_vals = []
    last_vals = []
    for (game, a1, fs, metric), rows in groups.items():
        labels.append(_shorten(f"{game}|{a1}|{fs}|{metric}", 35))
        first_vals.append(mean(numeric_values(rows, "first_third_metric")) if numeric_values(rows, "first_third_metric") else 0.0)
        last_vals.append(mean(numeric_values(rows, "last_third_metric")) if numeric_values(rows, "last_third_metric") else 0.0)
    if not labels:
        return
    x = list(range(len(labels)))
    width = 0.38
    fig, ax = plt.subplots(figsize=(max(10, len(labels) * 0.55), 6))
    ax.bar([i - width / 2 for i in x], first_vals, width=width, label="first third")
    ax.bar([i + width / 2 for i in x], last_vals, width=width, label="last third")
    ax.set_title("Adaptation: first vs last third")
    ax.set_ylabel("game-specific action metric")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=70, ha="right")
    ax.grid(axis="y", alpha=0.3)
    ax.legend()
    _save(fig, output_dir / "adaptation_first_vs_last.png", save_svg)


def plot_s3_heatmap(summary_rows: Sequence[Dict[str, Any]], output_dir: Path, save_svg: bool = True) -> None:
    rows = [r for r in summary_rows if r.get("scenario_name") == "S3"]
    if not rows:
        return
    personalities = ["optimistic", "neutral", "pessimistic"]
    intensities = ["low", "neutral", "high"]
    games = sorted(set(r.get("game_name", "") for r in rows))
    for game in games:
        game_rows = [r for r in rows if r.get("game_name") == game]
        matrix = []
        for p in personalities:
            row_vals = []
            for inten in intensities:
                vals = [safe_float(r.get("pair_total_payoff_mean"), 0.0) for r in game_rows if r.get("personality_1") == p and r.get("intensity_1") == inten]
                row_vals.append(mean(vals) if vals else 0.0)
            matrix.append(row_vals)
        fig, ax = plt.subplots(figsize=(7, 5))
        im = ax.imshow(matrix, aspect="auto")
        ax.set_title(f"S3 service heatmap: pair payoff — {game}")
        ax.set_xticks(range(len(intensities)))
        ax.set_xticklabels(intensities)
        ax.set_yticks(range(len(personalities)))
        ax.set_yticklabels(personalities)
        for i in range(len(personalities)):
            for j in range(len(intensities)):
                ax.text(j, i, f"{matrix[i][j]:.1f}", ha="center", va="center")
        fig.colorbar(im, ax=ax, label="pair total payoff")
        _save(fig, output_dir / f"S3_heatmap_pair_payoff_{str(game).replace(' ', '_')}.png", save_svg)



def _scenario_from_run_dir(run_dir: Path) -> str:
    try:
        with (Path(run_dir) / "config.json").open("r", encoding="utf-8") as f:
            data = json.load(f)
        return str(data.get("scenario_name", "")).upper()
    except Exception:
        return ""

def plot_rolling_action_metric(round_rows: Sequence[Dict[str, Any]], output_dir: Path, save_svg: bool = False) -> None:
    """Compact S2 adaptation plot: rolling game-specific metric by condition."""
    if not round_rows:
        return
    groups = group_rows(round_rows, ["game_name", "condition_label"])
    for (game_name, condition_label), rows in groups.items():
        rows = sorted(rows, key=lambda r: int(safe_float(r.get("round_id"), 0)))
        if not rows:
            continue
        g = str(game_name).lower()
        if "prison" in g:
            metric = "cooperation_flag_1"
        elif "battle" in g:
            metric = "agreement_flag"
        elif "ultimatum" in g:
            metric = "fairness_proxy"
        else:
            metric = "pair_payoff"
        window = max(3, min(10, len(rows) // 5 or 3))
        xs, ys = [], []
        for i, row in enumerate(rows):
            bucket = rows[max(0, i - window + 1): i + 1]
            vals = numeric_values(bucket, metric)
            xs.append(int(safe_float(row.get("round_id"), i + 1)))
            ys.append(mean(vals) if vals else 0.0)
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(xs, ys, label=f"rolling {metric}")
        ax.set_title(f"Rolling adaptation metric\n{game_name} | {_shorten(condition_label, 70)}")
        ax.set_xlabel("round")
        ax.set_ylabel(metric)
        ax.grid(True, alpha=0.3)
        ax.legend()
        safe_name = f"rolling_metric_{str(game_name).replace(' ', '_')}_{str(condition_label).replace('/', '_').replace(':', '_')}"
        _save(fig, output_dir / f"{safe_name[:140]}.png", save_svg)

def plot_values_appraisal_timeseries(round_rows: Sequence[Dict[str, Any]], output_dir: Path, save_svg: bool = False) -> None:
    """S4 diagnostic values/appraisal trajectories from post-hoc adapter fields."""
    groups = group_rows(round_rows, ["game_name", "condition_label"])
    for (game_name, condition_label), rows in groups.items():
        round_ids = sorted(set(int(safe_float(r.get("round_id"), 0)) for r in rows))
        if not round_ids:
            continue
        for idx in (1, 2):
            fig, ax = plt.subplots(figsize=(10, 6))
            for metric in ("q_material", "q_fairness", "q_relationship", "q_safety"):
                ys=[]
                for rid in round_ids:
                    bucket=[r for r in rows if int(safe_float(r.get("round_id"),0))==rid]
                    vals=numeric_values(bucket, f"agent_{idx}_{metric}")
                    ys.append(mean(vals) if vals else 0.0)
                ax.plot(round_ids, ys, label=metric.replace('q_',''))
            ax.set_title(f"Post-hoc event values — Agent {idx}\n{game_name} | {_shorten(condition_label, 70)}")
            ax.set_xlabel("round")
            ax.set_ylabel("event value [0, 1]")
            ax.grid(True, alpha=0.3)
            ax.legend()
            safe_name=f"event_values_{str(game_name).replace(' ', '_')}_{str(condition_label).replace('/', '_').replace(':', '_')}_agent{idx}"
            _save(fig, output_dir / f"{safe_name[:140]}.png", save_svg)


def build_all_plots(run_dir: Path, save_svg: bool = False) -> None:
    run_dir = Path(run_dir)
    plots_dir = run_dir / "plots"
    round_rows = read_csv(run_dir / "round_level.csv")
    episode_rows = read_csv(run_dir / "episode_level.csv")
    summary_rows = read_csv(run_dir / "summary_by_condition.csv")
    adaptation_rows = read_csv(run_dir / "adaptation_summary.csv")

    scenario = _scenario_from_run_dir(run_dir)

    # Compact article-ready summaries for all scenarios.
    plot_summary_bars(summary_rows, plots_dir, save_svg)
    plot_game_specific_bars(summary_rows, plots_dir, save_svg)
    plot_episode_boxplots(episode_rows, plots_dir, save_svg)

    # Detailed time-series are essential for S4 and useful for S0 smoke runs;
    # generating them for the full S1 matrix creates hundreds of figures.
    if scenario in {"S0", "S4"}:
        plot_mean_timeseries(round_rows, plots_dir, save_svg)
        plot_cumulative_payoff(round_rows, plots_dir, save_svg)
        plot_values_appraisal_timeseries(round_rows, plots_dir, save_svg)
    elif scenario == "S2":
        plot_adaptation(adaptation_rows, plots_dir, save_svg)
        plot_rolling_action_metric(round_rows, plots_dir, save_svg)
        plot_cumulative_payoff(round_rows, plots_dir, save_svg)
    elif scenario == "S3":
        plot_s3_heatmap(summary_rows, plots_dir, save_svg)
    else:
        # S1: matrix-level bars/boxplots only by default.
        pass
