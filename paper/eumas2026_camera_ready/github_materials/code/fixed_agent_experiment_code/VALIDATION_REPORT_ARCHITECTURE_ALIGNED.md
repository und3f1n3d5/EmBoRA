# Architecture-aligned validation report

## Static checks

`python -m py_compile` was run for:

- legacy entry/modules: `main.py`, `agent_fixed.py`, `emotional_agent.py`, `fixed_strategy_agent.py`, `rational_new.py`, `rational_new_corrected.py`;
- experiment modules: `experiment_runner.py`, `experiment_config.py`, `experiment_utils.py`, `experiment_metrics.py`, `experiment_plots.py`, `diagnostic_adapter.py`;
- new core modules: `agent_core/*.py`;
- example: `examples/minimal_run.py`.

Result: passed.

## Tests

`pytest -q` result is saved in `pytest_report.txt`.

Summary: 15 tests passed.

## Smoke and reduced-standard runs included

The folder `validation_runs/` contains:

1. `quick_S0_reported_runs_compat`: strict smoke run for the article-v11 compatibility mode.
2. `quick_S0_integrated_model`: strict smoke run for the behavior-driving integrated model.
3. `standard_S1_integrated_model`: reduced standard matrix, all three games, 48 ordered conditions, 20 rounds, 1 seed.

All included runs have `validation_report.json` with `passed: true`, no fallback rows, no duplicate observe updates, no out-of-range mood/fatigue and no NaN/inf cells.
