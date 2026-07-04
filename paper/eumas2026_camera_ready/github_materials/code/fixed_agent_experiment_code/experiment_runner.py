#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CLI/interactive runner for emotionally bounded-rational agents.

Supports two explicit model modes:
- reported_runs_compat: article-v11-compatible status boundary; adapter/appraisal
  are diagnostic/explanatory in CSV.
- integrated_model: adapter/appraisal are behavior-driving in observe().
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence
import argparse
import hashlib
import json
import os
import subprocess
import sys

from agent_core.model_schema import ModelMode, normalize_model_mode
from experiment_config import (
    FIXED_STRATEGIES,
    GAMES,
    PROFILES,
    SCENARIOS,
    ExperimentConfig,
    make_config,
)
from experiment_metrics import export_all, read_csv, write_json, safe_float
from experiment_plots import build_all_plots
from experiment_utils import load_project_main, run_conditions

SCENARIO_DESCRIPTIONS = {
    "S0": "Smoke / sanity check.",
    "S1": "Ordered cross-type matrix across games.",
    "S2": "Adaptation to fixed strategies: first vs last third deltas.",
    "S3": "Personality × emotional intensity sweep.",
    "S3B": "Extended all-game profile sweep alias.",
    "S4": "Internal state dynamics / collapse diagnostics.",
    "S5": "Legacy exploratory placeholder; not used for v11 claims.",
    "S6": "Legacy exploratory placeholder; not used for v11 claims.",
}


def prompt_choice(title: str, options: Sequence[str], default: Optional[str] = None) -> str:
    print(f"\n{title}")
    for i, opt in enumerate(options, 1):
        marker = " (default)" if default == opt else ""
        print(f"  {i}. {opt}{marker}")
    while True:
        raw = input(f"Выбор [default={default or options[0]}]: ").strip()
        if not raw and default:
            return default
        if not raw:
            return options[0]
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return options[int(raw) - 1]
        if raw in options:
            return raw
        print("Неверный выбор, попробуйте ещё раз.")


def prompt_multi_choice(title: str, options: Sequence[str], default: Optional[Sequence[str]] = None) -> List[str]:
    default = list(default or [])
    print(f"\n{title}")
    for i, opt in enumerate(options, 1):
        marker = " *" if opt in default else ""
        print(f"  {i}. {opt}{marker}")
    print("Введите номера через запятую, 'all' для всех или Enter для значения по умолчанию.")
    while True:
        raw = input("Выбор: ").strip().lower()
        if not raw:
            return default or [options[0]]
        if raw == "all":
            return list(options)
        selected: List[str] = []
        ok = True
        for part in raw.split(","):
            part = part.strip()
            if part.isdigit() and 1 <= int(part) <= len(options):
                selected.append(options[int(part) - 1])
            else:
                ok = False
                break
        if ok and selected:
            return selected
        print("Неверный ввод, пример: 1,3 или all")


def prompt_int(title: str, default: int, min_value: int = 1) -> int:
    while True:
        raw = input(f"{title} [default={default}]: ").strip()
        if not raw:
            return default
        try:
            value = int(raw)
            if value >= min_value:
                return value
        except ValueError:
            pass
        print(f"Введите целое число >= {min_value}.")


def prompt_yes_no(title: str, default: bool = True) -> bool:
    suffix = "Y/n" if default else "y/N"
    raw = input(f"{title} [{suffix}]: ").strip().lower()
    if not raw:
        return default
    return raw in {"y", "yes", "д", "да"}


