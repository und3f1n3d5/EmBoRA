#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared model schema and numeric scales.

This module is the single source of truth for model modes, agent kinds, value
names and the numeric ranges used by the architecture-aligned implementation.
All public dataclasses document whether they are side-effect free. Containers
are mutable only where explicitly stated by the agent/state update loop.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Mapping, Optional
import math

MOOD_MIN = -0.5
MOOD_MAX = 0.5
FATIGUE_MIN = 0.0
FATIGUE_MAX = 1.0
RESOURCE_MIN = 0.0
RESOURCE_MAX = 1.0
VALUE_MIN = 0.0
VALUE_MAX = 1.0
WELLBEING_MIN = 0.0
WELLBEING_MAX = 1.0
REPORTED_WELLBEING_MIN = -1.0
REPORTED_WELLBEING_MAX = 1.0
EMOTION_MIN = -1.5
EMOTION_MAX = 1.5
PRIORITY_MIN = 0.5
PRIORITY_MAX = 1.5


def finite_float(value: Any, default: float = 0.0) -> float:
    """Return a finite float or *default*; side-effect free."""
    try:
        v = float(value)
    except Exception:
        return default
    if math.isnan(v) or math.isinf(v):
        return default
    return v


def clip(value: Any, low: float, high: float) -> float:
    """Clip a numeric value into [low, high]; side-effect free."""
    v = finite_float(value, low)
    return max(low, min(high, v))


def clip01(value: Any) -> float:
    """Clip a numeric value into [0, 1]; side-effect free."""
    return clip(value, 0.0, 1.0)


class ModelMode(str, Enum):
    """Experiment/model semantics.

    REPORTED_RUNS_COMPAT reproduces the status boundary of article v11:
    adapter/appraisal variables are logged diagnostics. INTEGRATED_MODEL makes
    the adapter/appraisal layer behavior-driving through observe().
    """

    REPORTED_RUNS_COMPAT = "reported_runs_compat"
    INTEGRATED_MODEL = "integrated_model"


DEPRECATED_MODEL_MODE_ALIASES = {
    "paper_v10_compat": ModelMode.REPORTED_RUNS_COMPAT,
    "paper_v11_compat": ModelMode.REPORTED_RUNS_COMPAT,
    "paper": ModelMode.REPORTED_RUNS_COMPAT,
}


def normalize_model_mode(value: Any) -> ModelMode:
    """Normalize CLI/config aliases to a ModelMode; side-effect free."""
    if isinstance(value, ModelMode):
        return value
    text = str(value or ModelMode.REPORTED_RUNS_COMPAT.value).strip().lower()
    if text in DEPRECATED_MODEL_MODE_ALIASES:
        return DEPRECATED_MODEL_MODE_ALIASES[text]
    try:
        return ModelMode(text)
    except ValueError as exc:
        allowed = ", ".join([m.value for m in ModelMode] + list(DEPRECATED_MODEL_MODE_ALIASES))
        raise ValueError(f"Unknown model mode '{value}'. Expected one of: {allowed}") from exc


class AgentKind(str, Enum):
    """Production agent families used by create_core_agent()."""

    HYBRID = "hybrid"
    EMOTIONAL_ONLY = "emotional"
    RATIONAL_ONLY = "rational"
    FIXED_STRATEGY = "fixed"


class ValueType(str, Enum):
    """Shared internal value dimensions, all stored on the [0, 1] scale."""

    MATERIAL = "material"
    FAIRNESS = "fairness"
    RELATIONSHIP = "relationship"
    SAFETY = "safety"


VALUE_TYPES: List[ValueType] = [
    ValueType.MATERIAL,
    ValueType.FAIRNESS,
    ValueType.RELATIONSHIP,
    ValueType.SAFETY,
]


