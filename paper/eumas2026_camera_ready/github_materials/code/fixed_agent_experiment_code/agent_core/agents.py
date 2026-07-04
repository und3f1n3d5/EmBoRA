#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Architecture-aligned agent implementations with decide/observe API."""
from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple
import random

from .appraisal import CurrentStateEvaluation
from .dqn import DQNPolicy, Transition
from .model_schema import (
    ActionOption,
    AgentKind,
    AgentState,
    DecisionTrace,
    GameResult,
    GameState,
    ModelMode,
    ObservationTrace,
    Values,
    ValueType,
    clip,
    normalize_model_mode,
)
from .state_updater import StateUpdater
from .value_adapter import GameValueAdapter, parse_action_name


def get_legal_actions(game_name: str, role: str = "player", offer_grid: Sequence[float] = (2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0)) -> List[ActionOption]:
    """Return role-specific action options.

    For UG, proposers only offer and responders only accept/reject. For PD and
    BoS both roles have the same action space.
    """
    g = game_name.lower()
    r = (role or "player").lower()
    if "ultimatum" in g:
        if r == "responder":
            return [ActionOption("accept"), ActionOption("reject")]
        return [ActionOption("offer", {"offer": float(x)}) for x in offer_grid]
    if "battle" in g:
        return [ActionOption("opera"), ActionOption("fight")]
    return [ActionOption("cooperate"), ActionOption("defect")]


def _kind_from_agent_type(agent_type: str) -> AgentKind:
    text = str(agent_type or "").lower()
    if text in {"emotional_rational", "hybrid"}:
        return AgentKind.HYBRID
    if text in {"emotional", "emotional_only"}:
        return AgentKind.EMOTIONAL_ONLY
    if text in {"rational", "rational_only"}:
        return AgentKind.RATIONAL_ONLY
    if text in {"fixed_strategy", "fixed"}:
        return AgentKind.FIXED_STRATEGY
    raise ValueError(f"Unknown agent type: {agent_type}")


def _chunk_1(personality: str) -> float:
    # Lower threshold for pessimistic/irritable; higher for optimistic/stable.
    return {"pessimistic": 0.55, "neutral": 0.75, "optimistic": 0.95}.get(str(personality).lower(), 0.75)


def _chunk_2(intensity: str) -> float:
    return {"low": 0.5, "neutral": 1.0, "high": 1.5}.get(str(intensity).lower(), 1.0)


