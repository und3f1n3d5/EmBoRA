#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuration models and scenario builders for v3 experiments.

This file intentionally does not import project agent/game modules. It contains
only serializable configuration structures used by experiment_runner.py.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple
import json


AGENT_TYPES: List[str] = [
    "emotional_rational",
    "rational",
    "emotional",
    "fixed_strategy",
]

PERSONALITIES: List[str] = ["optimistic", "neutral", "pessimistic"]
INTENSITIES: List[str] = ["low", "neutral", "high"]
FIXED_STRATEGIES: List[str] = ["always_cooperate", "always_defect", "tit_for_tat"]
GAMES: List[str] = ["Prisoners Dilemma", "Battle of Sexes", "Ultimatum Game"]
SCENARIOS: List[str] = ["S0", "S1", "S2", "S3", "S4"]


@dataclass(frozen=True)
class RunProfile:
    name: str
    description: str
    default_episodes: int
    default_rounds: int
    seed_count: int


PROFILES: Dict[str, RunProfile] = {
    "quick": RunProfile(
        name="quick",
        description="Fast import/sanity run for debugging.",
        default_episodes=2,
        default_rounds=25,
        seed_count=2,
    ),
    "standard": RunProfile(
        name="standard",
        description="Working analysis profile: at least 10 episodes per condition.",
        default_episodes=10,
        default_rounds=100,
        seed_count=10,
    ),
    "paper": RunProfile(
        name="paper",
        description="Paper-oriented profile: at least 20 episodes per condition.",
        default_episodes=20,
        default_rounds=200,
        seed_count=20,
    ),
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
    episodes: int
    rounds: int
    seeds: List[int]
    conditions: List[Condition]
    output_root: str = "experiments_output"
    notes: str = ""
    save_svg: bool = False
    timestamp: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def save(self, output_dir: Path) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / "config.json"
        with path.open("w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
        return path


def normalize_profile(profile: str) -> str:
    profile = (profile or "quick").strip().lower()
    if profile not in PROFILES:
        raise ValueError(f"Unknown profile '{profile}'. Expected one of: {', '.join(PROFILES)}")
    return profile


def make_seed_list(base_seed: int, count: int) -> List[int]:
    return [int(base_seed) + i for i in range(int(count))]


def episodes_for_profile(profile: str, override: Optional[int] = None) -> int:
    if override is not None:
        return int(override)
    return PROFILES[normalize_profile(profile)].default_episodes


def rounds_for_profile(profile: str, override: Optional[int] = None) -> int:
    if override is not None:
        return int(override)
    return PROFILES[normalize_profile(profile)].default_rounds


def seeds_for_profile(profile: str, base_seed: int = 20260430, override_episodes: Optional[int] = None) -> List[int]:
    profile_obj = PROFILES[normalize_profile(profile)]
    count = int(override_episodes) if override_episodes is not None else profile_obj.seed_count
    return make_seed_list(base_seed, count)


def _default_agent(agent_type: str, *, fixed_strategy: Optional[str] = None,
                   personality: str = "neutral", intensity: str = "neutral") -> AgentSpec:
    if agent_type == "fixed_strategy":
        return AgentSpec(agent_type=agent_type, personality=personality, intensity=intensity,
                         fixed_strategy=fixed_strategy or "tit_for_tat")
    return AgentSpec(agent_type=agent_type, personality=personality, intensity=intensity)


def build_s0_conditions(games: Sequence[str]) -> List[Condition]:
    game = list(games)[0] if games else "Prisoners Dilemma"
    return [Condition(
        condition_id="S0_smoke_hybrid_vs_tft",
        scenario_name="S0",
        game_name=game,
        agent_1=_default_agent("emotional_rational"),
        agent_2=_default_agent("fixed_strategy", fixed_strategy="tit_for_tat"),
        tags={"purpose": "smoke"},
    )]


def build_s1_conditions(games: Sequence[str], include_fixed_variants: bool = False) -> List[Condition]:
    """Full homogeneous and cross-type matrix for all requested games.

    By default fixed_strategy is represented by tit_for_tat to keep the matrix
    compact. If include_fixed_variants=True, every fixed-strategy cell is
    expanded across all fixed baselines.
    """
    types = ["emotional_rational", "rational", "emotional", "fixed_strategy"]
    conditions: List[Condition] = []
    idx = 0
    fixed_variants = FIXED_STRATEGIES if include_fixed_variants else ["tit_for_tat"]
    for game in games:
        for t1 in types:
            for t2 in types:
                variants1 = fixed_variants if t1 == "fixed_strategy" else [None]
                variants2 = fixed_variants if t2 == "fixed_strategy" else [None]
                for fs1 in variants1:
                    for fs2 in variants2:
                        idx += 1
                        a1 = _default_agent(t1, fixed_strategy=fs1)
                        a2 = _default_agent(t2, fixed_strategy=fs2)
                        conditions.append(Condition(
                            condition_id=f"S1_{idx:03d}_{game.replace(' ', '_')}_{a1.short_label()}__{a2.short_label()}",
                            scenario_name="S1",
                            game_name=game,
                            agent_1=a1,
                            agent_2=a2,
                            tags={"matrix": "ordered_cross_type"},
                        ))
    return conditions


def build_s2_conditions(games: Sequence[str], tested_agents: Sequence[str] = ("emotional_rational", "emotional", "rational"),
                        fixed_strategies: Sequence[str] = tuple(FIXED_STRATEGIES)) -> List[Condition]:
    conditions: List[Condition] = []
    idx = 0
    for game in games:
        for test_type in tested_agents:
            for strategy in fixed_strategies:
                idx += 1
                conditions.append(Condition(
                    condition_id=f"S2_{idx:03d}_{game.replace(' ', '_')}_{test_type}_vs_{strategy}",
                    scenario_name="S2",
                    game_name=game,
                    agent_1=_default_agent(test_type),
                    agent_2=_default_agent("fixed_strategy", fixed_strategy=strategy),
                    tags={"tested_agent": test_type, "fixed_strategy": strategy, "hypothesis": "H1"},
                ))
    return conditions


def build_s3_conditions(games: Sequence[str], tested_agent: str = "emotional_rational",
                        opponents: Sequence[str] = ("always_cooperate", "always_defect", "tit_for_tat")) -> List[Condition]:
    conditions: List[Condition] = []
    idx = 0
    for game in games:
        for personality in PERSONALITIES:
            for intensity in INTENSITIES:
                for opponent in opponents:
                    idx += 1
                    conditions.append(Condition(
                        condition_id=(
                            f"S3_{idx:03d}_{game.replace(' ', '_')}_"
                            f"{tested_agent}_{personality}_{intensity}_vs_{opponent}"
                        ),
                        scenario_name="S3",
                        game_name=game,
                        agent_1=_default_agent(tested_agent, personality=personality, intensity=intensity),
                        agent_2=_default_agent("fixed_strategy", fixed_strategy=opponent),
                        tags={"hypothesis": "H3", "sweep_cell": f"{personality}__{intensity}", "opponent": opponent},
                    ))
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
            conditions.append(Condition(
                condition_id=f"S4_{idx:03d}_{game.replace(' ', '_')}_{label}",
                scenario_name="S4",
                game_name=game,
                agent_1=a1,
                agent_2=a2,
                tags={"diagnostic": "collapse", "template": label},
            ))
    return conditions


def build_conditions(scenario: str, games: Sequence[str], **kwargs: Any) -> List[Condition]:
    scenario = scenario.upper().strip()
    if scenario == "S0":
        return build_s0_conditions(games)
    if scenario == "S1":
        return build_s1_conditions(games, include_fixed_variants=bool(kwargs.get("include_fixed_variants", False)))
    if scenario == "S2":
        return build_s2_conditions(
            games,
            tested_agents=kwargs.get("tested_agents", ("emotional_rational", "emotional", "rational")),
            fixed_strategies=kwargs.get("fixed_strategies", tuple(FIXED_STRATEGIES)),
        )
    if scenario == "S3":
        return build_s3_conditions(
            games,
            tested_agent=kwargs.get("tested_agent", "emotional_rational"),
            opponents=kwargs.get("opponents", tuple(FIXED_STRATEGIES)),
        )
    if scenario == "S4":
        return build_s4_conditions(games)
    raise ValueError(f"Unknown scenario '{scenario}'. Expected one of: {', '.join(SCENARIOS)}")


def make_config(scenario: str, profile: str, games: Sequence[str], *, episodes: Optional[int] = None,
                rounds: Optional[int] = None, base_seed: int = 20260430, output_root: str = "experiments_output",
                notes: str = "", save_svg: bool = False, **condition_kwargs: Any) -> ExperimentConfig:
    profile = normalize_profile(profile)
    scenario = scenario.upper().strip()
    games = list(games) or ["Prisoners Dilemma"]
    episodes_value = episodes_for_profile(profile, episodes)
    rounds_value = rounds_for_profile(profile, rounds)
    seeds = make_seed_list(base_seed, episodes_value)
    conditions = build_conditions(scenario, games, **condition_kwargs)
    return ExperimentConfig(
        scenario_name=scenario,
        run_profile=profile,
        games=games,
        episodes=episodes_value,
        rounds=rounds_value,
        seeds=seeds,
        conditions=conditions,
        output_root=output_root,
        notes=notes,
        save_svg=save_svg,
    )