@dataclass(frozen=True)
class ActionOption:
    """Legal game action.

    Side effects: none. The string representation is the form passed to the game
    engine, for example ``offer(offer=5.00)``.
    """

    name: str
    params: Dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        if not self.params:
            return self.name
        pieces = []
        for key, value in self.params.items():
            if isinstance(value, float):
                pieces.append(f"{key}={value:.2f}")
            else:
                pieces.append(f"{key}={value}")
        return f"{self.name}(" + ", ".join(pieces) + ")"

    @classmethod
    def from_any(cls, value: Any) -> "ActionOption":
        """Build an ActionOption from a str/dict/ActionOption; side-effect free."""
        if isinstance(value, ActionOption):
            return value
        if isinstance(value, Mapping):
            return cls(str(value.get("name", "")), dict(value.get("params", {}) or {}))
        text = str(value)
        if "(" not in text:
            return cls(text)
        name = text.split("(", 1)[0]
        raw = text.split("(", 1)[1].rstrip(")")
        params: Dict[str, Any] = {}
        for part in raw.split(","):
            if "=" not in part:
                continue
            key, val = part.split("=", 1)
            key = key.strip()
            val = val.strip()
            try:
                params[key] = float(val)
            except ValueError:
                params[key] = val
        return cls(name.strip(), params)


@dataclass(frozen=True)
class GameState:
    """Observation passed to decide(); side-effect free for agents."""

    game_name: str
    game_parameters: Dict[str, float] = field(default_factory=dict)
    available_actions: List[ActionOption] = field(default_factory=list)
    role: str = "player"
    agent_id: int = 1
    opponent_last_action: Optional[str] = None


@dataclass(frozen=True)
class GameResult:
    """External outcome consumed by observe(); side-effect free container.

    The result is created by the experiment loop after ``game.execute_round``;
    agents must not construct random outcomes inside decide().
    """

    game_name: str
    agent_id: int
    role: str
    own_action: str
    opponent_action: str
    own_payoff: float
    opponent_payoff: float
    game_state_after: Dict[str, float] = field(default_factory=dict)
    raw_outcome: Any = None


@dataclass
class Values:
    """Mutable internal values in [0, 1].

    Side effects: update_from_event mutates previous/current values by smoothing
    event values with alpha. Use snapshot() for immutable comparisons.
    """

    current: Dict[ValueType, float] = field(default_factory=lambda: {vt: 0.5 for vt in VALUE_TYPES})
    previous: Dict[ValueType, float] = field(default_factory=lambda: {vt: 0.5 for vt in VALUE_TYPES})
    desired: Dict[ValueType, float] = field(default_factory=lambda: {vt: 1.0 for vt in VALUE_TYPES})
    priorities: Dict[ValueType, float] = field(default_factory=lambda: {vt: 1.0 for vt in VALUE_TYPES})

    def snapshot(self) -> "Values":
        """Return a deep-enough copy for pre/post comparisons; side-effect free."""
        return Values(
            current=dict(self.current),
            previous=dict(self.previous),
            desired=dict(self.desired),
            priorities=dict(self.priorities),
        )

    def update_from_event(self, event_values: Mapping[ValueType | str, float], alpha: float = 0.35) -> None:
        """Smooth event values into internal values; mutates this object."""
        self.previous = dict(self.current)
        a = clip01(alpha)
        for vt in VALUE_TYPES:
            raw = event_values.get(vt, event_values.get(vt.value, self.current.get(vt, 0.5)))  # type: ignore[arg-type]
            q = clip01(raw)
            self.current[vt] = clip01((1.0 - a) * self.current.get(vt, 0.5) + a * q)

    def normalized_priorities(self) -> Dict[ValueType, float]:
        """Return priorities normalized to sum 1; side-effect free."""
        clipped = {vt: clip(v, PRIORITY_MIN, PRIORITY_MAX) for vt, v in self.priorities.items()}
        total = sum(clipped.values()) or 1.0
        return {vt: val / total for vt, val in clipped.items()}

    def as_plain_dict(self) -> Dict[str, Dict[str, float]]:
        """Serialize values using string keys; side-effect free."""
        return {
            "current": {vt.value: float(self.current.get(vt, 0.0)) for vt in VALUE_TYPES},
            "previous": {vt.value: float(self.previous.get(vt, 0.0)) for vt in VALUE_TYPES},
            "desired": {vt.value: float(self.desired.get(vt, 1.0)) for vt in VALUE_TYPES},
            "priorities": {vt.value: float(self.priorities.get(vt, 1.0)) for vt in VALUE_TYPES},
        }