def build_interactive_config(project_dir: Path) -> ExperimentConfig:
    print("\n" + "=" * 96)
    print("EXPERIMENT RUNNER — architecture-aligned emotionally bounded agents")
    print("=" * 96)
    scenario = prompt_choice("Выберите сценарий", SCENARIOS, default="S0")
    print(f"\n{scenario}: {SCENARIO_DESCRIPTIONS[scenario]}")
    profile = prompt_choice("Выберите профиль запуска", list(PROFILES.keys()), default="quick")
    profile_obj = PROFILES[profile]
    model_mode = prompt_choice("Выберите режим модели", [m.value for m in ModelMode], default=ModelMode.REPORTED_RUNS_COMPAT.value)
    games = prompt_multi_choice("Выберите игры", GAMES, default=GAMES if scenario in {"S1", "S3B"} else ["Prisoners Dilemma"])
    episodes = prompt_int("Количество эпизодов на условие", default=profile_obj.default_episodes)
    rounds = prompt_int("Количество раундов в эпизоде", default=profile_obj.default_rounds)
    seeds_count = prompt_int("Количество seed-ов", default=profile_obj.seed_count)
    base_seed = prompt_int("Базовый random seed", default=20260430, min_value=0)
    output_root = input("Каталог вывода [default=experiments_output]: ").strip() or "experiments_output"
    condition_kwargs: Dict[str, Any] = {}
    if scenario == "S1":
        condition_kwargs["include_fixed_variants"] = prompt_yes_no("Развернуть fixed_strategy во все варианты?", default=False)
    elif scenario == "S2":
        condition_kwargs["fixed_strategies"] = prompt_multi_choice("Какие fixed strategies использовать?", FIXED_STRATEGIES, default=FIXED_STRATEGIES)
    config = make_config(
        scenario=scenario,
        profile=profile,
        games=games,
        episodes=episodes,
        rounds=rounds,
        seeds_count=seeds_count,
        base_seed=base_seed,
        output_root=output_root,
        notes="interactive_run",
        model_mode=model_mode,
        strict=False,
        allow_fallback=False,
        **condition_kwargs,
    )
    print_config_summary(config, project_dir)
    if not prompt_yes_no("Запустить эксперимент с этими параметрами?", default=True):
        print("Запуск отменён пользователем.")
        sys.exit(0)
    return config


def print_config_summary(config: ExperimentConfig, project_dir: Path) -> None:
    print("\n" + "-" * 96)
    print("Сводка запуска")
    print("-" * 96)
    print(f"Project dir: {project_dir}")
    print(f"Scenario: {config.scenario_name} — {SCENARIO_DESCRIPTIONS.get(config.scenario_name, '')}")
    print(f"Profile: {config.run_profile}")
    print(f"Model mode: {config.model_mode}")
    print(f"Strict: {config.strict}; allow_fallback: {config.allow_fallback}")
    print(f"Games: {', '.join(config.games)}")
    print(f"Episodes per condition: {config.episodes_per_condition}")
    print(f"Rounds per episode: {config.rounds_per_episode}")
    print(f"Seed count: {config.seed_count}; seeds: {config.seeds[:5]}{'...' if len(config.seeds) > 5 else ''}")
    print(f"Conditions: {len(config.conditions)}")
    print(f"Estimated total episodes: {len(config.conditions) * len(config.seeds)}")
    print(f"Estimated total round rows: {len(config.conditions) * len(config.seeds) * config.rounds_per_episode}")
    print(f"Output root: {config.output_root}")
    print("Примеры условий:")
    for cond in config.conditions[:5]:
        print(f"  - {cond.condition_id}: {cond.game_name} | {cond.pair_label()}")
    if len(config.conditions) > 5:
        print("  ...")
    print("-" * 96)


