#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Runtime utilities for architecture-aligned experiment runs.

The runner uses a strict two-phase loop: decide -> external game.execute_round ->
observe. Agent decide() never simulates a game and observe() is called exactly
once per agent per round.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
import importlib.util
import math
import random
import re
import sys

try:
    import numpy as np
except Exception:  # pragma: no cover
    np = None  # type: ignore

try:
    import torch
except Exception:  # pragma: no cover
    torch = None  # type: ignore

from agent_core import (
    ActionOption,
    AgentState,
    GameResult,
    GameState,
    ModelMode,
    create_core_agent,
    get_legal_actions,
    normalize_model_mode,
)
from experiment_config import AgentSpec, Condition
from diagnostic_adapter import compute_event_values, compute_appraisal, flatten_diagnostics, parse_action_name, parse_offer

_MAIN_CACHE: Dict[Path, Any] = {}


def set_global_seed(seed: int) -> None:
    """Seed Python, NumPy and PyTorch where available."""
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
    """Load the game definitions from main.py."""
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


def role_for(game_name: str, agent_index: int) -> str:
    if "ultimatum" in game_name.lower():
        return "proposer" if agent_index == 1 else "responder"
    return "player"


def create_agent(spec: AgentSpec, name: str, *, model_mode: str, role: str, training: bool = False) -> Any:
    return create_core_agent(
        agent_type=spec.agent_type,
        name=name,
        personality=spec.personality,
        intensity=spec.intensity,
        fixed_strategy=spec.fixed_strategy,
        model_mode=model_mode,
        role=role,
        training=training,
    )


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


def _transition_forced(item: Any) -> bool:
    if isinstance(item, dict):
        return bool(item.get("forced_by_emotion", False))
    meta = getattr(item, "meta", None)
    return bool(isinstance(meta, dict) and meta.get("forced_by_emotion", False))


def count_forced_by_emotion(agent: Any) -> int:
    count = 0
    for module_name in ("rational_module", "dqn_module"):
        module = getattr(agent, module_name, None)
        buffer = getattr(module, "replay_buffer", None)
        if buffer is not None:
            for item in list(buffer):
                if _transition_forced(item):
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
        f"{prefix}_observations_count": int(getattr(agent, "observations_count", 0)),
    }


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
    offer = parse_offer(row.get("action_1")) if "ultimatum" in game else None
    row["offer"] = offer if offer is not None else ""
    row["offer_bin"] = offer_bin(offer)
    row["accepted_flag"] = 1 if "accept" in a2 else 0
    row["fairness_proxy"] = 1.0 - min(abs((offer if offer is not None else 5.0) - 5.0) / 5.0, 1.0) if "ultimatum" in game else ""


def _trace_dict(trace: Any) -> Dict[str, Any]:
    if trace is None:
        return {}
    if hasattr(trace, "to_dict"):
        return trace.to_dict()
    if isinstance(trace, dict):
        return dict(trace)
    return {}


def _observation_dict(obs: Any) -> Dict[str, Any]:
    if obs is None:
        return {}
    if hasattr(obs, "to_plain_dict"):
        return obs.to_plain_dict()
    if isinstance(obs, dict):
        return dict(obs)
    return {}


