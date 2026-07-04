#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Current-state evaluation (ОТС) / appraisal layer."""
from __future__ import annotations

from typing import Dict, Mapping, Optional

from .model_schema import AppraisalResult, ValueType, Values, clip, clip01, VALUE_TYPES


def signed_urgency(previous: float, current: float, desired: float = 1.0, eps: float = 1e-6) -> float:
    """Delta-based bounded signed urgency.

    Gains are normalized by remaining distance to desired; losses by what had
    already been attained. The sign is the sign of the actual value delta. This
    prevents positive improvements below an ideal target from being misclassified
    as negative events.
    """
    prev = clip01(previous)
    cur = clip01(current)
    des = clip01(desired)
    delta = cur - prev
    if delta > 0:
        denom = max(eps, abs(des - prev))
        return min(1.0, abs(delta) / denom)
    if delta < 0:
        denom = max(eps, prev)
        return -min(1.0, abs(delta) / denom)
    return 0.0


class CurrentStateEvaluation:
    """Side-effect-free ОТС/appraisal evaluator."""

    def __init__(self, reaction_scale: float = 1.0):
        self.reaction_scale = float(reaction_scale)

    def evaluate(
        self,
        previous_values: Mapping[ValueType, float] | Values,
        current_values: Mapping[ValueType, float] | Values,
        priorities: Optional[Mapping[ValueType, float]] = None,
        desired_values: Optional[Mapping[ValueType, float]] = None,
        chunk_2: float = 1.0,
    ) -> AppraisalResult:
        """Compute value deltas, urgency, valence, load, focus and reaction.

        Side effects: none. ``chunk_2`` multiplies emotional reaction intensity
        while preserving valence/sign.
        """
        if isinstance(previous_values, Values):
            prev = previous_values.current
            desired = desired_values or previous_values.desired
            pr = priorities or previous_values.normalized_priorities()
        else:
            prev = previous_values
            desired = desired_values or {vt: 1.0 for vt in VALUE_TYPES}
            pr = priorities or {vt: 1.0 / len(VALUE_TYPES) for vt in VALUE_TYPES}
        if isinstance(current_values, Values):
            cur = current_values.current
            desired = desired_values or current_values.desired
            pr = priorities or current_values.normalized_priorities()
        else:
            cur = current_values

        # Normalize priorities to sum 1 for aggregation.
        clipped_pr = {vt: clip(pr.get(vt, 1.0), 0.0, 10.0) for vt in VALUE_TYPES}  # type: ignore[arg-type]
        total_pr = sum(clipped_pr.values()) or 1.0
        weights = {vt: clipped_pr[vt] / total_pr for vt in VALUE_TYPES}

        delta: Dict[ValueType, float] = {}
        urgency: Dict[ValueType, float] = {}
        signed: Dict[ValueType, float] = {}
        weighted_abs: Dict[ValueType, float] = {}
        for vt in VALUE_TYPES:
            old = clip01(prev.get(vt, 0.5))  # type: ignore[arg-type]
            new = clip01(cur.get(vt, old))  # type: ignore[arg-type]
            des = clip01(desired.get(vt, 1.0))  # type: ignore[arg-type]
            su = signed_urgency(old, new, des)
            delta[vt] = new - old
            signed[vt] = su
            urgency[vt] = abs(su)
            weighted_abs[vt] = weights[vt] * urgency[vt]

        valence = sum(weights[vt] * signed[vt] for vt in VALUE_TYPES)
        emotional_load = sum(weights[vt] * urgency[vt] for vt in VALUE_TYPES)
        focus = max(weighted_abs, key=weighted_abs.get) if any(weighted_abs.values()) else None
        reaction = clip(valence * float(chunk_2) * self.reaction_scale, -1.5, 1.5)
        return AppraisalResult(
            value_delta=delta,
            urgency=urgency,
            signed_urgency=signed,
            valence=clip(valence, -1.0, 1.0),
            emotional_load=clip01(emotional_load),
            attention_focus=focus,
            reaction_intensity=reaction,
        )
