Experiment run log
==================
scenario_name: S0
run_profile: quick
model_mode: reported_runs_compat
games: Prisoners Dilemma
episodes_per_condition: 1
rounds_per_episode: 10
seed_count: 1
seeds: [20260430]
conditions: 1
strict: True
allow_fallback: False

Artifacts:
- round_level: round_level.csv
- episode_level: episode_level.csv
- summary_by_condition: summary_by_condition.csv
- summary_for_paper: summary_for_paper.csv
- adaptation_summary: adaptation_summary.csv
- collapse_diagnostics: collapse_diagnostics.csv
- plots: plots/
- manifest: manifest.json
- validation: validation_report.md/json

Interpretation guardrail:
reported_runs_compat: adapter/appraisal columns are diagnostic/explanatory and reproduce the article-v11 status boundary.
Fixed-strategy semantics are cleanest in PD; BoS/UG fixed-strategy rows are stress tests unless explicitly redesigned.

Validation summary:
{
  "run_dir": "/mnt/data/work_isdg/final_runs/20260521_093848_quick_S0_reported_runs_compat",
  "missing_files": [],
  "round_rows": 10,
  "episode_rows": 1,
  "mood_out_of_range": 0,
  "fatigue_out_of_range": 0,
  "nan_or_inf_cells": 0,
  "duplicate_observe_count": 0,
  "fallback_rows": 0,
  "passed": true
}