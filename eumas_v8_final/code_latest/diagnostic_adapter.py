#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Post-hoc game-to-values and appraisal diagnostics.

These helpers are intentionally side-effect free: they do NOT affect agent
behavior. They only enrich experiment CSV files with interpretable diagnostics
that are useful for article revision and reviewer-facing analysis.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
import math


def _clip01(x: float) -> float:
    try:
        x = float(x)
    except Exception:
        return 0.0
    if math.isnan(x) or math.isinf(x):
        return 0.0
    return max(0.0, min(1.0, x))


def _parse_action_name(action: Any) -> str:
    text = str(action or "").strip().lower()
    if "(" in text:
        text = text.split("(", 1)[0]
    return text.strip()


def _parse_offer(action: Any) -> float:
    import re
    text = str(action or "")
    m = re.search(r"(?:offer|amount)\s*=\s*([-+]?\d+(?:\.\d+)?)", text, flags=re.I)
    if m:
        return max(0.0, min(10.0, float(m.group(1))))
    return 5.0


def normalize_payoff(payoff: float, min_payoff: float, max_payoff: float) -> float:
    if max_payoff == min_payoff:
        return 1.0
    return _clip01((float(payoff) - min_payoff) / (max_payoff - min_payoff))


def _pd_payoff(a1: str, a2: str) -> Tuple[float, float]:
    a1 = "cooperate" if "cooperate" in a1 else "defect"
    a2 = "cooperate" if "cooperate" in a2 else "defect"
    return {
        ("cooperate", "cooperate"): (3.0, 3.0),
        ("cooperate", "defect"): (0.0, 5.0),
        ("defect", "cooperate"): (5.0, 0.0),
        ("defect", "defect"): (1.0, 1.0),
    }[(a1, a2)]


def _bos_payoff(a1: str, a2: str) -> Tuple[float, float]:
    a1 = "opera" if "opera" in a1 else "fight"
    a2 = "opera" if "opera" in a2 else "fight"
    return {
        ("opera", "opera"): (3.0, 2.0),
        ("opera", "fight"): (0.0, 0.0),
        ("fight", "opera"): (0.0, 0.0),
        ("fight", "fight"): (2.0, 3.0),
    }[(a1, a2)]


def _ug_payoff(a1: str, a2: str) -> Tuple[float, float]:
    offer = _parse_offer(a1)
    accept = "accept" in _parse_action_name(a2)
    if accept:
        return 10.0 - offer, offer
    return 0.0, 0.0


def action_sets(game_name: str) -> Tuple[List[str], List[str]]:
    g = game_name.lower()
    if "battle" in g:
        return ["opera", "fight"], ["opera", "fight"]
    if "ultimatum" in g:
        # Small representative offer grid is enough for normalized diagnostics.
        return ["offer(offer=0)", "offer(offer=2.5)", "offer(offer=5)", "offer(offer=7.5)", "offer(offer=10)"], ["accept", "reject"]
    return ["cooperate", "defect"], ["cooperate", "defect"]


def payoff_for(game_name: str, a1: str, a2: str) -> Tuple[float, float]:
    g = game_name.lower()
    if "battle" in g:
        return _bos_payoff(_parse_action_name(a1), _parse_action_name(a2))
    if "ultimatum" in g:
        return _ug_payoff(a1, a2)
    return _pd_payoff(_parse_action_name(a1), _parse_action_name(a2))


def payoff_range(game_name: str, agent_id: int) -> Tuple[float, float]:
    acts1, acts2 = action_sets(game_name)
    vals = []
    for a1 in acts1:
        for a2 in acts2:
            p1, p2 = payoff_for(game_name, a1, a2)
            vals.append(p1 if agent_id == 1 else p2)
    return min(vals), max(vals)


def _actual_actions_for_agent(agent_id: int, action_1: str, action_2: str) -> Tuple[str, str]:
    return (action_1, action_2) if agent_id == 1 else (action_2, action_1)


