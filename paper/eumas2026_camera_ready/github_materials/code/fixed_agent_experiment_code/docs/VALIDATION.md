# Validation

## Unit and integration tests

Run:

```powershell
pytest -q
```

The test suite covers delta-based appraisal, PD/BoS/UG adapter outputs, `decide()` side effects, one `observe()` per agent per round, order-invariant well-being, non-negative thresholds, UG role-specific actions, forced-by-emotion logging, strict mode and model-mode status flags.

## Syntax checks

```powershell
python -m py_compile main.py agent_fixed.py emotional_agent.py fixed_strategy_agent.py rational_new.py rational_new_corrected.py experiment_runner.py experiment_config.py experiment_utils.py experiment_metrics.py experiment_plots.py diagnostic_adapter.py agent_core\*.py
```

## Smoke-run validation

Each run writes `validation_report.md/json`. Key invariants:

- mood is in `[-0.5, 0.5]`;
- fatigue is in `[0,1]`;
- no NaN/inf cells in CSV;
- duplicate observe count is zero;
- strict runs have no fallback rows;
- required artifacts exist.

## Reading negative-state share

Negative state is a diagnostic indicator, not automatic failure. Check value deltas, reaction intensity, fatigue, fallback, duplicate observe and adapter status before interpreting it.

## Ablations

The current code is ready for future flags such as `no_mood`, `no_fatigue`, `no_refocus`, `no_adapter_behavior`, `fixed_threshold`, and `no_learning`. These should be added as explicit config fields, not silent code edits.