def build_round_row(
    *,
    condition: Condition,
    run_profile: str,
    episode_id: int,
    round_id: int,
    seed: int,
    model_mode: str,
    action_1: str,
    action_2: str,
    payoff_1: float,
    payoff_2: float,
    cumulative_payoff_1: float,
    cumulative_payoff_2: float,
    agent_1: Any,
    agent_2: Any,
    decision_trace_1: Optional[Any] = None,
    decision_trace_2: Optional[Any] = None,
    observation_trace_1: Optional[Any] = None,
    observation_trace_2: Optional[Any] = None,
    prev_values_1: Optional[Dict[str, float]] = None,
    prev_values_2: Optional[Dict[str, float]] = None,
    fallback_used: bool = False,
    errors_count_so_far: int = 0,
) -> Dict[str, Any]:
    mode = normalize_model_mode(model_mode).value
    adapter_driving = mode == ModelMode.INTEGRATED_MODEL.value
    row: Dict[str, Any] = {
        "scenario_name": condition.scenario_name,
        "condition_id": condition.condition_id,
        "condition_label": condition.pair_label(),
        "game_name": condition.game_name,
        "run_profile": run_profile,
        "model_mode": mode,
        "mechanism_status": "behavior-driving" if adapter_driving else "diagnostic/explanatory",
        "adapter_behavior_driving": adapter_driving,
        "appraisal_behavior_driving": adapter_driving,
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
        "role_1": role_for(condition.game_name, 1),
        "role_2": role_for(condition.game_name, 2),
        "focal_agent_id_1": 1,
        "focal_agent_id_2": 2,
        "action_1": str(action_1),
        "action_2": str(action_2),
        "own_action_1": str(action_1),
        "own_action_2": str(action_2),
        "opponent_action_1": str(action_2),
        "opponent_action_2": str(action_1),
        "payoff_1": safe_float(payoff_1),
        "payoff_2": safe_float(payoff_2),
        "own_payoff_1": safe_float(payoff_1),
        "own_payoff_2": safe_float(payoff_2),
        "opponent_payoff_1": safe_float(payoff_2),
        "opponent_payoff_2": safe_float(payoff_1),
        "pair_payoff": safe_float(payoff_1) + safe_float(payoff_2),
        "cumulative_payoff_1": safe_float(cumulative_payoff_1),
        "cumulative_payoff_2": safe_float(cumulative_payoff_2),
        "fallback_used": bool(fallback_used),
        "errors_count_so_far": int(errors_count_so_far),
    }
    for idx, agent in ((1, agent_1), (2, agent_2)):
        row[f"mood_{idx}"] = get_state_metric(agent, "mood")
        row[f"wellbeing_{idx}"] = get_state_metric(agent, "wellbeing")
        row[f"reported_wellbeing_{idx}"] = get_state_metric(agent, "reported_wellbeing")
        row[f"fatigue_{idx}"] = get_state_metric(agent, "fatigue")
        row[f"resources_{idx}"] = get_state_metric(agent, "resources", 0.0)
        row[f"overall_state_{idx}"] = get_state_metric(agent, "overall_state")
        row[f"negative_state_flag_{idx}"] = 1 if row[f"overall_state_{idx}"] < 0 else 0
        row.update(learning_metrics(agent, f"agent_{idx}"))

    for idx, trace in ((1, decision_trace_1), (2, decision_trace_2)):
        td = _trace_dict(trace)
        for src, dst in {
            "emotional_intensity": "emotional_intensity",
            "threshold": "threshold",
            "emotional_action": "emotional_action",
            "rational_action": "rational_action",
            "final_action": "final_action",
            "forced_by_emotion": "forced_by_emotion",
            "override_reason": "override_reason",
            "action_type": "action_type",
        }.items():
            if src in td:
                row[f"agent_{idx}_{dst}"] = td[src]
        row[f"agent_{idx}_suppressed"] = 1 if td.get("emotional_action") and td.get("emotional_action") != td.get("final_action") else 0
        row[f"agent_{idx}_suppression_cost_proxy"] = abs(safe_float(td.get("emotional_intensity", 0.0))) * row[f"agent_{idx}_suppressed"]

    # Use observation traces when available, and independently reconstruct diagnostics for CSV compatibility.
    for idx, obs in ((1, observation_trace_1), (2, observation_trace_2)):
        od = _observation_dict(obs)
        for k, v in od.items():
            row[f"agent_{idx}_{k}"] = v

    try:
        q1 = compute_event_values(condition.game_name, 1, action_1, action_2, payoff_1, payoff_2)
        q2 = compute_event_values(condition.game_name, 2, action_1, action_2, payoff_1, payoff_2)
        app1 = compute_appraisal(prev_values_1, q1)
        app2 = compute_appraisal(prev_values_2, q2)
        row.update(flatten_diagnostics("agent_1", q1, app1))
        row.update(flatten_diagnostics("agent_2", q2, app2))
    except Exception as exc:
        row["diagnostic_adapter_error"] = str(exc)
    add_game_specific_round_features(row)
    return row


def _game_state_from_external(game: Any, condition: Condition, agent_index: int, legal_actions: Sequence[ActionOption], opponent_last_action: Optional[str]) -> GameState:
    try:
        raw_state = game.get_game_state(agent_index - 1)
        params = dict(getattr(raw_state, "game_parameters", {}) or {})
    except Exception:
        params = {}
    return GameState(
        game_name=condition.game_name,
        game_parameters=params,
        available_actions=list(legal_actions),
        role=role_for(condition.game_name, agent_index),
        agent_id=agent_index,
        opponent_last_action=opponent_last_action,
    )


def _handle_error(errors: List[str], strict: bool, allow_fallback: bool, message: str) -> None:
    errors.append(message)
    if strict or not allow_fallback:
        raise RuntimeError(message)


