#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Post-hoc game-to-values/appraisal diagnostics.

This module now delegates to the same production adapter/appraisal used by the
integrated model. In reported_runs_compat these values remain diagnostic only;
in integrated_model the same formulas are behavior-driving through observe().
"""
from __future__ import annotations

from typing import Any, Dict, Optional, Tuple, List

from agent_core.appraisal import CurrentStateEvaluation
from agent_core.model_schema import ValueType, VALUE_TYPES
from agent_core.value_adapter import GameValueAdapter, parse_action_name, parse_offer

_ADAPTER = GameValueAdapter()
_APPRAISAL = CurrentStateEvaluation()


def _stringify(values: Dict[ValueType, float]) -> Dict[str, float]:
    return {k.value if isinstance(k, ValueType) else str(k): float(v) for k, v in values.items()}


def _vt_map(values: Optional[Dict[str, float]]) -> Optional[Dict[ValueType, float]]:
    if values is None:
        return None
    out: Dict[ValueType, float] = {}
    for vt in VALUE_TYPES:
        out[vt] = float(values.get(vt.value, values.get(str(vt), 0.5)))
    return out


def action_sets(game_name: str) -> Tuple[List[str], List[str]]:
    return _ADAPTER.action_sets(game_name)


def payoff_for(game_name: str, a1: str, a2: str) -> Tuple[float, float]:
    return _ADAPTER.payoff_for(game_name, a1, a2)


def payoff_range(game_name: str, agent_id: int) -> Tuple[float, float]:
    return _ADAPTER.payoff_range(game_name, agent_id)


def normalize_payoff(payoff: float, min_payoff: float, max_payoff: float) -> float:
    return _ADAPTER.normalize_payoff(payoff, min_payoff, max_payoff)


def compute_event_values(game_name: str, agent_id: int, action_1: str, action_2: str, payoff_1: float, payoff_2: float) -> Dict[str, float]:
    """Return material/fairness/relationship/safety in [0,1] for one focal side."""
    if int(agent_id) == 1:
        own_action, opponent_action = action_1, action_2
        own_payoff, opponent_payoff = payoff_1, payoff_2
    else:
        own_action, opponent_action = action_2, action_1
        own_payoff, opponent_payoff = payoff_2, payoff_1
    return _stringify(_ADAPTER.compute_event_values(
        game_name=game_name,
        focal_agent_id=int(agent_id),
        own_action=own_action,
        opponent_action=opponent_action,
        own_payoff=float(own_payoff),
        opponent_payoff=float(opponent_payoff),
        role="proposer" if ("ultimatum" in game_name.lower() and int(agent_id) == 1) else "responder" if "ultimatum" in game_name.lower() else "player",
    ))


def compute_appraisal(prev_values: Optional[Dict[str, float]], new_values: Dict[str, float], weights: Optional[Dict[str, float]] = None, eps: float = 1e-6) -> Dict[str, Any]:
    """Return delta-based appraisal diagnostics for string-key values."""
    prev = _vt_map(prev_values) or {vt: float(new_values.get(vt.value, 0.5)) for vt in VALUE_TYPES}
    cur = {vt: float(new_values.get(vt.value, prev.get(vt, 0.5))) for vt in VALUE_TYPES}
    if weights:
        pr = {vt: float(weights.get(vt.value, weights.get(str(vt), 1.0))) for vt in VALUE_TYPES}
    else:
        pr = {vt: 1.0 for vt in VALUE_TYPES}
    app = _APPRAISAL.evaluate(prev, cur, priorities=pr)
    return {
        "delta": _stringify(app.value_delta),
        "urgency": _stringify(app.urgency),
        "signed_urgency": _stringify(app.signed_urgency),
        "valence": app.valence,
        "emotional_load": app.emotional_load,
        "attention_focus": app.attention_focus.value if app.attention_focus else "none",
        "reaction_intensity": app.reaction_intensity,
    }


def flatten_diagnostics(prefix: str, values: Dict[str, float], appraisal: Dict[str, Any]) -> Dict[str, Any]:
    """Flatten adapter/appraisal diagnostics into round_level CSV columns."""
    out: Dict[str, Any] = {}
    for k, v in values.items():
        out[f"{prefix}_q_{k}"] = v
        out[f"{prefix}_event_{k}"] = v
    for group_name in ("delta", "urgency", "signed_urgency"):
        group = appraisal.get(group_name, {}) if isinstance(appraisal, dict) else {}
        for k, v in group.items():
            out[f"{prefix}_{group_name}_{k}"] = v
    out[f"{prefix}_valence"] = appraisal.get("valence", "")
    out[f"{prefix}_emotional_load"] = appraisal.get("emotional_load", "")
    out[f"{prefix}_attention_focus"] = appraisal.get("attention_focus", "")
    out[f"{prefix}_reaction_intensity"] = appraisal.get("reaction_intensity", "")
    return out
