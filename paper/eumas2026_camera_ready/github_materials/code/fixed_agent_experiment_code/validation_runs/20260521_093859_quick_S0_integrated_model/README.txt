Experiment run log
==================
scenario_name: S0
run_profile: quick
model_mode: integrated_model
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
integrated_model: adapter/appraisal are behavior-driving; results belong to the new architecture and must not be mixed with v11 reported runs.
Fixed-strategy semantics are cleanest in PD; BoS/UG fixed-strategy rows are stress tests unless explicitly redesigned.

Validation summary:
{
  "run_dir": "/mnt/data/work_isdg/final_runs/20260521_093859_quick_S0_integrated_model",
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