class ArchitectureAlignedAgent:
    """Base decide/observe agent.

    decide() is side-effect free with respect to values/state/learning buffers:
    it only constructs a DecisionTrace from the current state. observe() is the
    single state-update and replay-storage point.
    """

    def __init__(
        self,
        *,
        name: str,
        agent_type: str,
        personality: str = "neutral",
        intensity: str = "neutral",
        model_mode: ModelMode | str = ModelMode.REPORTED_RUNS_COMPAT,
        fixed_strategy: Optional[str] = None,
        role: str = "player",
        training: bool = False,
    ):
        self.name = name
        self.kind = _kind_from_agent_type(agent_type)
        self.agent_type = agent_type
        self.personality = personality or "neutral"
        self.intensity = intensity or "neutral"
        self.fixed_strategy = fixed_strategy or "tit_for_tat"
        self.role = role
        self.model_mode = normalize_model_mode(model_mode)
        self.training = bool(training)
        self.chunk_1 = _chunk_1(self.personality)
        self.chunk_2 = _chunk_2(self.intensity)
        self.values = Values()
        self.state = AgentState()
        self.state_updater = StateUpdater()
        self.value_adapter = GameValueAdapter()
        self.appraisal = CurrentStateEvaluation()
        # DQN-like modules. Output dimension 16 safely covers current actions and controls.
        self.emotional_module = DQNPolicy(input_dim=14, output_dim=16, epsilon=0.0 if not training else 1.0)
        self.rational_module = DQNPolicy(input_dim=16, output_dim=16, epsilon=0.0 if not training else 1.0)
        self.last_decision: Optional[DecisionTrace] = None
        self.last_observation: Optional[ObservationTrace] = None
        self.last_action: Optional[str] = None
        self.observations_count = 0
        self._last_observed_round: Optional[int] = None

    def reset_episode(self, seed: Optional[int] = None) -> None:
        """Reset mutable episode state; mutates the agent."""
        if seed is not None:
            random.seed(seed)
        self.values = Values()
        self.state = AgentState()
        self.last_decision = None
        self.last_observation = None
        self.last_action = None
        self.observations_count = 0
        self._last_observed_round = None

    def snapshot_before_decision(self) -> Dict[str, Any]:
        """Return a state/value snapshot for tests and traces; side-effect free."""
        return {
            "state": self.state.snapshot(),
            "values": self.values.snapshot(),
            "em_buffer_size": len(self.emotional_module.replay_buffer),
            "rm_buffer_size": len(self.rational_module.replay_buffer),
        }

    def _state_vector(self, observation: GameState, legal_actions: Sequence[ActionOption]) -> List[float]:
        params = observation.game_parameters or {}
        param_vals = [float(params.get(k, 0.0)) / 100.0 for k in sorted(params)[:4]]
        while len(param_vals) < 4:
            param_vals.append(0.0)
        vals = [self.values.current[vt] for vt in self.values.current]
        return [
            self.state.mood,
            self.state.fatigue,
            self.state.resources,
            self.state.wellbeing,
            self.state.overall_state,
            float(len(legal_actions)) / 10.0,
            *vals,
            *param_vals,
        ][:14]

    def _threshold(self) -> float:
        """Fatigue-dependent emotional dominance threshold in [0.15, 1.25]."""
        theta0 = self.chunk_1
        fatigue_modifier = 0.45 * self.state.fatigue
        mood_modifier = -0.12 if self.state.mood < -0.25 else 0.05 if self.state.mood > 0.25 else 0.0
        resource_modifier = -0.10 if self.state.resources < 0.4 else 0.0
        return clip(theta0 * (1.0 - fatigue_modifier) + mood_modifier + resource_modifier, 0.15, 1.25)

    def _heuristic_emotional_action(self, observation: GameState, legal_actions: Sequence[ActionOption]) -> Tuple[str, float]:
        """Fast affective proposal and intensity; side-effect free."""
        if not legal_actions:
            raise ValueError("No legal actions supplied to decide()")
        # Deterministic DQN index in eval mode, but mixed with simple appraisal-like sign.
        idx = self.emotional_module.select_action(self._state_vector(observation, legal_actions), len(legal_actions), eval_mode=not self.training)
        # Keep intuitive defaults for stable smoke/sanity checks.
        game = observation.game_name.lower()
        if self.kind == AgentKind.RATIONAL_ONLY:
            intensity = 0.0
        else:
            base = self.state.mood - 0.35 * self.state.fatigue + 0.15 * (self.state.wellbeing - 0.5)
            intensity = clip(base * self.chunk_2, -1.5, 1.5)
        if "ultimatum" in game and observation.role == "responder":
            action = "accept" if intensity >= -0.35 else "reject"
        elif "ultimatum" in game:
            # More positive state -> fairer/more generous offers around 5.
            target = 5.0 + max(-2.0, min(2.0, intensity))
            best = min(legal_actions, key=lambda a: abs(float(a.params.get("offer", 5.0)) - target))
            action = str(best)
        elif "battle" in game:
            action = str(legal_actions[idx % len(legal_actions)])
        else:
            action = "cooperate" if intensity >= -0.25 else "defect"
            if action not in {parse_action_name(a) for a in legal_actions}:
                action = str(legal_actions[idx % len(legal_actions)])
        return action, intensity

    def _rational_action(self, observation: GameState, legal_actions: Sequence[ActionOption]) -> str:
        """Payoff/overall-state oriented proposal; side-effect free."""
        if not legal_actions:
            raise ValueError("No legal actions supplied to decide()")
        game = observation.game_name.lower()
        if "ultimatum" in game and observation.role == "responder":
            # Accept when offer is unknown in state; a later richer state can set offer.
            return "accept"
        if "ultimatum" in game:
            # Self-interested but bounded: offer 4 by default to increase acceptance plausibility.
            target = 4.0 if self.kind == AgentKind.RATIONAL_ONLY else 5.0
            best = min(legal_actions, key=lambda a: abs(float(a.params.get("offer", 5.0)) - target))
            return str(best)
        if "battle" in game:
            # Prefer role-specific favorite if role names are used, else DQN index.
            if observation.agent_id == 1:
                return "opera"
            return "fight"
        if self.kind == AgentKind.RATIONAL_ONLY:
            return "defect"
        return "cooperate" if self.state.overall_state >= -0.2 else "defect"

    def _fixed_action(self, observation: GameState, legal_actions: Sequence[ActionOption]) -> str:
        strategy = str(self.fixed_strategy or "tit_for_tat").lower()
        game = observation.game_name.lower()
        if "ultimatum" in game:
            if observation.role == "responder":
                if strategy == "always_defect":
                    return "reject"
                return "accept"
            if strategy == "always_defect":
                return "offer(offer=2.00)"
            if strategy == "always_cooperate":
                return "offer(offer=5.00)"
            return "offer(offer=4.00)"
        if "battle" in game:
            if strategy == "always_defect":
                return "fight"
            return "opera" if strategy == "always_cooperate" else (observation.opponent_last_action or "opera")
        if strategy == "always_cooperate":
            return "cooperate"
        if strategy == "always_defect":
            return "defect"
        if observation.opponent_last_action:
            opp = parse_action_name(observation.opponent_last_action)
            return "cooperate" if "cooperate" in opp else "defect"
        return "cooperate"

    def _ensure_legal(self, action: str, legal_actions: Sequence[ActionOption]) -> str:
        legal_names = {parse_action_name(str(a)) for a in legal_actions}
        name = parse_action_name(action)
        if name in legal_names:
            if name == "offer" and legal_actions:
                return action
            return name
        if not legal_actions:
            raise ValueError("No legal actions available")
        return str(legal_actions[0])

    def decide(self, observation: GameState, legal_actions: Sequence[ActionOption], turn_number: int) -> Tuple[str, DecisionTrace]:
        """Choose action without mutating state/values/replay buffers."""
        obs = observation
        if not obs.available_actions:
            obs = GameState(
                game_name=observation.game_name,
                game_parameters=dict(observation.game_parameters),
                available_actions=list(legal_actions),
                role=observation.role,
                agent_id=observation.agent_id,
                opponent_last_action=observation.opponent_last_action,
            )
        if self.kind == AgentKind.FIXED_STRATEGY:
            final = self._ensure_legal(self._fixed_action(obs, legal_actions), legal_actions)
            trace = DecisionTrace(
                turn_number=turn_number,
                emotional_action=final,
                rational_action=final,
                final_action=final,
                emotional_intensity=0.0,
                threshold=self._threshold(),
                forced_by_emotion=False,
                override_reason="fixed_strategy",
                model_mode=self.model_mode.value,
            )
            self.last_decision = trace
            return final, trace

        emotional_action, emotional_intensity = self._heuristic_emotional_action(obs, legal_actions)
        rational_action = self._rational_action(obs, legal_actions)
        threshold = self._threshold()

        if self.kind == AgentKind.EMOTIONAL_ONLY:
            final = emotional_action
            forced = True
            reason = "emotional_only"
        elif self.kind == AgentKind.RATIONAL_ONLY:
            final = rational_action
            forced = False
            reason = "rational_only"
        elif abs(emotional_intensity) > threshold:
            final = emotional_action
            forced = True
            reason = "emotional_dominance_threshold"
        else:
            final = rational_action
            forced = False
            reason = "system2_selected"
        final = self._ensure_legal(final, legal_actions)
        emotional_action = self._ensure_legal(emotional_action, legal_actions)
        rational_action = self._ensure_legal(rational_action, legal_actions)
        trace = DecisionTrace(
            turn_number=turn_number,
            emotional_action=emotional_action,
            rational_action=rational_action,
            final_action=final,
            emotional_intensity=emotional_intensity,
            threshold=threshold,
            forced_by_emotion=forced,
            override_reason=reason,
            model_mode=self.model_mode.value,
        )
        self.last_decision = trace
        return final, trace

    def observe(self, result: GameResult, decision_trace: Optional[DecisionTrace] = None, pre_state: Optional[AgentState] = None) -> ObservationTrace:
        """Update values/state/replay once after an externally executed game round."""
        trace = decision_trace or self.last_decision
        if trace is None:
            raise ValueError("observe() requires a DecisionTrace from decide()")
        previous_values = self.values.snapshot()
        pre_state_copy = pre_state.snapshot() if isinstance(pre_state, AgentState) else self.state.snapshot()
        event_values = self.value_adapter.compute_event_values(
            game_name=result.game_name,
            focal_agent_id=result.agent_id,
            own_action=result.own_action,
            opponent_action=result.opponent_action,
            own_payoff=result.own_payoff,
            opponent_payoff=result.opponent_payoff,
            role=result.role,
        )
        appraisal_behavior_driving = self.model_mode == ModelMode.INTEGRATED_MODEL
        adapter_behavior_driving = self.model_mode == ModelMode.INTEGRATED_MODEL
        if self.model_mode == ModelMode.INTEGRATED_MODEL:
            self.values.update_from_event(event_values, alpha=0.35)
            appraisal = self.appraisal.evaluate(
                previous_values.current,
                self.values.current,
                priorities=self.values.normalized_priorities(),
                desired_values=self.values.desired,
                chunk_2=self.chunk_2,
            )
            suppression_cost = abs(trace.emotional_intensity) if trace.emotional_action != trace.final_action else 0.0
            self.state_updater.apply_appraisal(
                self.state,
                self.values,
                appraisal,
                emotional_intensity=trace.emotional_intensity,
                suppression_cost=suppression_cost,
            )
            reward_em = float(appraisal.reaction_intensity)
            reward_rm = float(self.state.overall_state - pre_state_copy.overall_state)
        else:
            # Diagnostic appraisal is reconstructed but not behavior-driving.
            simulated_current = previous_values.snapshot()
            simulated_current.update_from_event(event_values, alpha=0.35)
            appraisal = self.appraisal.evaluate(
                previous_values.current,
                simulated_current.current,
                priorities=previous_values.normalized_priorities(),
                desired_values=previous_values.desired,
                chunk_2=self.chunk_2,
            )
            max_payoff = 10.0 if "ultimatum" in result.game_name.lower() else 5.0
            self.state_updater.compatibility_update_from_payoff(self.state, self.values, result.own_payoff, max_payoff=max_payoff)
            reward_em = 0.0
            reward_rm = float(result.own_payoff)
        self.observations_count += 1
        duplicate = 0
        if self._last_observed_round == trace.turn_number:
            duplicate = 1
        self._last_observed_round = trace.turn_number
        self.last_action = result.own_action
        # Store DQN-like transitions only in observe().
        s0 = [pre_state_copy.mood, pre_state_copy.fatigue, pre_state_copy.resources, pre_state_copy.wellbeing, pre_state_copy.overall_state] + [0.0] * 9
        s1 = [self.state.mood, self.state.fatigue, self.state.resources, self.state.wellbeing, self.state.overall_state] + [0.0] * 9
        self.emotional_module.add_transition(Transition(s0, 0, reward_em, s1, meta={"forced_by_emotion": trace.forced_by_emotion}))
        self.rational_module.add_transition(Transition(s0 + [trace.threshold, trace.emotional_intensity], 0, reward_rm, s1 + [trace.threshold, trace.emotional_intensity], meta={"forced_by_emotion": trace.forced_by_emotion}))
        if self.training:
            self.emotional_module.train_step()
            self.rational_module.train_step()
        obs_trace = ObservationTrace(
            event_values=event_values,
            appraisal=appraisal,
            pre_state=pre_state_copy,
            post_state=self.state.snapshot(),
            adapter_behavior_driving=adapter_behavior_driving,
            appraisal_behavior_driving=appraisal_behavior_driving,
            transition_stored=True,
            duplicate_update_count=duplicate,
        )
        self.last_observation = obs_trace
        return obs_trace

    # Compatibility wrapper for older interactive main.py. It does not simulate a game or update state.
    def take_turn(self, turn_number: int) -> Dict[str, Any]:
        """Legacy wrapper around decide(); no internal game execution."""
        observation = GameState("Prisoners Dilemma", available_actions=get_legal_actions("Prisoners Dilemma"))
        action, trace = self.decide(observation, observation.available_actions, turn_number)
        out = trace.to_dict()
        out["action"] = action
        out["em_intensity"] = out["emotional_intensity"]
        out["em_action"] = out["emotional_action"]
        return out

    def update_from_game(self, game_result: Any) -> None:
        """Legacy wrapper for old GameResult objects when focal metadata is absent."""
        result = GameResult(
            game_name="Prisoners Dilemma",
            agent_id=1,
            role="player",
            own_action=str(getattr(game_result, "action", "cooperate")),
            opponent_action="cooperate",
            own_payoff=float(getattr(game_result, "payoff", 0.0)),
            opponent_payoff=0.0,
            game_state_after=dict(getattr(game_result, "game_state", {}) or {}),
        )
        if self.last_decision is None:
            self.last_decision = DecisionTrace(0, result.own_action, result.own_action, result.own_action, 0.0, self._threshold(), False, "legacy_update", model_mode=self.model_mode.value)
        self.observe(result, self.last_decision)

    def get_public_metrics(self) -> Dict[str, Any]:
        """Return serializable state metrics; side-effect free."""
        data = asdict(self.state)
        data.update({
            "kind": self.kind.value,
            "model_mode": self.model_mode.value,
            "observations_count": self.observations_count,
            "values": self.values.as_plain_dict(),
        })
        return data