def make_run_dir(config: ExperimentConfig) -> Path:
    ts = config.timestamp or datetime.now().strftime("%Y%m%d_%H%M%S")
    config.timestamp = ts
    mode = normalize_model_mode(config.model_mode).value
    run_dir = Path(config.output_root) / f"{ts}_{config.run_profile}_{config.scenario_name}_{mode}"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "plots").mkdir(exist_ok=True)
    return run_dir


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def build_manifest(project_dir: Path, run_dir: Path, config: ExperimentConfig, paths: Dict[str, Path]) -> Dict[str, Any]:
    py_files = sorted([p for p in project_dir.rglob("*.py") if ".venv" not in p.parts and "__pycache__" not in p.parts])
    sha = {str(p.relative_to(project_dir)): sha256_file(p) for p in py_files}
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=str(project_dir), text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        commit = "not-a-git-repository-or-git-unavailable"
    manifest = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "project_dir": str(project_dir),
        "run_dir": str(run_dir),
        "git_commit": commit,
        "code_snapshot_id": hashlib.sha256(json.dumps(sha, sort_keys=True).encode("utf-8")).hexdigest(),
        "model_mode": normalize_model_mode(config.model_mode).value,
        "scenario_name": config.scenario_name,
        "run_profile": config.run_profile,
        "episodes_per_condition": config.episodes_per_condition,
        "rounds_per_episode": config.rounds_per_episode,
        "seed_count": config.seed_count,
        "seeds": config.seeds,
        "strict": config.strict,
        "allow_fallback": config.allow_fallback,
        "artifact_files": {name: str(path.name) for name, path in paths.items()},
        "python_files_sha256": sha,
    }
    write_json(run_dir / "manifest.json", manifest)
    return manifest


def validate_run_outputs(run_dir: Path) -> Dict[str, Any]:
    round_rows = read_csv(run_dir / "round_level.csv")
    episode_rows = read_csv(run_dir / "episode_level.csv")
    required = ["round_level.csv", "episode_level.csv", "summary_by_condition.csv", "summary_for_paper.csv", "adaptation_summary.csv", "collapse_diagnostics.csv", "config.json", "manifest.json", "README.txt", "run_log.txt"]
    missing = [name for name in required if not (run_dir / name).exists()]
    numeric_checks: Dict[str, Any] = {
        "mood_out_of_range": 0,
        "fatigue_out_of_range": 0,
        "nan_or_inf_cells": 0,
        "duplicate_observe_count": 0,
        "fallback_rows": 0,
    }
    for row in round_rows:
        for idx in (1, 2):
            mood = safe_float(row.get(f"mood_{idx}"), 0.0)
            fatigue = safe_float(row.get(f"fatigue_{idx}"), 0.0)
            if mood < -0.500001 or mood > 0.500001:
                numeric_checks["mood_out_of_range"] += 1
            if fatigue < -0.000001 or fatigue > 1.000001:
                numeric_checks["fatigue_out_of_range"] += 1
            numeric_checks["duplicate_observe_count"] += int(safe_float(row.get(f"agent_{idx}_duplicate_update_count"), 0.0))
        if str(row.get("fallback_used", "")).lower() in {"true", "1"}:
            numeric_checks["fallback_rows"] += 1
        for value in row.values():
            if isinstance(value, str) and value.lower() in {"nan", "inf", "-inf"}:
                numeric_checks["nan_or_inf_cells"] += 1
    validation = {
        "run_dir": str(run_dir),
        "missing_files": missing,
        "round_rows": len(round_rows),
        "episode_rows": len(episode_rows),
        **numeric_checks,
        "passed": not missing and all(v == 0 for k, v in numeric_checks.items() if k not in {"fallback_rows"}),
    }
    write_json(run_dir / "validation_report.json", validation)
    lines = ["# Validation report", "", f"Run dir: `{run_dir}`", ""]
    for k, v in validation.items():
        lines.append(f"- **{k}**: {v}")
    (run_dir / "validation_report.md").write_text("\n".join(lines), encoding="utf-8")
    return validation


