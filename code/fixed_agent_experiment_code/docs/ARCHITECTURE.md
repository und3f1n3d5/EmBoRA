# Architecture

## Research hypothesis

The project studies whether over-rationalized agents are insufficient for repeated social interaction and whether emotionally bounded-rational agents expose divergences between payoff, social interpretation and internal state.

## Closed loop

The target loop is:

```text
external game outcome
  -> GameValueAdapter(material, fairness, relationship, safety)
  -> CurrentStateEvaluation / appraisal(delta, urgency, valence, load, focus)
  -> StateUpdater(mood, fatigue, resources, well-being, overall state)
  -> System 1 affective proposal + System 2 threshold/override/refocus
  -> next external action
```

The experiment loop enforces:

```text
pre_state = agent.snapshot_before_decision()
action, decision_trace = agent.decide(observation, legal_actions, turn)
outcome = game.execute_round(action_1, action_2)
agent.observe(real_game_result, decision_trace, pre_state)
```

No production `decide()` method executes a random internal game or updates values/state.

## Game-to-values adapter

The adapter maps a focal-agent event into four values in `[0,1]`:

- `material`: own payoff normalized by feasible payoff range;
- `fairness`: symmetry proxy `1 - |normalized_own - normalized_other|`;
- `relationship`: how supportive the observed partner action was given the focal action;
- `safety`: inverse normalized regret/no-regret vulnerability proxy.

The adapter API is focal-agent oriented: `game_name`, `focal_agent_id`, `own_action`, `opponent_action`, `own_payoff`, `opponent_payoff`, `role`.

## Appraisal / ОТС

Appraisal compares `previous_values` and `current_values`. Positive deltas produce positive signed urgency; negative deltas produce negative signed urgency. Gains are normalized by distance remaining to the desired value; losses are normalized by what had already been attained. This fixes the previous failure mode where a positive improvement below the ideal was treated as negative.

`chunk_2` scales reaction intensity without changing sign.

## State variables

- `mood`: `[-0.5, 0.5]`;
- `fatigue`: `[0,1]`;
- `resources`: `[0,1]`, currently `1 - fatigue`;
- `wellbeing`: weighted value satisfaction `[0,1]`;
- `reported_wellbeing`: `2 * wellbeing - 1`;
- `overall_state`: `lambda_w * reported_wellbeing + lambda_m * mood - lambda_f * fatigue`.

## System 1 and System 2

System 1 is the affective proposal mechanism. It returns an emotional action and a signed intensity. System 2 computes a rational proposal and uses a fatigue-dependent threshold:

```text
theta = clip(theta0 * (1 - lambda_f * fatigue) + mood_modifier + resource_modifier, theta_min, theta_max)
```

There are no negative production thresholds. In `emotional` agents the final action is the System 1 action. In `rational` agents the emotional module may be logged, but final action is rational. In `hybrid` agents System 1 can dominate only when `abs(intensity) > threshold`.

## Refocus

Refocus is treated as an internal control option and diagnostic extension point, not as a hidden external game action. The current production runner does not consume a game round for refocus.

## Two model modes

`reported_runs_compat` reproduces the conservative v11 boundary: adapter/appraisal columns are diagnostics.

`integrated_model` is the new behavior-driving architecture: event values are smoothed into internal values, appraisal updates state, and state affects later decisions.