class HybridAgent(ArchitectureAlignedAgent):
    pass


class EmotionalOnlyAgent(ArchitectureAlignedAgent):
    pass


class RationalOnlyAgent(ArchitectureAlignedAgent):
    pass


class FixedStrategyAgent(ArchitectureAlignedAgent):
    pass


def create_core_agent(
    *,
    agent_type: str,
    name: str,
    personality: str = "neutral",
    intensity: str = "neutral",
    fixed_strategy: Optional[str] = None,
    model_mode: ModelMode | str = ModelMode.REPORTED_RUNS_COMPAT,
    role: str = "player",
    training: bool = False,
) -> ArchitectureAlignedAgent:
    """Factory for architecture-aligned agents."""
    kind = _kind_from_agent_type(agent_type)
    cls = {
        AgentKind.HYBRID: HybridAgent,
        AgentKind.EMOTIONAL_ONLY: EmotionalOnlyAgent,
        AgentKind.RATIONAL_ONLY: RationalOnlyAgent,
        AgentKind.FIXED_STRATEGY: FixedStrategyAgent,
    }[kind]
    return cls(
        name=name,
        agent_type=agent_type,
        personality=personality,
        intensity=intensity,
        fixed_strategy=fixed_strategy,
        model_mode=model_mode,
        role=role,
        training=training,
    )