def write_run_log(run_dir: Path, config: ExperimentConfig, paths: Dict[str, Path], validation: Dict[str, Any]) -> None:
    mode = normalize_model_mode(config.model_mode).value
    if mode == ModelMode.REPORTED_RUNS_COMPAT.value:
        guardrail = "reported_runs_compat: adapter/appraisal columns are diagnostic/explanatory and reproduce the article-v11 status boundary."
    else:
        guardrail = "integrated_model: adapter/appraisal are behavior-driving; results belong to the new architecture and must not be mixed with v11 reported runs."
    lines = [
        "Experiment run log",
        "==================",
        f"scenario_name: {config.scenario_name}",
        f"run_profile: {config.run_profile}",
        f"model_mode: {mode}",
        f"games: {', '.join(config.games)}",
        f"episodes_per_condition: {config.episodes_per_condition}",
        f"rounds_per_episode: {config.rounds_per_episode}",
        f"seed_count: {config.seed_count}",
        f"seeds: {config.seeds}",
        f"conditions: {len(config.conditions)}",
        f"strict: {config.strict}",
        f"allow_fallback: {config.allow_fallback}",
        "",
        "Artifacts:",
    ]
    for name, path in paths.items():
        lines.append(f"- {name}: {path.name}")
    lines.extend([
        "- plots: plots/",
        "- manifest: manifest.json",
        "- validation: validation_report.md/json",
        "",
        "Interpretation guardrail:",
        guardrail,
        "Fixed-strategy semantics are cleanest in PD; BoS/UG fixed-strategy rows are stress tests unless explicitly redesigned.",
        "",
        "Validation summary:",
        json.dumps(validation, ensure_ascii=False, indent=2),
    ])
    (run_dir / "README.txt").write_text("\n".join(lines), encoding="utf-8")
    (run_dir / "run_log.txt").write_text("\n".join(lines), encoding="utf-8")


def run_experiment(config: ExperimentConfig, project_dir: Path, yes: bool = False) -> Path:
    if not yes:
        print_config_summary(config, project_dir)
        if not prompt_yes_no("Подтвердить запуск?", default=True):
            print("Запуск отменён.")
            sys.exit(0)
    main_module = load_project_main(project_dir)
    run_dir = make_run_dir(config)
    config.save(run_dir)
    print(f"\nРезультаты будут сохранены в: {run_dir}")
    round_rows, episode_infos = run_conditions(
        main_module,
        config.conditions,
        run_profile=config.run_profile,
        rounds=config.rounds_per_episode,
        seeds=config.seeds,
        model_mode=config.model_mode,
        strict=config.strict,
        allow_fallback=config.allow_fallback,
        progress=True,
    )
    paths = export_all(run_dir, round_rows, episode_infos)
    print("\nСтрою графики...")
    build_all_plots(run_dir, save_svg=config.save_svg)
    build_manifest(project_dir, run_dir, config, paths)
    write_run_log(run_dir, config, paths, {"pending": True})
    validation = validate_run_outputs(run_dir)
    write_run_log(run_dir, config, paths, validation)
    print("\n" + "=" * 96)
    print("Готово")
    print("=" * 96)
    print(f"Папка результата: {run_dir}")
    for name, path in paths.items():
        print(f"  {name}: {path}")
    print(f"  plots: {run_dir / 'plots'}")
    print(f"  validation: {run_dir / 'validation_report.md'}")
    return run_dir


def parse_games_arg(value: Optional[str], scenario: str) -> List[str]:
    if not value:
        return GAMES if scenario.upper() in {"S1", "S3B"} else ["Prisoners Dilemma"]
    if value.lower() == "all":
        return GAMES
    games: List[str] = []
    for part in value.split(","):
        part = part.strip()
        if not part:
            continue
        matched = None
        for game in GAMES:
            if part.lower() in {game.lower(), game.lower().replace(" ", "_"), game.lower().replace(" ", "-")}:
                matched = game
                break
        games.append(matched or part)
    return games


