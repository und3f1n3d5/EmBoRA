#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Production game-to-values adapter.

The adapter is side-effect free. It implements the article v11 API for a focal
agent: A_i^G(a_i, a_j, pi_i, pi_j) -> material/fairness/relationship/safety in
[0, 1]. It is used as diagnostic-only in reported_runs_compat and as a
behavior-driving signal in integrated_model.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Tuple
import math
import re

from .model_schema import ValueType, clip01


def parse_action_name(action: Any) -> str:
    text = str(action or "").strip().lower()
    if "(" in text:
        text = text.split("(", 1)[0]
    return text.strip()


def parse_offer(action: Any) -> float:
    text = str(action or "")
    match = re.search(r"(?:offer|amount)\s*=\s*([-+]?\d+(?:\.\d+)?)", text, flags=re.I)
    if match:
        return max(0.0, min(10.0, float(match.group(1))))
    # An offer action without explicit parameter is treated as an equal split.
    return 5.0


class GameValueAdapter:
    """Side-effect-free mapper from external outcomes to internal event values."""

    def action_sets(self, game_name: str, role: str | None = None) -> Tuple[List[str], List[str]]:
        """Return representative legal action sets for the two roles in a game."""
        g = game_name.lower()
        if "battle" in g:
            return ["opera", "fight"], ["opera", "fight"]
        if "ultimatum" in g:
            return [
                "offer(offer=0)", "offer(offer=2.5)", "offer(offer=5)",
                "offer(offer=7.5)", "offer(offer=10)",
            ], ["accept", "reject"]
        return ["cooperate", "defect"], ["cooperate", "defect"]

    def payoff_for(self, game_name: str, action_1: str, action_2: str) -> Tuple[float, float]:
        """Compute game payoff for normalized action strings; side-effect free."""
        g = game_name.lower()
        if "battle" in g:
            a1 = "opera" if "opera" in parse_action_name(action_1) else "fight"
            a2 = "opera" if "opera" in parse_action_name(action_2) else "fight"
            return {
                ("opera", "opera"): (3.0, 2.0),
                ("opera", "fight"): (0.0, 0.0),
                ("fight", "opera"): (0.0, 0.0),
                ("fight", "fight"): (2.0, 3.0),
            }[(a1, a2)]
        if "ultimatum" in g:
            offer = parse_offer(action_1)
            accept = "accept" in parse_action_name(action_2)
            return (10.0 - offer, offer) if accept else (0.0, 0.0)
        a1 = "cooperate" if "cooperate" in parse_action_name(action_1) else "defect"
        a2 = "cooperate" if "cooperate" in parse_action_name(action_2) else "defect"
        return {
            ("cooperate", "cooperate"): (3.0, 3.0),
            ("cooperate", "defect"): (0.0, 5.0),
            ("defect", "cooperate"): (5.0, 0.0),
            ("defect", "defect"): (1.0, 1.0),
        }[(a1, a2)]

    def payoff_range(self, game_name: str, agent_id: int) -> Tuple[float, float]:
        """Return feasible min/max payoff for one focal side; side-effect free."""
        acts1, acts2 = self.action_sets(game_name)
        vals: List[float] = []
        for a1 in acts1:
            for a2 in acts2:
                p1, p2 = self.payoff_for(game_name, a1, a2)
                vals.append(float(p1 if int(agent_id) == 1 else p2))
        return min(vals), max(vals)

    def normalize_payoff(self, payoff: float, min_payoff: float, max_payoff: float) -> float:
        """Normalize payoff to [0, 1]; side-effect free."""
        if max_payoff == min_payoff:
            return 1.0
        return clip01((float(payoff) - min_payoff) / (max_payoff - min_payoff))

    def compute_event_values(
        self,
        *,
        game_name: str,
        focal_agent_id: int,
        own_action: str,
        opponent_action: str,
        own_payoff: float,
        opponent_payoff: float,
        role: str | None = None,
    ) -> Dict[ValueType, float]:
        """Return material/fairness/relationship/safety for the focal agent.

        Inputs are focal-agent oriented. For compatibility with two-sided games,
        focal_agent_id=1 means own_action is player-1 action; focal_agent_id=2
        means own_action is player-2 action and is internally reordered.
        """
        agent_id = int(focal_agent_id)
        if agent_id == 1:
            action_1, action_2 = str(own_action), str(opponent_action)
            payoff_1, payoff_2 = float(own_payoff), float(opponent_payoff)
        else:
            action_1, action_2 = str(opponent_action), str(own_action)
            payoff_1, payoff_2 = float(opponent_payoff), float(own_payoff)

        min_i, max_i = self.payoff_range(game_name, agent_id)
        min_j, max_j = self.payoff_range(game_name, 2 if agent_id == 1 else 1)
        norm_i = self.normalize_payoff(own_payoff, min_i, max_i)
        norm_j = self.normalize_payoff(opponent_payoff, min_j, max_j)

        a1_set, a2_set = self.action_sets(game_name, role)
        own_actions = a1_set if agent_id == 1 else a2_set
        partner_actions = a2_set if agent_id == 1 else a1_set
        actual_partner_action = action_2 if agent_id == 1 else action_1

        # Relationship: how supportive the observed partner action was given my action.
        partner_impact_values: List[float] = []
        for partner_action in partner_actions:
            if agent_id == 1:
                p_i, _ = self.payoff_for(game_name, str(own_action), partner_action)
            else:
                _, p_i = self.payoff_for(game_name, partner_action, str(own_action))
            partner_impact_values.append(float(p_i))
        best_partner = max(partner_impact_values) if partner_impact_values else float(own_payoff)
        worst_partner = min(partner_impact_values) if partner_impact_values else float(own_payoff)
        relationship = 1.0 if best_partner == worst_partner else (float(own_payoff) - worst_partner) / (best_partner - worst_partner)

        # Safety: inverse normalized ex-post regret relative to a best response.
        best_response_payoff = -1e9
        for candidate in own_actions:
            if agent_id == 1:
                p_i, _ = self.payoff_for(game_name, candidate, actual_partner_action)
            else:
                _, p_i = self.payoff_for(game_name, actual_partner_action, candidate)
            best_response_payoff = max(best_response_payoff, float(p_i))
        regret = max(0.0, best_response_payoff - float(own_payoff))

        max_regret = 0.0
        for own_candidate in own_actions:
            for partner_candidate in partner_actions:
                if agent_id == 1:
                    p_i, _ = self.payoff_for(game_name, own_candidate, partner_candidate)
                    best_resp = max(self.payoff_for(game_name, c, partner_candidate)[0] for c in own_actions)
                else:
                    _, p_i = self.payoff_for(game_name, partner_candidate, own_candidate)
                    best_resp = max(self.payoff_for(game_name, partner_candidate, c)[1] for c in own_actions)
                max_regret = max(max_regret, float(best_resp) - float(p_i))
        safety = 1.0 if max_regret <= 0 else 1.0 - regret / max_regret

        return {
            ValueType.MATERIAL: clip01(norm_i),
            ValueType.FAIRNESS: clip01(1.0 - abs(norm_i - norm_j)),
            ValueType.RELATIONSHIP: clip01(relationship),
            ValueType.SAFETY: clip01(safety),
        }


_DEFAULT_ADAPTER = GameValueAdapter()


def compute_event_values(
    game_name: str,
    focal_agent_id: int,
    own_action: str,
    opponent_action: str,
    own_payoff: float,
    opponent_payoff: float,
    role: str | None = None,
) -> Dict[ValueType, float]:
    """Functional convenience wrapper; side-effect free."""
    return _DEFAULT_ADAPTER.compute_event_values(
        game_name=game_name,
        focal_agent_id=focal_agent_id,
        own_action=own_action,
        opponent_action=opponent_action,
        own_payoff=own_payoff,
        opponent_payoff=opponent_payoff,
        role=role,
    )
