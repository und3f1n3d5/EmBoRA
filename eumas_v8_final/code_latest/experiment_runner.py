#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Interactive and CLI experiment runner for emotionally bounded-rational agents.
Version 3.0 — reviewed experimental wrapper.

Place this file and helper modules next to the existing project main.py and
agent files, then run:

    python experiment_runner.py

The runner imports the current project code, does not edit existing agent/game
modules, and writes reproducible experiment artifacts to experiments_output/.
"""
from __future__ import annotations

"""
Experiment Runner v3
--------------------

This module provides an interactive and command‑line interface for running
experiments with emotionally bounded‑rational agents.  It orchestrates
scenarios, profiles, seeding, data export and plotting.

Important note on headless environments:  The OpenAI CaaS environment used
for this project automatically monkey‑patches matplotlib via the
`caas_jupyter_tools` package.  This patch instructs matplotlib to log
chart metadata back to a Jupyter server running on localhost:8080.  When
such a server is not available (as in a non‑interactive CLI run) any
attempt to render plots will crash with a `ConnectionRefusedError` as it
tries to contact the Jupyter API.  To avoid this failure we disable the
matplotlib–Jupyter callback by default.

The environment variable ``ENABLE_MATPLOTLIB_JUPYTER_SERVER`` controls this
behaviour.  If it is unset, we set it to ``"false"`` here at module import
time.  Doing so early ensures that when matplotlib or caas_jupyter_tools
initializes, it sees the flag disabled and refrains from contacting the
Jupyter server.  Users who wish to re‑enable logging can explicitly set
``ENABLE_MATPLOTLIB_JUPYTER_SERVER=true`` before invoking this script.
"""

import os

# Disable the caas_jupyter_tools matplotlib server unless explicitly enabled.
if os.environ.get("ENABLE_MATPLOTLIB_JUPYTER_SERVER", "").lower() not in {"true", "1", "yes"}:
    os.environ["ENABLE_MATPLOTLIB_JUPYTER_SERVER"] = "false"

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence
import argparse
import os
import json
import os
import shutil
import sys
import textwrap

from experiment_config import (
    AGENT_TYPES,
    FIXED_STRATEGIES,
    GAMES,
    INTENSITIES,
    PERSONALITIES,
    PROFILES,
    SCENARIOS,
    ExperimentConfig,
    build_conditions,
    make_config,
)
from experiment_metrics import export_all, read_csv, write_json
from experiment_plots import build_all_plots
from experiment_utils import load_project_main, run_conditions


SCENARIO_DESCRIPTIONS = {
    "S0": "Smoke / sanity check: quick import and file-writing test.",
    "S1": "Full matchup matrix across games: homogeneous + cross-type comparisons.",
    "S2": "Adaptation to fixed strategies: first vs last third deltas for H1.",
    "S3": "Personality × Emotional Intensity sweep: 9 cells preserved separately for H3.",
    "S4": "Internal state dynamics / collapse diagnostics: round-level state trajectories.",
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
    print("EXPERIMENT RUNNER v3 — эмоционально-ограниченно-рациональные агенты")
    print("=" * 96)
    print("Код агентов и игр не изменяется: runner импортирует текущий main.py и сохраняет результаты отдельно.")

    scenario = prompt_choice("Выберите сценарий", SCENARIOS, default="S0")
    print(f"\n{scenario}: {SCENARIO_DESCRIPTIONS[scenario]}")
    profile = prompt_choice("Выберите профиль запуска", list(PROFILES.keys()), default="quick")
    profile_obj = PROFILES[profile]

    if scenario in {"S1"}:
        games = prompt_multi_choice("Выберите игры", GAMES, default=GAMES)
    else:
        games = prompt_multi_choice("Выберите игры", GAMES, default=["Prisoners Dilemma"])

    episodes = prompt_int("Количество эпизодов на условие", default=profile_obj.default_episodes)
    rounds = prompt_int("Количество раундов в эпизоде", default=profile_obj.default_rounds)
    base_seed = prompt_int("Базовый random seed", default=20260430, min_value=0)
    output_root = input("Каталог вывода [default=experiments_output]: ").strip() or "experiments_output"

    condition_kwargs: Dict[str, Any] = {}
    if scenario == "S1":
        condition_kwargs["include_fixed_variants"] = prompt_yes_no(
            "Развернуть fixed_strategy во все варианты (always cooperate/defect/tit-for-tat)?", default=False
        )
    elif scenario == "S2":
        tested_agents = prompt_multi_choice(
            "Каких обучаемых/адаптирующихся агентов тестировать?",
            ["emotional_rational", "emotional", "rational"],
            default=["emotional_rational", "emotional", "rational"],
        )
        fixed_strategies = prompt_multi_choice(
            "Какие fixed strategies использовать?",
            FIXED_STRATEGIES,
            default=FIXED_STRATEGIES,
        )
        condition_kwargs["tested_agents"] = tested_agents
        condition_kwargs["fixed_strategies"] = fixed_strategies
    elif scenario == "S3":
        tested_agent = prompt_choice(
            "Какой тип агента прогонять по сетке personality × intensity?",
            ["emotional_rational", "emotional"],
            default="emotional_rational",
        )
        opponents = prompt_multi_choice(
            "Какие fixed-strategy оппоненты использовать?",
            FIXED_STRATEGIES,
            default=FIXED_STRATEGIES,
        )
        condition_kwargs["tested_agent"] = tested_agent
        condition_kwargs["opponents"] = opponents

    config = make_config(
        scenario=scenario,
        profile=profile,
        games=games,
        episodes=episodes,
        rounds=rounds,
        base_seed=base_seed,
        output_root=output_root,
        notes="interactive_run",
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
    print(f"Games: {', '.join(config.games)}")
    print(f"Episodes per condition: {config.episodes}")
    print(f"Rounds per episode: {config.rounds}")
    print(f"Seeds: {config.seeds[:5]}{'...' if len(config.seeds) > 5 else ''}")
    print(f"Conditions: {len(config.conditions)}")
    print(f"Estimated total episodes: {len(config.conditions) * len(config.seeds)}")
    print(f"Estimated total round rows: {len(config.conditions) * len(config.seeds) * config.rounds}")
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
    run_dir = Path(config.output_root) / f"{ts}_{config.run_profile}_{config.scenario_name}"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "plots").mkdir(exist_ok=True)
    return run_dir


def write_run_log(run_dir: Path, config: ExperimentConfig, paths: Dict[str, Path]) -> None:
    lines = [
        "Experiment Runner v3 — run log",
        "=================================",
        f"scenario_name: {config.scenario_name}",
        f"run_profile: {config.run_profile}",
        f"games: {', '.join(config.games)}",
        f"episodes_per_condition: {config.episodes}",
        f"rounds_per_episode: {config.rounds}",
        f"seeds: {config.seeds}",
        f"conditions: {len(config.conditions)}",
        "",
        "Artifacts:",
    ]
    for name, path in paths.items():
        lines.append(f"- {name}: {path.name}")
    lines.extend([
        "- plots: plots/",
        "",
        "Interpretation guardrail:",
        "These outputs are descriptive experimental traces. The wrapper does not claim H2/human-likeness confirmation automatically and does not alter the core agent update rules.",
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
        rounds=config.rounds,
        seeds=config.seeds,
        progress=True,
    )

    paths = export_all(run_dir, round_rows, episode_infos)
    print("\nСтрою графики...")
    build_all_plots(run_dir, save_svg=config.save_svg)
    write_run_log(run_dir, config, paths)

    print("\n" + "=" * 96)
    print("Готово")
    print("=" * 96)
    print(f"Папка результата: {run_dir}")
    for name, path in paths.items():
        print(f"  {name}: {path}")
    print(f"  plots: {run_dir / 'plots'}")
    print("\nВажно: summary_for_paper.csv содержит компактную таблицу для статьи, а round_level.csv — полные трейсы для перепроверки.")
    return run_dir


def parse_games_arg(value: Optional[str], scenario: str) -> List[str]:
    if not value:
        return GAMES if scenario.upper() == "S1" else ["Prisoners Dilemma"]
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
    if scenario == "S3":
        condition_kwargs["tested_agent"] = args.tested_agent or "emotional_rational"
        condition_kwargs["opponents"] = args.fixed_strategies.split(",") if args.fixed_strategies else FIXED_STRATEGIES
    return make_config(
        scenario=scenario,
        profile=profile,
        games=games,
        episodes=args.episodes,
        rounds=args.rounds,
        base_seed=args.seed,
        output_root=args.output,
        notes="cli_run",
        save_svg=bool(args.save_svg),
        **condition_kwargs,
    )


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Experiment Runner v3 for emotional-rational agent games.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--project-dir", default=".", help="Directory containing current main.py and agent modules.")
    parser.add_argument("--scenario", choices=SCENARIOS, help="Scenario to run: S0-S4.")
    parser.add_argument("--profile", choices=list(PROFILES.keys()), default="quick", help="Run profile.")
    parser.add_argument("--games", default=None, help="Comma-separated game names or 'all'.")
    parser.add_argument("--episodes", type=int, default=None, help="Episodes per condition. Overrides profile default.")
    parser.add_argument("--rounds", type=int, default=None, help="Rounds per episode. Overrides profile default.")
    parser.add_argument("--seed", type=int, default=20260430, help="Base random seed.")
    parser.add_argument("--output", default="experiments_output", help="Output root directory.")
    parser.add_argument("--include-fixed-variants", action="store_true", help="For S1, expand fixed_strategy cells over all fixed strategies.")
    parser.add_argument("--tested-agents", default=None, help="For S2, comma-separated tested agent types.")
    parser.add_argument("--tested-agent", default=None, help="For S3, agent type for personality×intensity sweep.")
    parser.add_argument("--fixed-strategies", default=None, help="Comma-separated fixed strategies for S2/S3.")
    parser.add_argument("--yes", action="store_true", help="Run without confirmation.")
    parser.add_argument("--save-svg", action="store_true", help="Also save SVG copies of plots. Disabled by default for speed.")
    parser.add_argument("--rebuild-plots", default=None, help="Rebuild plots from an existing run directory and exit.")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> None:
    """
    Entry point for the experiment runner.  In this containerised environment, matplotlib is
    monkey‑patched by caas_jupyter_tools to report charts back to a Jupyter server at
    localhost:8080.  When running experiments outside of the chat UI the server isn't
    available, which causes any plotting to crash with a ConnectionRefusedError.  To
    preserve backwards compatibility while allowing headless runs, we explicitly
    disable the matplotlib → jupyter callback by setting the
    `ENABLE_MATPLOTLIB_JUPYTER_SERVER` environment variable to ``false`` if it is not
    already defined.  This prevents caas_jupyter_tools from attempting network
    callbacks during plotting.  See `caas_jupyter_tools/__init__.py` for details.
    """

    # Disable the caas_jupyter_tools matplotlib server if not explicitly enabled.
    if not os.environ.get("ENABLE_MATPLOTLIB_JUPYTER_SERVER"):
        os.environ["ENABLE_MATPLOTLIB_JUPYTER_SERVER"] = "false"
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