def build_cli_config(args: argparse.Namespace) -> ExperimentConfig:
    scenario = (args.scenario or "S0").upper()
    profile = (args.profile or "quick").lower()
    games = parse_games_arg(args.games, scenario)
    condition_kwargs: Dict[str, Any] = {}
    if scenario == "S1":
        condition_kwargs["include_fixed_variants"] = bool(args.include_fixed_variants)
    if scenario == "S2":
        condition_kwargs["tested_agents"] = args.tested_agents.split(",") if args.tested_agents else ["emotional_rational", "emotional", "rational"]
        condition_kwargs["fixed_strategies"] = args.fixed_strategies.split(",") if args.fixed_strategies else FIXED_STRATEGIES
    if scenario in {"S3", "S3B"}:
        condition_kwargs["tested_agent"] = args.tested_agent or "emotional_rational"
        condition_kwargs["opponents"] = args.fixed_strategies.split(",") if args.fixed_strategies else FIXED_STRATEGIES
    return make_config(
        scenario=scenario,
        profile=profile,
        games=games,
        episodes=args.episodes,
        rounds=args.rounds,
        seeds_count=args.seeds_count,
        base_seed=args.seed,
        output_root=args.output,
        notes="cli_run",
        save_svg=bool(args.save_svg),
        model_mode=args.model_mode,
        strict=bool(args.strict),
        allow_fallback=bool(args.allow_fallback),
        **condition_kwargs,
    )


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Architecture-aligned experiment runner.", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--project-dir", default=".", help="Directory containing main.py and agent modules.")
    parser.add_argument("--scenario", choices=SCENARIOS, help="Scenario to run: S0-S6.")
    parser.add_argument("--profile", choices=list(PROFILES.keys()), default="quick", help="Run profile.")
    parser.add_argument("--games", default=None, help="Comma-separated game names or 'all'.")
    parser.add_argument("--episodes", type=int, default=None, help="Episodes per condition. Overrides profile default.")
    parser.add_argument("--rounds", type=int, default=None, help="Rounds per episode. Overrides profile default.")
    parser.add_argument("--seeds-count", type=int, default=None, help="Number of independent seeds/episode runs per condition.")
    parser.add_argument("--seed", type=int, default=20260430, help="Base random seed.")
    parser.add_argument("--model-mode", default=ModelMode.REPORTED_RUNS_COMPAT.value, help="reported_runs_compat, integrated_model, or deprecated alias paper_v10_compat.")
    parser.add_argument("--strict", action="store_true", help="Fail immediately on agent/game errors; recommended for paper runs.")
    parser.add_argument("--allow-fallback", action="store_true", help="Allow fallback actions in debug/quick mode. Ignored when --strict is set.")
    parser.add_argument("--output", default="experiments_output", help="Output root directory.")
    parser.add_argument("--include-fixed-variants", action="store_true", help="For S1, expand fixed_strategy cells over all fixed strategies.")
    parser.add_argument("--tested-agents", default=None, help="For S2, comma-separated tested agent types.")
    parser.add_argument("--tested-agent", default=None, help="For S3, agent type for personality×intensity sweep.")
    parser.add_argument("--fixed-strategies", default=None, help="Comma-separated fixed strategies for S2/S3.")
    parser.add_argument("--yes", action="store_true", help="Run without confirmation.")
    parser.add_argument("--save-svg", action="store_true", help="Also save SVG copies of plots.")
    parser.add_argument("--rebuild-plots", default=None, help="Rebuild plots from an existing run directory and exit.")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> None:
    args = parse_args(argv)
    project_dir = Path(args.project_dir).resolve()
    if args.rebuild_plots:
        run_dir = Path(args.rebuild_plots).resolve()
        print(f"Rebuilding plots from CSV in: {run_dir}")
        build_all_plots(run_dir, save_svg=bool(args.save_svg))
        print(f"Done. Plots are in: {run_dir / 'plots'}")
        return
    if args.scenario:
        config = build_cli_config(args)
        run_experiment(config, project_dir, yes=args.yes)
    else:
        config = build_interactive_config(project_dir)
        run_experiment(config, project_dir, yes=True)


if __name__ == "__main__":
    main()