@dataclass
class AgentState:
    """Mutable affective-cognitive state.

    Scales: mood [-0.5,0.5], fatigue/resources [0,1], wellbeing [0,1],
    reported_wellbeing [-1,1], overall_state roughly [-1.5,1.5].
    """

    mood: float = 0.0
    fatigue: float = 0.0
    resources: float = 1.0
    wellbeing: float = 0.5
    reported_wellbeing: float = 0.0
    overall_state: float = 0.5
    refocus_count: int = 0
    total_refocus_count: int = 0

    def clamp(self) -> None:
        """Clamp all state fields in place; mutates this object."""
        self.mood = clip(self.mood, MOOD_MIN, MOOD_MAX)
        self.fatigue = clip(self.fatigue, FATIGUE_MIN, FATIGUE_MAX)
        self.resources = clip(self.resources, RESOURCE_MIN, RESOURCE_MAX)
        self.wellbeing = clip(self.wellbeing, WELLBEING_MIN, WELLBEING_MAX)
        self.reported_wellbeing = clip(2.0 * self.wellbeing - 1.0, REPORTED_WELLBEING_MIN, REPORTED_WELLBEING_MAX)
        self.overall_state = finite_float(self.overall_state, 0.0)

    def snapshot(self) -> "AgentState":
        """Return a copy for side-effect checks; side-effect free."""
        return AgentState(**asdict(self))

    def calculate_overall_state(self) -> float:
        """Compatibility method used by old metrics; side-effect free."""
        return float(self.overall_state)


@dataclass(frozen=True)
class AppraisalResult:
    """Side-effect-free output of CurrentStateEvaluation."""

    value_delta: Dict[ValueType, float]
    urgency: Dict[ValueType, float]
    signed_urgency: Dict[ValueType, float]
    valence: float
    emotional_load: float
    attention_focus: Optional[ValueType]
    reaction_intensity: float


@dataclass(frozen=True)
class DecisionTrace:
    """Decision diagnostics returned by decide(); side-effect free container."""

    turn_number: int
    emotional_action: str
    rational_action: str
    final_action: str
    emotional_intensity: float
    threshold: float
    forced_by_emotion: bool
    override_reason: str
    action_type: str = "game_action"
    model_mode: str = ModelMode.REPORTED_RUNS_COMPAT.value

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ObservationTrace:
    """Observation/update diagnostics returned by observe(); side-effect free container."""

    event_values: Dict[ValueType, float]
    appraisal: AppraisalResult
    pre_state: AgentState
    post_state: AgentState
    adapter_behavior_driving: bool
    appraisal_behavior_driving: bool
    transition_stored: bool
    duplicate_update_count: int = 0

    def to_plain_dict(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {
            "adapter_behavior_driving": self.adapter_behavior_driving,
            "appraisal_behavior_driving": self.appraisal_behavior_driving,
            "transition_stored": self.transition_stored,
            "duplicate_update_count": self.duplicate_update_count,
        }
        for vt, value in self.event_values.items():
            out[f"event_{vt.value}"] = float(value)
            out[f"delta_{vt.value}"] = float(self.appraisal.value_delta.get(vt, 0.0))
            out[f"signed_urgency_{vt.value}"] = float(self.appraisal.signed_urgency.get(vt, 0.0))
            out[f"urgency_{vt.value}"] = float(self.appraisal.urgency.get(vt, 0.0))
        out["valence"] = float(self.appraisal.valence)
        out["emotional_load"] = float(self.appraisal.emotional_load)
        out["attention_focus"] = self.appraisal.attention_focus.value if self.appraisal.attention_focus else "none"
        out["reaction_intensity"] = float(self.appraisal.reaction_intensity)
        return out
