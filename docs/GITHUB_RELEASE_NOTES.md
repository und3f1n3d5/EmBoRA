# GitHub release notes

## Recommended release structure

Publish the code from `github_materials/code/fixed_agent_experiment_code` as the repository content. Put full raw paper results in GitHub Releases or Git LFS, because `round_level.csv` files are large. Keep compact summaries in the repository under `results/compact/`.

## What is validated

- Unit tests: 15 passed.
- Official paper runs: S1-S4 in `reported_runs_compat` and `integrated_model`.
- Validation checks: required files, row counts, NaN/inf, mood/fatigue bounds, duplicate observe, fallback rows.

## Suggested repository folders

```text
agent_core/
tests/
docs/
examples/
results/compact/
article_materials/tables/
article_materials/figures/
```

Do not mix `reported_runs_compat` and `integrated_model` results in the same claims. Treat the first as paper-compatible and the second as a new integrated architecture snapshot.
