Experiment run log
==================
scenario_name: S4
run_profile: paper
model_mode: reported_runs_compat
games: Prisoners Dilemma, Battle of Sexes, Ultimatum Game
episodes_per_condition: 20
rounds_per_episode: 200
seed_count: 20
seeds: [20260430, 20260431, 20260432, 20260433, 20260434, 20260435, 20260436, 20260437, 20260438, 20260439, 20260440, 20260441, 20260442, 20260443, 20260444, 20260445, 20260446, 20260447, 20260448, 20260449]
conditions: 12
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
  "run_dir": "paper_runs_reported\\20260521_163931_paper_S4_reported_runs_compat",
  "missing_files": [],
  "round_rows": 48000,
  "episode_rows": 240,
  "mood_out_of_range": 0,
  "fatigue_out_of_range": 0,
  "nan_or_inf_cells": 0,
  "duplicate_observe_count": 0,
  "fallback_rows": 0,
  "passed": true
}