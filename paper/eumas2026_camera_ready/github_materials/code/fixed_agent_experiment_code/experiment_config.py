#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Serializable experiment configuration and scenario builders.

The configuration separates episodes_per_condition from seed_count and stores
model_mode explicitly, as required by the architecture-aligned v11 task.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple
import json

from agent_core.model_schema import ModelMode, normalize_model_mode

AGENT_TYPES: List[str] = ["emotional_rational", "rational", "emotional", "fixed_strategy"]
PERSONALITIES: List[str] = ["optimistic", "neutral", "pessimistic"]
INTENSITIES: List[str] = ["low", "neutral", "high"]
FIXED_STRATEGIES: List[str] = ["always_cooperate", "always_defect", "tit_for_tat"]
GAMES: List[str] = ["Prisoners Dilemma", "Battle of Sexes", "Ultimatum Game"]
SCENARIOS: List[str] = ["S0", "S1", "S2", "S3", "S3B", "S4", "S5", "S6"]


@dataclass(frozen=True)
class RunProfile:
    name: str
    description: str
    default_episodes: int
    default_rounds: int
    seed_count: int


PROFILES: Dict[str, RunProfile] = {
    "quick": RunProfile("quick", "Fast import/sanity run for debugging.", 1, 20, 1),
    "standard": RunProfile("standard", "Working analysis profile.", 10, 100, 10),
    "paper": RunProfile("paper", "Paper-oriented profile.", 20, 200, 20),
}


@dataclass
class AgentSpec:
    agent_type: str
    personality: str = "neutral"
    intensity: str = "neutral"
    fixed_strategy: Optional[str] = None
    name: Optional[str] = None

    def label(self) -> str:
        chunks = [self.agent_type]
        if self.agent_type in {"emotional_rational", "emotional", "fixed_strategy"}:
            chunks.extend([self.personality, self.intensity])
        if self.agent_type == "fixed_strategy":
            chunks.append(self.fixed_strategy or "always_cooperate")
        return ":".join(chunks)

    def short_label(self) -> str:
        mapping = {
            "emotional_rational": "hybrid",
            "rational": "rational",
            "emotional": "emotional",
            "fixed_strategy": "fixed",
        }
        label = mapping.get(self.agent_type, self.agent_type)
        if self.agent_type == "fixed_strategy":
            label += f"-{self.fixed_strategy or 'always_cooperate'}"
        elif self.agent_type in {"emotional_rational", "emotional"}:
            label += f"-{self.personality}-{self.intensity}"
        return label


@dataclass
class Condition:
    condition_id: str
    scenario_name: str
    game_name: str
    agent_1: AgentSpec
    agent_2: AgentSpec
    tags: Dict[str, Any] = field(default_factory=dict)

    def pair_label(self) -> str:
        return f"{self.agent_1.short_label()}__vs__{self.agent_2.short_label()}"


@dataclass
class ExperimentConfig:
    scenario_name: str
    run_profile: str
    games: List[str]
    episodes_per_condition: int
    rounds_per_episode: int
    seed_count: int
    seeds: List[int]
    conditions: List[Condition]
    model_mode: str = ModelMode.REPORTED_RUNS_COMPAT.value
    strict: bool = False
    allow_fallback: bool = False
    output_root: str = "experiments_output"
    notes: str = ""
    save_svg: bool = False
    timestamp: Optional[str] = None

    @property
    def episodes(self) -> int:
        """Backward-compatible alias used by old scripts."""
        return self.episodes_per_condition

    @property
    def rounds(self) -> int:
        """Backward-compatible alias used by old scripts."""
        return self.rounds_per_episode

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["episodes"] = self.episodes_per_condition
        data["rounds"] = self.rounds_per_episode
        data["model_mode"] = normalize_model_mode(self.model_mode).value
        data["deprecated_aliases"] = {"paper_v10_compat": "reported_runs_compat", "paper_v11_compat": "reported_runs_compat"}
        return data

    def save(self, output_dir: Path) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / "config.json"
        path.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        return path


