#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Centralized state update rules for the integrated model."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .model_schema import AgentState, AppraisalResult, Values, clip, clip01, VALUE_TYPES


@dataclass
class StateUpdater:
    """Mutable state updater.

    Side effects: apply_appraisal mutates the supplied AgentState. Values are not
    mutated here; they are read only to compute well-being.
    """

    mood_decay: float = 0.94
    mood_scale: float = 3.0
    fatigue_emotional_load_rate: float = 0.08
    fatigue_intensity_rate: float = 0.04
    suppression_cost_rate: float = 0.03
    recovery_rate: float = 0.015
    lambda_w: float = 1.0
    lambda_m: float = 1.0
    lambda_f: float = 1.0

    def weighted_wellbeing(self, values: Values) -> float:
        """Compute weighted value satisfaction in [0,1]; side-effect free."""
        weights = values.normalized_priorities()
        return clip01(sum(weights[vt] * clip01(values.current.get(vt, 0.5)) for vt in VALUE_TYPES))

    def recompute_aggregates(self, state: AgentState, values: Values) -> None:
        """Recompute well-being and overall-state fields in place."""
        state.wellbeing = self.weighted_wellbeing(values)
        state.reported_wellbeing = clip(2.0 * state.wellbeing - 1.0, -1.0, 1.0)
        state.overall_state = (
            self.lambda_w * state.reported_wellbeing
            + self.lambda_m * state.mood
            - self.lambda_f * state.fatigue
        )
        state.clamp()

    def apply_appraisal(
        self,
        state: AgentState,
        values: Values,
        appraisal: AppraisalResult,
        emotional_intensity: float = 0.0,
        suppression_cost: float = 0.0,
    ) -> AgentState:
        """Apply appraisal/recovery to state and return the mutated state.

        Mood changes with the signed reaction; fatigue grows with emotional load
        and absolute intensity and recovers when load is low. Suppression cost is
        optional and behavior-driving only in integrated_model variants.
        """
        state.mood = clip(
            state.mood * self.mood_decay + appraisal.reaction_intensity / self.mood_scale,
            -0.5,
            0.5,
        )
        fatigue_delta = (
            self.fatigue_emotional_load_rate * abs(appraisal.emotional_load)
            + self.fatigue_intensity_rate * min(1.5, abs(float(emotional_intensity))) / 1.5
            + self.suppression_cost_rate * max(0.0, float(suppression_cost))
            - self.recovery_rate * (1.0 - min(1.0, abs(appraisal.emotional_load)))
        )
        state.fatigue = clip(state.fatigue + fatigue_delta, 0.0, 1.0)
        state.resources = clip(1.0 - state.fatigue, 0.0, 1.0)
        self.recompute_aggregates(state, values)
        return state

    def compatibility_update_from_payoff(self, state: AgentState, values: Values, payoff: float, max_payoff: float = 5.0) -> None:
        """Reported-runs-compatible lightweight state update.

        This deliberately does not use adapter/appraisal as behavior-driving
        state input. It keeps compatibility mode separate from integrated_model
        while still respecting numeric ranges and the two-phase decide/observe
        invariant.
        """
        material = clip01(float(payoff) / max(1e-6, float(max_payoff)))
        values.update_from_event({"material": material}, alpha=0.15)
        state.mood = clip(state.mood * self.mood_decay + (material - 0.5) / 8.0, -0.5, 0.5)
        state.fatigue = clip(state.fatigue + 0.01 * abs(material - 0.5) - self.recovery_rate, 0.0, 1.0)
        state.resources = clip(1.0 - state.fatigue, 0.0, 1.0)
        self.recompute_aggregates(state, values)
