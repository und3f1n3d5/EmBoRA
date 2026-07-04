# CHANGELOG_FIXES

## Completed fixes against the architecture-alignment ТЗ

1. **Separated decision and observation.** Production experiments now use `agent.decide()` and `agent.observe()`; the external game is executed exactly once by the runner.
2. **Removed behavior-driving internal random game.** The new core agents do not call an internal `GameAdapter.execute_game_action()` in `decide()`.
3. **Added `ModelMode`.** `reported_runs_compat` and `integrated_model` are saved into configs, CSVs and manifests. Deprecated aliases are normalized.
4. **Introduced production `GameValueAdapter`.** It implements focal-agent arguments and returns material/fairness/relationship/safety for PD, BoS and UG.
5. **Implemented delta-based appraisal.** Positive value deltas produce positive reactions; negative deltas produce negative reactions; neutral deltas produce zero reaction.
6. **Centralized state update.** Mood, fatigue, resources, well-being and overall state are updated in `StateUpdater` with explicit scales.
7. **Fixed well-being semantics.** Well-being is weighted value satisfaction and does not depend on enum/dict traversal order.
8. **Separated agent kinds.** Factory creates hybrid, emotional-only, rational-only and fixed-strategy agents with clear final-action logic.
9. **Added truthful decision diagnostics.** `forced_by_emotion`, threshold, emotional/rational/final actions and override reason are stored in traces and CSV.
10. **Added UG role-specific action spaces.** Proposer gets offer grid; responder gets accept/reject.
11. **Separated `episodes_per_condition` and `seed_count`.** CLI supports `--episodes` and `--seeds-count` independently.
12. **Added strict error policy.** `--strict` raises on errors; fallback only works with `--allow-fallback` in non-strict debug runs.
13. **Added S5/S6 handling.** They are explicit legacy placeholders and cannot silently appear as unknown scenario IDs.
14. **Added validation and manifests.** Every run contains config, manifest, validation report, CSV and plots.
15. **Added tests and docs.** `pytest -q` passes 15 tests.

## Main changed/added files

- Added: `agent_core/__init__.py`, `model_schema.py`, `value_adapter.py`, `appraisal.py`, `state_updater.py`, `dqn.py`, `agents.py`.
- Rewritten: `experiment_config.py`, `experiment_utils.py`, `experiment_runner.py`, `diagnostic_adapter.py`.
- Patched: `experiment_metrics.py`, `requirements_experiments_v3.txt`.
- Added: `tests/`, `docs/`, `examples/minimal_run.py`, `pytest_report.txt`.

## Compatibility and migration

Use old files only as legacy references. Use `experiment_runner.py` and `agent_core/` for new experiments. Use `reported_runs_compat` for v11-compatible diagnostics and `integrated_model` for new architecture experiments.
