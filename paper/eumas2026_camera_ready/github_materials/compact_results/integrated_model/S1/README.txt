Experiment run log
==================
scenario_name: S1
run_profile: paper
model_mode: integrated_model
games: Prisoners Dilemma, Battle of Sexes, Ultimatum Game
episodes_per_condition: 20
rounds_per_episode: 200
seed_count: 20
seeds: [20260430, 20260431, 20260432, 20260433, 20260434, 20260435, 20260436, 20260437, 20260438, 20260439, 20260440, 20260441, 20260442, 20260443, 20260444, 20260445, 20260446, 20260447, 20260448, 20260449]
conditions: 48
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
  "run_dir": "paper_runs_integrated\\20260521_173035_paper_S1_integrated_model",
  "missing_files": [],
  "round_rows": 192000,
  "episode_rows": 960,
  "mood_out_of_range": 0,
  "fatigue_out_of_range": 0,
  "nan_or_inf_cells": 0,
  "duplicate_observe_count": 0,
  "fallback_rows": 0,
  "passed": true
}