def compute_event_values(game_name: str, agent_id: int, action_1: str, action_2: str, payoff_1: float, payoff_2: float) -> Dict[str, float]:
    """Return material/fairness/relationship/safety in [0, 1]."""
    payoff_i = float(payoff_1 if agent_id == 1 else payoff_2)
    payoff_j = float(payoff_2 if agent_id == 1 else payoff_1)
    min_i, max_i = payoff_range(game_name, agent_id)
    min_j, max_j = payoff_range(game_name, 2 if agent_id == 1 else 1)
    norm_i = normalize_payoff(payoff_i, min_i, max_i)
    norm_j = normalize_payoff(payoff_j, min_j, max_j)

    a1_set, a2_set = action_sets(game_name)
    own_action = action_1 if agent_id == 1 else action_2
    partner_actions = a2_set if agent_id == 1 else a1_set

    # Relationship: how the observed partner action affected my payoff given my action.
    partner_impact_values = []
    for partner_action in partner_actions:
        if agent_id == 1:
            p_i, _ = payoff_for(game_name, own_action, partner_action)
        else:
            _, p_i = payoff_for(game_name, partner_action, own_action)
        partner_impact_values.append(float(p_i))
    best_partner = max(partner_impact_values) if partner_impact_values else payoff_i
    worst_partner = min(partner_impact_values) if partner_impact_values else payoff_i
    relationship = 1.0 if best_partner == worst_partner else (payoff_i - worst_partner) / (best_partner - worst_partner)

    # Safety: inverse normalized regret against actual partner action.
    actual_partner_action = action_2 if agent_id == 1 else action_1
    own_actions = a1_set if agent_id == 1 else a2_set
    best_response_payoff = -1e9
    for candidate in own_actions:
        if agent_id == 1:
            p_i, _ = payoff_for(game_name, candidate, actual_partner_action)
        else:
            _, p_i = payoff_for(game_name, actual_partner_action, candidate)
        best_response_payoff = max(best_response_payoff, float(p_i))
    regret = max(0.0, best_response_payoff - payoff_i)
    max_regret = 0.0
    for oa in own_actions:
        for pa in partner_actions:
            if agent_id == 1:
                p_i, _ = payoff_for(game_name, oa, pa)
                best_resp = max(payoff_for(game_name, cand, pa)[0] for cand in own_actions)
            else:
                _, p_i = payoff_for(game_name, pa, oa)
                best_resp = max(payoff_for(game_name, pa, cand)[1] for cand in own_actions)
            max_regret = max(max_regret, float(best_resp) - float(p_i))
    safety = 1.0 if max_regret <= 0 else 1.0 - regret / max_regret

    return {
        "material": _clip01(norm_i),
        "fairness": _clip01(1.0 - abs(norm_i - norm_j)),
        "relationship": _clip01(relationship),
        "safety": _clip01(safety),
    }


def compute_appraisal(prev_values: Optional[Dict[str, float]], new_values: Dict[str, float], weights: Optional[Dict[str, float]] = None, eps: float = 1e-6) -> Dict[str, Any]:
    keys = ["material", "fairness", "relationship", "safety"]
    weights = weights or {k: 0.25 for k in keys}
    prev_values = prev_values or {k: new_values.get(k, 0.5) for k in keys}
    delta: Dict[str, float] = {}
    urgency: Dict[str, float] = {}
    signed_urgency: Dict[str, float] = {}
    for k in keys:
        old = _clip01(prev_values.get(k, 0.5))
        new = _clip01(new_values.get(k, old))
        d = new - old
        delta[k] = d
        if d < 0:
            u = min(1.0, abs(d) / max(eps, old))
        elif d > 0:
            u = min(1.0, abs(d) / max(eps, 1.0 - old))
        else:
            u = 0.0
        urgency[k] = u
        signed_urgency[k] = (1.0 if d > 0 else -1.0 if d < 0 else 0.0) * u
    weighted_abs = {k: weights.get(k, 0.25) * urgency[k] for k in keys}
    focus = max(weighted_abs, key=weighted_abs.get) if any(weighted_abs.values()) else "none"
    valence = sum(weights.get(k, 0.25) * signed_urgency[k] for k in keys)
    emotional_load = sum(weights.get(k, 0.25) * urgency[k] for k in keys)
    return {
        "delta": delta,
        "urgency": urgency,
        "signed_urgency": signed_urgency,
        "valence": valence,
        "emotional_load": emotional_load,
        "attention_focus": focus,
    }


def flatten_diagnostics(prefix: str, values: Dict[str, float], appraisal: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for k, v in values.items():
        out[f"{prefix}_q_{k}"] = v
    for group_name in ("delta", "urgency", "signed_urgency"):
        group = appraisal.get(group_name, {}) if isinstance(appraisal, dict) else {}
        for k, v in group.items():
            out[f"{prefix}_{group_name}_{k}"] = v
    out[f"{prefix}_valence"] = appraisal.get("valence", "")
    out[f"{prefix}_emotional_load"] = appraisal.get("emotional_load", "")
    out[f"{prefix}_attention_focus"] = appraisal.get("attention_focus", "")
    return out
