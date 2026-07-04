#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Minimal one-round white-box trace for the architecture-aligned core."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent_core import GameResult, GameState, ModelMode, create_core_agent, get_legal_actions


def main() -> None:
    actions = get_legal_actions("Prisoners Dilemma")
    a1 = create_core_agent(agent_type="emotional_rational", name="Hybrid", model_mode=ModelMode.INTEGRATED_MODEL)
    a2 = create_core_agent(agent_type="fixed_strategy", name="TFT", fixed_strategy="tit_for_tat", model_mode=ModelMode.INTEGRATED_MODEL)

    obs1 = GameState("Prisoners Dilemma", available_actions=actions, agent_id=1)
    obs2 = GameState("Prisoners Dilemma", available_actions=actions, agent_id=2)
    action1, trace1 = a1.decide(obs1, actions, 1)
    action2, trace2 = a2.decide(obs2, actions, 1)

    # External game: PD CC=3/3, CD=0/5, DC=5/0, DD=1/1.
    payoffs = {
        ("cooperate", "cooperate"): (3.0, 3.0),
        ("cooperate", "defect"): (0.0, 5.0),
        ("defect", "cooperate"): (5.0, 0.0),
        ("defect", "defect"): (1.0, 1.0),
    }
    payoff1, payoff2 = payoffs[(action1, action2)]

    result1 = GameResult("Prisoners Dilemma", 1, "player", action1, action2, payoff1, payoff2)
    result2 = GameResult("Prisoners Dilemma", 2, "player", action2, action1, payoff2, payoff1)
    obs_trace1 = a1.observe(result1, trace1)
    obs_trace2 = a2.observe(result2, trace2)

    print("Agent 1 decision:", trace1.to_dict())
    print("Agent 1 observation:", obs_trace1.to_plain_dict())
    print("Agent 1 state:", a1.get_public_metrics())
    print("Agent 2 decision:", trace2.to_dict())
    print("Agent 2 observation:", obs_trace2.to_plain_dict())


if __name__ == "__main__":
    main()