def normalize_profile(profile: str) -> str:
    profile = (profile or "quick").strip().lower()
    if profile not in PROFILES:
        raise ValueError(f"Unknown profile '{profile}'. Expected one of: {', '.join(PROFILES)}")
    return profile


def make_seed_list(base_seed: int, count: int) -> List[int]:
    return [int(base_seed) + i for i in range(int(count))]


def episodes_for_profile(profile: str, override: Optional[int] = None) -> int:
    return int(override) if override is not None else PROFILES[normalize_profile(profile)].default_episodes


def rounds_for_profile(profile: str, override: Optional[int] = None) -> int:
    return int(override) if override is not None else PROFILES[normalize_profile(profile)].default_rounds


def seed_count_for_profile(profile: str, override: Optional[int] = None) -> int:
    return int(override) if override is not None else PROFILES[normalize_profile(profile)].seed_count


def _default_agent(agent_type: str, *, fixed_strategy: Optional[str] = None, personality: str = "neutral", intensity: str = "neutral") -> AgentSpec:
    if agent_type == "fixed_strategy":
        return AgentSpec(agent_type=agent_type, personality=personality, intensity=intensity, fixed_strategy=fixed_strategy or "tit_for_tat")
    return AgentSpec(agent_type=agent_type, personality=personality, intensity=intensity)


def build_s0_conditions(games: Sequence[str]) -> List[Condition]:
    game = list(games)[0] if games else "Prisoners Dilemma"
    return [Condition("S0_smoke_hybrid_vs_tft", "S0", game, _default_agent("emotional_rational"), _default_agent("fixed_strategy", fixed_strategy="tit_for_tat"), {"purpose": "smoke"})]


def build_s1_conditions(games: Sequence[str], include_fixed_variants: bool = False) -> List[Condition]:
    types = ["emotional_rational", "rational", "emotional", "fixed_strategy"]
    fixed_variants = FIXED_STRATEGIES if include_fixed_variants else ["tit_for_tat"]
    conditions: List[Condition] = []
    idx = 0
    for game in games:
        for t1 in types:
            for t2 in types:
                variants1 = fixed_variants if t1 == "fixed_strategy" else [None]
                variants2 = fixed_variants if t2 == "fixed_strategy" else [None]
                for fs1 in variants1:
                    for fs2 in variants2:
                        idx += 1
                        a1, a2 = _default_agent(t1, fixed_strategy=fs1), _default_agent(t2, fixed_strategy=fs2)
                        conditions.append(Condition(f"S1_{idx:03d}_{game.replace(' ', '_')}_{a1.short_label()}__{a2.short_label()}", "S1", game, a1, a2, {"matrix": "ordered_cross_type"}))
    return conditions


def build_s2_conditions(games: Sequence[str], tested_agents: Sequence[str] = ("emotional_rational", "emotional", "rational"), fixed_strategies: Sequence[str] = tuple(FIXED_STRATEGIES)) -> List[Condition]:
    conditions: List[Condition] = []
    idx = 0
    for game in games:
        for test_type in tested_agents:
            for strategy in fixed_strategies:
                idx += 1
                conditions.append(Condition(f"S2_{idx:03d}_{game.replace(' ', '_')}_{test_type}_vs_{strategy}", "S2", game, _default_agent(test_type), _default_agent("fixed_strategy", fixed_strategy=strategy), {"tested_agent": test_type, "fixed_strategy": strategy, "hypothesis": "H1"}))
    return conditions


def build_s3_conditions(games: Sequence[str], tested_agent: str = "emotional_rational", opponents: Sequence[str] = ("always_cooperate", "always_defect", "tit_for_tat")) -> List[Condition]:
    conditions: List[Condition] = []
    idx = 0
    for game in games:
        for personality in PERSONALITIES:
            for intensity in INTENSITIES:
                for opponent in opponents:
                    idx += 1
                    conditions.append(Condition(f"S3_{idx:03d}_{game.replace(' ', '_')}_{tested_agent}_{personality}_{intensity}_vs_{opponent}", "S3", game, _default_agent(tested_agent, personality=personality, intensity=intensity), _default_agent("fixed_strategy", fixed_strategy=opponent), {"hypothesis": "H3", "sweep_cell": f"{personality}__{intensity}", "opponent": opponent}))
    return conditions


