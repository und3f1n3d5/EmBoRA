#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Runtime utilities for v3 experiment wrapper.

The helpers here load the existing project `main.py`, create agents via the
public factory provided there, run episodes, and collect round-level traces.
They do not edit or monkey-patch the source files on disk.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
import importlib
import importlib.util
import math
import os
import random
import re
import sys
import traceback

try:
    import numpy as np
except Exception:  # pragma: no cover
    np = None  # type: ignore

try:
    import torch
except Exception:  # pragma: no cover
    torch = None  # type: ignore

from experiment_config import AgentSpec, Condition
from diagnostic_adapter import compute_event_values, compute_appraisal, flatten_diagnostics


_MAIN_CACHE: Dict[Path, Any] = {}


def set_global_seed(seed: int) -> None:
    random.seed(seed)
    if np is not None:
        np.random.seed(seed)
    if torch is not None:
        try:
            torch.manual_seed(seed)
            if hasattr(torch, "cuda") and torch.cuda.is_available():
                torch.cuda.manual_seed_all(seed)
        except Exception:
            pass


def find_main_file(project_dir: Path) -> Path:
    project_dir = Path(project_dir).resolve()
    candidates = [project_dir / "main.py"]
    candidates.extend(sorted(project_dir.glob("main (*.py)")))
    candidates.extend(sorted(project_dir.glob("main*.py")))
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate
    raise FileNotFoundError(f"Cannot find main.py near {project_dir}")


