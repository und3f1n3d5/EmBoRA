# CSV schema

## round_level.csv

Key fields:

- run identity: `scenario_name`, `condition_id`, `condition_label`, `game_name`, `run_profile`, `model_mode`;
- status flags: `mechanism_status`, `adapter_behavior_driving`, `appraisal_behavior_driving`;
- focal outcome API: `focal_agent_id_1/2`, `role_1/2`, `own_action_1/2`, `opponent_action_1/2`, `own_payoff_1/2`, `opponent_payoff_1/2`;
- state: `mood_1/2`, `wellbeing_1/2`, `reported_wellbeing_1/2`, `fatigue_1/2`, `resources_1/2`, `overall_state_1/2`;
- decision trace: `agent_i_emotional_action`, `agent_i_rational_action`, `agent_i_final_action`, `agent_i_emotional_intensity`, `agent_i_threshold`, `agent_i_forced_by_emotion`, `agent_i_override_reason`;
- adapter/appraisal: `agent_i_event_material`, `agent_i_event_fairness`, `agent_i_event_relationship`, `agent_i_event_safety`, `agent_i_delta_*`, `agent_i_signed_urgency_*`, `agent_i_valence`, `agent_i_emotional_load`, `agent_i_attention_focus`, `agent_i_reaction_intensity`;
- validation: `fallback_used`, `errors_count_so_far`, `agent_i_duplicate_update_count`.

## episode_level.csv

One row per condition/seed episode with payoff, game-specific metrics, internal-state means/finals, errors and fallback flags.

## summary_by_condition.csv

Aggregates `episode_level.csv` by scenario/game/mode/condition and reports means/std/medians.

## summary_for_paper.csv

Compact descriptive table. It includes guardrails that v11 compatible diagnostics and integrated-model outputs must not be mixed.

## adaptation_summary.csv

First-third vs last-third adaptation proxies.

## collapse_diagnostics.csv

State range/slope and payoff-state correlation diagnostics.
