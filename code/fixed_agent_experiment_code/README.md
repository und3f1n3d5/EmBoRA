# Emotionally Bounded-Rational Agents — architecture-aligned code snapshot

This package contains a corrected and documented implementation of the repeated-game emotionally bounded-rational agent pipeline. It is aligned with the article status boundary: external game outcome → game-to-values adapter → appraisal → mood/fatigue/well-being/overall state → System 1/System 2 → next action.

## What changed

The new `agent_core/` package is the architecture-aligned implementation. It introduces a strict `decide()` / `observe()` API, shared model schema, a production `GameValueAdapter`, delta-based appraisal, centralized state updates, role-specific Ultimatum Game actions, DQN-like modules, strict error policy, model modes, tests, docs and reproducible run manifests.

Legacy files (`agent_fixed.py`, `emotional_agent.py`, `rational_new.py`, `fixed_strategy_agent.py`, `main.py`) are preserved for compatibility and reference. The experiment runner now uses the architecture-aligned core so that agents do not simulate random internal games inside `take_turn()`.

## Model modes

`reported_runs_compat` preserves the article interpretation boundary: adapter/appraisal values are logged as diagnostic/explanatory variables and are not behavior-driving.

`integrated_model` implements the full target architecture: adapter/appraisal update internal values and state and therefore affect future decisions. Results in this mode are new architecture results and should not be mixed with the reported runs.

Deprecated aliases such as `paper_v10_compat` are accepted but saved as `reported_runs_compat`.

## Installation

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements_experiments_v3.txt
```

## Validation

```powershell
python -m py_compile main.py agent_fixed.py emotional_agent.py fixed_strategy_agent.py rational_new.py rational_new_corrected.py experiment_runner.py experiment_config.py experiment_utils.py experiment_metrics.py experiment_plots.py diagnostic_adapter.py agent_core\*.py
pytest -q
```

## Smoke runs

```powershell
python experiment_runner.py --scenario S0 --profile quick --games "Prisoners Dilemma" --rounds 20 --seeds-count 1 --model-mode reported_runs_compat --strict --yes
python experiment_runner.py --scenario S0 --profile quick --games "Prisoners Dilemma" --rounds 20 --seeds-count 1 --model-mode integrated_model --strict --yes
```

## Reduced standard run

```powershell
python experiment_runner.py --scenario S1 --profile standard --games all --episodes 1 --seeds-count 1 --rounds 20 --model-mode integrated_model --strict --yes
```

Each run writes `config.json`, `manifest.json`, `validation_report.md/json`, `run_log.txt`, CSV tables and figures under `experiments_output/`.

## Main files

- `agent_core/model_schema.py` — model modes, values, state, traces and scales.
- `agent_core/value_adapter.py` — production game-to-values adapter for PD/BoS/UG.
- `agent_core/appraisal.py` — delta-based ОТС/appraisal.
- `agent_core/state_updater.py` — mood/fatigue/resources/well-being/overall-state update.
- `agent_core/dqn.py` — compact DQN-like module.
- `agent_core/agents.py` — Hybrid, EmotionalOnly, RationalOnly and FixedStrategy agents.
- `experiment_runner.py` — CLI runner with strict/fallback and mode controls.
- `experiment_utils.py` — two-phase experiment loop.
- `tests/` — unit and integration tests.
- `docs/` — architecture, API, CSV schema, validation and debugging notes.
