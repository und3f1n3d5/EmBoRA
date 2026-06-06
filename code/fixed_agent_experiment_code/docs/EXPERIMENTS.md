# Experiments

## Scenarios

- `S0`: smoke sanity check.
- `S1`: ordered cross-type matrix across games.
- `S2`: fixed-strategy adaptation proxy, first third vs last third.
- `S3`: personality × emotional intensity sweep.
- `S3B`: extended all-game profile sweep alias.
- `S4`: internal-state dynamics and collapse diagnostics.
- `S5`, `S6`: legacy exploratory placeholders, not v11 evidence.

## Profiles

- `quick`: 1 seed, 20 rounds by default.
- `standard`: 10 seeds, 100 rounds by default.
- `paper`: 20 seeds, 200 rounds by default.

`--episodes` and `--seeds-count` are separate. The runner repeats every condition for each seed. `episodes_per_condition` describes the intended episode count; `seed_count` controls the actual independent seeds used in the current run.

## Commands

```powershell
python experiment_runner.py --scenario S0 --profile quick --games "Prisoners Dilemma" --model-mode reported_runs_compat --strict --yes
python experiment_runner.py --scenario S0 --profile quick --games "Prisoners Dilemma" --model-mode integrated_model --strict --yes
python experiment_runner.py --scenario S1 --profile standard --games all --episodes 1 --seeds-count 1 --rounds 20 --model-mode integrated_model --strict --yes
```

## Interpretation guardrails

`reported_runs_compat` is appropriate for reproducing the article-v11 status boundary. `integrated_model` results are new architecture results. Fixed strategies are clearest in Prisoner's Dilemma; fixed rows in BoS and UG are stress tests unless redesigned with game-specific partner policies.