def load_project_main(project_dir: Path) -> Any:
    project_dir = Path(project_dir).resolve()
    if project_dir in _MAIN_CACHE:
        return _MAIN_CACHE[project_dir]

    main_path = find_main_file(project_dir)
    if str(project_dir) not in sys.path:
        sys.path.insert(0, str(project_dir))

    module_name = f"agent_project_main_{abs(hash(str(main_path))) & 0xffffffff:x}"
    spec = importlib.util.spec_from_file_location(module_name, main_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not create import spec for {main_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    _MAIN_CACHE[project_dir] = module
    return module


def make_game(main_module: Any, game_name: str) -> Any:
    game_name_norm = game_name.strip().lower()
    if game_name_norm in {"prisoners dilemma", "prisoner's dilemma", "prisoner’s dilemma", "pd", "ipd"}:
        return main_module.PrisonersDilemmaGame()
    if game_name_norm in {"battle of sexes", "battle of the sexes", "bos"}:
        return main_module.BattleOfSexesGame()
    if game_name_norm in {"ultimatum game", "ultimatum", "ug"}:
        return main_module.UltimatumGame()
    raise ValueError(f"Unknown game name: {game_name}")


def _log_level_silent(main_module: Any) -> int:
    return int(getattr(getattr(main_module, "LogLevel", object), "SILENT", 50))


def create_agent(main_module: Any, spec: AgentSpec, name: str, game_actions: List[Dict[str, Any]]) -> Any:
    agent = main_module.create_agent(
        agent_type=spec.agent_type,
        name=name,
        personality=spec.personality,
        intensity=spec.intensity,
        strategy=spec.fixed_strategy,
        log_level=_log_level_silent(main_module),
        game_actions=game_actions,
    )
    if agent is None:
        raise RuntimeError(f"main.create_agent returned None for {spec}")
    try:
        agent.name = name
    except Exception:
        pass
    return agent


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        result = float(value)
        if math.isnan(result) or math.isinf(result):
            return default
        return result
    except Exception:
        return default


def get_state(agent: Any) -> Optional[Any]:
    for attr in ("state", "agent_state"):
        state = getattr(agent, attr, None)
        if state is not None:
            return state
    return None


def get_state_metric(agent: Any, metric: str, default: float = 0.0) -> float:
    state = get_state(agent)
    if state is None:
        return default
    if metric == "overall_state":
        if hasattr(state, "calculate_overall_state"):
            return safe_float(state.calculate_overall_state(), default)
        return safe_float(getattr(state, "wellbeing", 0.0), 0.0) + safe_float(getattr(state, "mood", 0.0), 0.0) - safe_float(getattr(state, "fatigue", 0.0), 0.0)
    return safe_float(getattr(state, metric, default), default)


def module_metric(module: Any, *names: str) -> Optional[float]:
    if module is None:
        return None
    for name in names:
        if hasattr(module, name):
            value = getattr(module, name)
            if value is not None:
                return safe_float(value, 0.0)
    return None


def module_buffer_size(module: Any) -> int:
    if module is None:
        return 0
    for name in ("replay_buffer", "memory", "buffer"):
        value = getattr(module, name, None)
        if value is not None:
            try:
                return int(len(value))
            except Exception:
                return 0
    return 0


def count_forced_by_emotion(agent: Any) -> int:
    count = 0
    for module_name in ("rational_module", "dqn_module"):
        module = getattr(agent, module_name, None)
        buffer = getattr(module, "replay_buffer", None)
        if isinstance(buffer, list):
            for item in buffer:
                if isinstance(item, dict) and bool(item.get("forced_by_emotion", False)):
                    count += 1
    return count


def learning_metrics(agent: Any, prefix: str) -> Dict[str, Any]:
    em = getattr(agent, "emotional_module", None)
    rm = getattr(agent, "rational_module", None)
    dqn = getattr(agent, "dqn_module", None)
    state = get_state(agent)
    return {
        f"{prefix}_em_epsilon": module_metric(em, "epsilon"),
        f"{prefix}_rm_epsilon": module_metric(rm, "epsilon"),
        f"{prefix}_dqn_epsilon": module_metric(dqn, "epsilon"),
        f"{prefix}_em_loss": module_metric(em, "last_loss", "loss"),
        f"{prefix}_rm_loss": module_metric(rm, "last_loss", "loss"),
        f"{prefix}_dqn_loss": module_metric(dqn, "last_loss", "loss"),
        f"{prefix}_em_buffer_size": module_buffer_size(em),
        f"{prefix}_rm_buffer_size": module_buffer_size(rm),
        f"{prefix}_dqn_buffer_size": module_buffer_size(dqn),
        f"{prefix}_refocus_count": int(getattr(state, "refocus_count", 0)) if state is not None else 0,
        f"{prefix}_total_refocus_count": int(getattr(state, "total_refocus_count", 0)) if state is not None else 0,
        f"{prefix}_forced_by_emotion_count": count_forced_by_emotion(agent),
    }


def parse_action_name(action: Any) -> str:
    text = str(action or "").strip().lower()
    if "(" in text:
        text = text.split("(", 1)[0]
    return text.strip()


def parse_offer(action: Any) -> Optional[float]:
    text = str(action or "")
    # action may look like offer(offer=5.50) or offer(amount=5)
    match = re.search(r"(?:offer|amount)\s*=\s*([-+]?\d+(?:\.\d+)?)", text, flags=re.I)
    if match:
        return safe_float(match.group(1), 0.0)
    if parse_action_name(text) == "offer":
        return 5.0
    return None


def offer_bin(offer: Optional[float]) -> str:
    if offer is None:
        return "none"
    if offer < 2.5:
        return "very_low"
    if offer < 4.0:
        return "low"
    if offer <= 6.0:
        return "fair"
    if offer <= 8.0:
        return "generous"
    return "very_generous"


def fallback_action(game_name: str, agent_index: int) -> str:
    game = game_name.lower()
    if "ultimatum" in game:
        return "offer(offer=5.00)" if agent_index == 1 else "accept"
    if "battle" in game:
        return "opera" if agent_index == 1 else "fight"
    return "cooperate"


def add_game_specific_round_features(row: Dict[str, Any]) -> None:
    game = str(row.get("game_name", "")).lower()
    a1 = parse_action_name(row.get("action_1"))
    a2 = parse_action_name(row.get("action_2"))
    row["cooperation_flag_1"] = 1 if "cooperate" in a1 else 0
    row["cooperation_flag_2"] = 1 if "cooperate" in a2 else 0
    row["mutual_cooperation_flag"] = 1 if row["cooperation_flag_1"] and row["cooperation_flag_2"] else 0
    row["mutual_defection_flag"] = 1 if "defect" in a1 and "defect" in a2 else 0
    row["unilateral_exploitation_flag"] = 1 if (("defect" in a1 and "cooperate" in a2) or ("cooperate" in a1 and "defect" in a2)) else 0

    row["agreement_flag"] = 1 if a1 == a2 and a1 in {"opera", "fight"} else 0
    row["opera_coordination_flag"] = 1 if a1 == "opera" and a2 == "opera" else 0
    row["fight_coordination_flag"] = 1 if a1 == "fight" and a2 == "fight" else 0

    offer = parse_offer(row.get("action_1"))
    row["offer"] = offer if offer is not None else ""
    row["offer_bin"] = offer_bin(offer)
    row["accepted_flag"] = 1 if "accept" in a2 else 0
    row["fairness_proxy"] = 1.0 - min(abs((offer if offer is not None else 5.0) - 5.0) / 5.0, 1.0) if "ultimatum" in game else ""


def build_round_row(
    *,
    condition: Condition,
    run_profile: str,
    episode_id: int,
    round_id: int,
    seed: int,
    action_1: str,
    action_2: str,
    payoff_1: float,
    payoff_2: float,
    cumulative_payoff_1: float,
    cumulative_payoff_2: float,
    agent_1: Any,
    agent_2: Any,
    turn_result_1: Optional[Dict[str, Any]] = None,
    turn_result_2: Optional[Dict[str, Any]] = None,
    prev_values_1: Optional[Dict[str, float]] = None,
    prev_values_2: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    row: Dict[str, Any] = {
        "scenario_name": condition.scenario_name,
        "condition_id": condition.condition_id,
        "condition_label": condition.pair_label(),
        "game_name": condition.game_name,
        "run_profile": run_profile,
        "episode_id": episode_id,
        "round_id": round_id,
        "random_seed": seed,
        "agent_1_type": condition.agent_1.agent_type,
        "agent_2_type": condition.agent_2.agent_type,
        "personality_1": condition.agent_1.personality,
        "personality_2": condition.agent_2.personality,
        "intensity_1": condition.agent_1.intensity,
        "intensity_2": condition.agent_2.intensity,
        "fixed_strategy_1": condition.agent_1.fixed_strategy or "",
        "fixed_strategy_2": condition.agent_2.fixed_strategy or "",
        "action_1": str(action_1),
        "action_2": str(action_2),
        "payoff_1": safe_float(payoff_1),
        "payoff_2": safe_float(payoff_2),
        "pair_payoff": safe_float(payoff_1) + safe_float(payoff_2),
        "cumulative_payoff_1": safe_float(cumulative_payoff_1),
        "cumulative_payoff_2": safe_float(cumulative_payoff_2),
    }
    for idx, agent in ((1, agent_1), (2, agent_2)):
        row[f"mood_{idx}"] = get_state_metric(agent, "mood")
        row[f"wellbeing_{idx}"] = get_state_metric(agent, "wellbeing")
        row[f"fatigue_{idx}"] = get_state_metric(agent, "fatigue")
        row[f"resources_{idx}"] = get_state_metric(agent, "resources", 0.0)
        row[f"overall_state_{idx}"] = get_state_metric(agent, "overall_state")
        row[f"negative_state_flag_{idx}"] = 1 if row[f"overall_state_{idx}"] < 0 else 0
        row.update(learning_metrics(agent, f"agent_{idx}"))
    if isinstance(turn_result_1, dict):
        for k in ("emotional_intensity", "em_intensity", "action_type"):
            if k in turn_result_1:
                row[f"agent_1_{k}"] = turn_result_1[k]
    if isinstance(turn_result_2, dict):
        for k in ("emotional_intensity", "em_intensity", "action_type"):
            if k in turn_result_2:
                row[f"agent_2_{k}"] = turn_result_2[k]

    # Post-hoc subjective event values and appraisal diagnostics. These values
    # are computed for logging/analysis only and do not affect agent behavior.
    try:
        q1 = compute_event_values(condition.game_name, 1, action_1, action_2, payoff_1, payoff_2)
        q2 = compute_event_values(condition.game_name, 2, action_1, action_2, payoff_1, payoff_2)
        app1 = compute_appraisal(prev_values_1, q1)
        app2 = compute_appraisal(prev_values_2, q2)
        row.update(flatten_diagnostics("agent_1", q1, app1))
        row.update(flatten_diagnostics("agent_2", q2, app2))
        # Regulation diagnostics if emotional action is reported by an agent.
        for idx, turn_result in ((1, turn_result_1), (2, turn_result_2)):
            if isinstance(turn_result, dict):
                em_action = str(turn_result.get("em_action", turn_result.get("emotional_action", "")))
                final_action = str(row.get(f"action_{idx}", ""))
                em_intensity = safe_float(turn_result.get("em_intensity", turn_result.get("emotional_intensity", 0.0)), 0.0)
                suppressed = 1 if em_action and em_action != "" and em_action != final_action else 0
                row[f"agent_{idx}_emotional_action"] = em_action
                row[f"agent_{idx}_final_action"] = final_action
                row[f"agent_{idx}_suppressed"] = suppressed
                row[f"agent_{idx}_suppression_cost_proxy"] = abs(em_intensity) * suppressed
    except Exception as exc:
        row["diagnostic_adapter_error"] = str(exc)
    add_game_specific_round_features(row)
    return row


def run_episode(main_module: Any, condition: Condition, *, run_profile: str, episode_id: int,
                rounds: int, seed: int) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    set_global_seed(seed)
    game = make_game(main_module, condition.game_name)
    game_actions = main_module.get_game_actions_for_game(game)
    agent_1 = create_agent(main_module, condition.agent_1, "Agent_1", game_actions)
    agent_2 = create_agent(main_module, condition.agent_2, "Agent_2", game_actions)

    last_action_1: Optional[str] = None
    last_action_2: Optional[str] = None
    rows: List[Dict[str, Any]] = []
    errors: List[str] = []
    prev_event_values_1: Optional[Dict[str, float]] = None
    prev_event_values_2: Optional[Dict[str, float]] = None

    for round_id in range(1, int(rounds) + 1):
        game_state_1 = game.get_game_state(0)
        game_state_2 = game.get_game_state(1)
        try:
            setattr(game_state_1, "opponent_last_action", last_action_2)
            setattr(game_state_2, "opponent_last_action", last_action_1)
        except Exception:
            pass

        try:
            main_module.update_agent_game_state(agent_1, game_state_1)
            main_module.update_agent_game_state(agent_2, game_state_2)
        except Exception as exc:
            errors.append(f"round {round_id}: update_game_state failed: {exc}")

        try:
            action_1, result_1 = main_module.execute_agent_turn(agent_1, round_id, game_state_1)
        except Exception as exc:
            action_1 = fallback_action(condition.game_name, 1)
            result_1 = {"turn": round_id, "action": action_1, "error": str(exc)}
            errors.append(f"round {round_id}: agent_1 failed: {exc}")

        try:
            action_2, result_2 = main_module.execute_agent_turn(agent_2, round_id, game_state_2)
        except Exception as exc:
            action_2 = fallback_action(condition.game_name, 2)
            result_2 = {"turn": round_id, "action": action_2, "error": str(exc)}
            errors.append(f"round {round_id}: agent_2 failed: {exc}")

        try:
            payoff_1, payoff_2 = game.execute_round(str(action_1), str(action_2))
        except Exception as exc:
            # Last-resort fallback actions should be legal for all current games.
            errors.append(f"round {round_id}: game.execute_round failed for ({action_1}, {action_2}): {exc}")
            action_1 = fallback_action(condition.game_name, 1)
            action_2 = fallback_action(condition.game_name, 2)
            payoff_1, payoff_2 = game.execute_round(str(action_1), str(action_2))

        try:
            if hasattr(agent_1, "update_from_game"):
                gr1 = main_module.GameResult(action=str(action_1), payoff=float(payoff_1), game_state=game.current_state.copy())
                agent_1.update_from_game(gr1)
            if hasattr(agent_2, "update_from_game"):
                gr2 = main_module.GameResult(action=str(action_2), payoff=float(payoff_2), game_state=game.current_state.copy())
                agent_2.update_from_game(gr2)
        except Exception as exc:
            errors.append(f"round {round_id}: update_from_game failed: {exc}")

        row = build_round_row(
            condition=condition,
            run_profile=run_profile,
            episode_id=episode_id,
            round_id=round_id,
            seed=seed,
            action_1=str(action_1),
            action_2=str(action_2),
            payoff_1=float(payoff_1),
            payoff_2=float(payoff_2),
            cumulative_payoff_1=float(game.payoffs[0]),
            cumulative_payoff_2=float(game.payoffs[1]),
            agent_1=agent_1,
            agent_2=agent_2,
            turn_result_1=result_1 if isinstance(result_1, dict) else {},
            turn_result_2=result_2 if isinstance(result_2, dict) else {},
            prev_values_1=prev_event_values_1,
            prev_values_2=prev_event_values_2,
        )
        rows.append(row)
        prev_event_values_1 = {k.replace("agent_1_q_", ""): safe_float(v, 0.0) for k, v in row.items() if k.startswith("agent_1_q_")}
        prev_event_values_2 = {k.replace("agent_2_q_", ""): safe_float(v, 0.0) for k, v in row.items() if k.startswith("agent_2_q_")}
        last_action_1 = str(action_1)
        last_action_2 = str(action_2)

    episode_info: Dict[str, Any] = {
        "scenario_name": condition.scenario_name,
        "condition_id": condition.condition_id,
        "condition_label": condition.pair_label(),
        "game_name": condition.game_name,
        "run_profile": run_profile,
        "episode_id": episode_id,
        "random_seed": seed,
        "rounds": rounds,
        "agent_1_type": condition.agent_1.agent_type,
        "agent_2_type": condition.agent_2.agent_type,
        "personality_1": condition.agent_1.personality,
        "personality_2": condition.agent_2.personality,
        "intensity_1": condition.agent_1.intensity,
        "intensity_2": condition.agent_2.intensity,
        "fixed_strategy_1": condition.agent_1.fixed_strategy or "",
        "fixed_strategy_2": condition.agent_2.fixed_strategy or "",
        "errors_count": len(errors),
        "errors_preview": " | ".join(errors[:3]),
    }
    try:
        summary = game.get_summary()
        for k, v in summary.items():
            episode_info[f"game_summary_{k}"] = v
    except Exception:
        pass
    return rows, episode_info


def run_conditions(main_module: Any, conditions: Iterable[Condition], *, run_profile: str,
                   rounds: int, seeds: List[int], progress: bool = True) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    round_rows: List[Dict[str, Any]] = []
    episode_rows: List[Dict[str, Any]] = []
    episode_id = 0
    conditions_list = list(conditions)
    total = len(conditions_list) * len(seeds)
    for condition in conditions_list:
        for seed in seeds:
            episode_id += 1
            if progress:
                print(f"[{episode_id}/{total}] {condition.scenario_name} | {condition.game_name} | {condition.pair_label()} | seed={seed}")
            rows, episode_info = run_episode(
                main_module,
                condition,
                run_profile=run_profile,
                episode_id=episode_id,
                rounds=rounds,
                seed=seed,
            )
            round_rows.extend(rows)
            episode_rows.append(episode_info)
    return round_rows, episode_rows
