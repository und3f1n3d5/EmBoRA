# API reference

## AgentProtocol-style API

```python
action, decision_trace = agent.decide(observation, legal_actions, turn_number)
observation_trace = agent.observe(result, decision_trace, pre_state)
agent.reset_episode(seed)
metrics = agent.get_public_metrics()
```

`decide()` has no side effects on values, state or replay buffers. `observe()` is the only production state update and transition-storage point.

## GameResult

`GameResult` contains `game_name`, `agent_id`, `role`, `own_action`, `opponent_action`, `own_payoff`, `opponent_payoff`, `game_state_after` and optional `raw_outcome`.

## DecisionTrace

Fields: `turn_number`, `emotional_action`, `rational_action`, `final_action`, `emotional_intensity`, `threshold`, `forced_by_emotion`, `override_reason`, `action_type`, `model_mode`.

## ObservationTrace

Fields include event values, appraisal result, pre/post state snapshots, behavior-driving flags, transition flag and duplicate-update count.

## GameValueAdapter

```python
adapter.compute_event_values(
    game_name="Prisoners Dilemma",
    focal_agent_id=1,
    own_action="cooperate",
    opponent_action="defect",
    own_payoff=0,
    opponent_payoff=5,
    role="player",
)
```

Returns a dict keyed by `ValueType`: material, fairness, relationship and safety in `[0,1]`.

## ExperimentConfig

Important fields: `scenario_name`, `run_profile`, `episodes_per_condition`, `rounds_per_episode`, `seed_count`, `seeds`, `model_mode`, `strict`, `allow_fallback`, `conditions`.