def run_episode(
    main_module: Any,
    condition: Condition,
    *,
    run_profile: str,
    episode_id: int,
    rounds: int,
    seed: int,
    model_mode: str = ModelMode.REPORTED_RUNS_COMPAT.value,
    strict: bool = False,
    allow_fallback: bool = False,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Run one episode with a strict decide -> external game -> observe loop."""
    set_global_seed(seed)
    mode = normalize_model_mode(model_mode).value
    game = make_game(main_module, condition.game_name)
    legal_1 = get_legal_actions(condition.game_name, role_for(condition.game_name, 1))
    legal_2 = get_legal_actions(condition.game_name, role_for(condition.game_name, 2))
    agent_1 = create_agent(condition.agent_1, "Agent_1", model_mode=mode, role=role_for(condition.game_name, 1), training=False)
    agent_2 = create_agent(condition.agent_2, "Agent_2", model_mode=mode, role=role_for(condition.game_name, 2), training=False)

    last_action_1: Optional[str] = None
    last_action_2: Optional[str] = None
    rows: List[Dict[str, Any]] = []
    errors: List[str] = []
    fallback_used = False
    prev_event_values_1: Optional[Dict[str, float]] = None
    prev_event_values_2: Optional[Dict[str, float]] = None

    for round_id in range(1, int(rounds) + 1):
        obs1 = _game_state_from_external(game, condition, 1, legal_1, last_action_2)
        obs2 = _game_state_from_external(game, condition, 2, legal_2, last_action_1)
        pre_state_1 = agent_1.state.snapshot()
        pre_state_2 = agent_2.state.snapshot()
        try:
            action_1, trace_1 = agent_1.decide(obs1, legal_1, round_id)
        except Exception as exc:
            _handle_error(errors, strict, allow_fallback, f"round {round_id}: agent_1 decide failed: {exc}")
            action_1 = fallback_action(condition.game_name, 1)
            trace_1 = None
            fallback_used = True
        try:
            action_2, trace_2 = agent_2.decide(obs2, legal_2, round_id)
        except Exception as exc:
            _handle_error(errors, strict, allow_fallback, f"round {round_id}: agent_2 decide failed: {exc}")
            action_2 = fallback_action(condition.game_name, 2)
            trace_2 = None
            fallback_used = True
        try:
            payoff_1, payoff_2 = game.execute_round(str(action_1), str(action_2))
        except Exception as exc:
            _handle_error(errors, strict, allow_fallback, f"round {round_id}: game.execute_round failed for ({action_1}, {action_2}): {exc}")
            action_1 = fallback_action(condition.game_name, 1)
            action_2 = fallback_action(condition.game_name, 2)
            payoff_1, payoff_2 = game.execute_round(str(action_1), str(action_2))
            fallback_used = True
        try:
            result_1 = GameResult(
                game_name=condition.game_name,
                agent_id=1,
                role=role_for(condition.game_name, 1),
                own_action=str(action_1),
                opponent_action=str(action_2),
                own_payoff=float(payoff_1),
                opponent_payoff=float(payoff_2),
                game_state_after=dict(getattr(game, "current_state", {}) or {}),
            )
            result_2 = GameResult(
                game_name=condition.game_name,
                agent_id=2,
                role=role_for(condition.game_name, 2),
                own_action=str(action_2),
                opponent_action=str(action_1),
                own_payoff=float(payoff_2),
                opponent_payoff=float(payoff_1),
                game_state_after=dict(getattr(game, "current_state", {}) or {}),
            )
            obs_trace_1 = agent_1.observe(result_1, trace_1, pre_state_1)
            obs_trace_2 = agent_2.observe(result_2, trace_2, pre_state_2)
        except Exception as exc:
            _handle_error(errors, strict, allow_fallback, f"round {round_id}: observe failed: {exc}")
            obs_trace_1 = None
            obs_trace_2 = None
            fallback_used = True

        row = build_round_row(
            condition=condition,
            run_profile=run_profile,
            episode_id=episode_id,
            round_id=round_id,
            seed=seed,
            model_mode=mode,
            action_1=str(action_1),
            action_2=str(action_2),
            payoff_1=float(payoff_1),
            payoff_2=float(payoff_2),
            cumulative_payoff_1=float(game.payoffs[0]),
            cumulative_payoff_2=float(game.payoffs[1]),
            agent_1=agent_1,
            agent_2=agent_2,
            decision_trace_1=trace_1,
            decision_trace_2=trace_2,
            observation_trace_1=obs_trace_1,
            observation_trace_2=obs_trace_2,
            prev_values_1=prev_event_values_1,
            prev_values_2=prev_event_values_2,
            fallback_used=fallback_used,
            errors_count_so_far=len(errors),
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
        "model_mode": mode,
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
        "fallback_used": bool(fallback_used),
        "errors_preview": " | ".join(errors[:3]),
        "duplicate_observe_count": int(sum(safe_float(r.get("agent_1_duplicate_update_count"), 0) + safe_float(r.get("agent_2_duplicate_update_count"), 0) for r in rows)),
    }
    try:
        summary = game.get_summary()
        for k, v in summary.items():
            episode_info[f"game_summary_{k}"] = v
    except Exception:
        pass
    return rows, episode_info


def run_conditions(
    main_module: Any,
    conditions: Iterable[Condition],
    *,
    run_profile: str,
    rounds: int,
    seeds: List[int],
    model_mode: str = ModelMode.REPORTED_RUNS_COMPAT.value,
    strict: bool = False,
    allow_fallback: bool = False,
    progress: bool = True,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
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
                model_mode=model_mode,
                strict=strict,
                allow_fallback=allow_fallback,
            )
            round_rows.extend(rows)
            episode_rows.append(episode_info)
    return round_rows, episode_rows