def build_s4_conditions(games: Sequence[str]) -> List[Condition]:
    templates: List[Tuple[str, AgentSpec, AgentSpec]] = [
        ("hybrid_vs_rational", _default_agent("emotional_rational"), _default_agent("rational")),
        ("hybrid_vs_always_defect", _default_agent("emotional_rational"), _default_agent("fixed_strategy", fixed_strategy="always_defect")),
        ("hybrid_vs_tit_for_tat", _default_agent("emotional_rational"), _default_agent("fixed_strategy", fixed_strategy="tit_for_tat")),
        ("emotional_vs_rational", _default_agent("emotional"), _default_agent("rational")),
    ]
    conditions: List[Condition] = []
    idx = 0
    for game in games:
        for label, a1, a2 in templates:
            idx += 1
            conditions.append(Condition(f"S4_{idx:03d}_{game.replace(' ', '_')}_{label}", "S4", game, a1, a2, {"diagnostic": "collapse", "template": label}))
    return conditions


def build_conditions(scenario: str, games: Sequence[str], **kwargs: Any) -> List[Condition]:
    scenario = scenario.upper().strip()
    if scenario == "S0":
        return build_s0_conditions(games)
    if scenario == "S1":
        return build_s1_conditions(games, include_fixed_variants=bool(kwargs.get("include_fixed_variants", False)))
    if scenario == "S2":
        return build_s2_conditions(games, kwargs.get("tested_agents", ("emotional_rational", "emotional", "rational")), kwargs.get("fixed_strategies", tuple(FIXED_STRATEGIES)))
    if scenario in {"S3", "S3B"}:
        return build_s3_conditions(games, kwargs.get("tested_agent", "emotional_rational"), kwargs.get("opponents", tuple(FIXED_STRATEGIES)))
    if scenario == "S4":
        return build_s4_conditions(games)
    if scenario in {"S5", "S6"}:
        # Explicit legacy placeholders: retained so old result directories are not unknown.
        return [Condition(f"{scenario}_legacy_exploratory_placeholder", scenario, list(games)[0] if games else "Prisoners Dilemma", _default_agent("emotional_rational"), _default_agent("rational"), {"legacy": True, "interpretation": "exploratory/archived"})]
    raise ValueError(f"Unknown scenario '{scenario}'. Expected one of: {', '.join(SCENARIOS)}")


def make_config(
    scenario: str,
    profile: str,
    games: Sequence[str],
    *,
    episodes: Optional[int] = None,
    rounds: Optional[int] = None,
    seeds_count: Optional[int] = None,
    base_seed: int = 20260430,
    output_root: str = "experiments_output",
    notes: str = "",
    save_svg: bool = False,
    model_mode: str = ModelMode.REPORTED_RUNS_COMPAT.value,
    strict: bool = False,
    allow_fallback: bool = False,
    **condition_kwargs: Any,
) -> ExperimentConfig:
    profile = normalize_profile(profile)
    scenario = scenario.upper().strip()
    games = list(games) or ["Prisoners Dilemma"]
    episodes_value = episodes_for_profile(profile, episodes)
    rounds_value = rounds_for_profile(profile, rounds)
    seed_count_value = seed_count_for_profile(profile, seeds_count)
    seeds = make_seed_list(base_seed, seed_count_value)
    conditions = build_conditions(scenario, games, **condition_kwargs)
    return ExperimentConfig(
        scenario_name=scenario,
        run_profile=profile,
        games=games,
        episodes_per_condition=episodes_value,
        rounds_per_episode=rounds_value,
        seed_count=seed_count_value,
        seeds=seeds,
        conditions=conditions,
        model_mode=normalize_model_mode(model_mode).value,
        strict=bool(strict),
        allow_fallback=bool(allow_fallback),
        output_root=output_root,
        notes=notes,
        save_svg=save_svg,
    )
