# Validation summary

## Verdict

All official paper runs passed automated validation: **True**. The local unit-test report says:

```text
...............                                                          [100%]
15 passed in 46.48s
```

Environment reported by the local Windows run:

```text
Python 3.13.13
platform= Windows-11-10.0.26200-SP0
python= 3.13.13
torch= 2.12.0+cpu
numpy= 2.4.6
matplotlib= 3.10.9
```

## Official runs

| model_mode           | scenario   | run_dir                                       | games                                              |   conditions_n |   episodes_per_condition |   seed_count |   rounds_per_episode |   expected_round_rows |   expected_episode_rows |   actual_round_rows |   actual_episode_rows | validation_passed   |   fallback_rows |   duplicate_observe_count |   mood_out_of_range |   fatigue_out_of_range |   nan_or_inf_cells |   missing_files_count |
|:---------------------|:-----------|:----------------------------------------------|:---------------------------------------------------|---------------:|-------------------------:|-------------:|---------------------:|----------------------:|------------------------:|--------------------:|----------------------:|:--------------------|----------------:|--------------------------:|--------------------:|-----------------------:|-------------------:|----------------------:|
| reported_runs_compat | S1         | 20260521_163020_paper_S1_reported_runs_compat | Battle of Sexes, Prisoners Dilemma, Ultimatum Game |             48 |                       20 |           20 |                  200 |                192000 |                     960 |              192000 |                   960 | True                |               0 |                         0 |                   0 |                      0 |                  0 |                     0 |
| reported_runs_compat | S2         | 20260521_163508_paper_S2_reported_runs_compat | Battle of Sexes, Prisoners Dilemma, Ultimatum Game |             27 |                       20 |           20 |                  200 |                108000 |                     540 |              108000 |                   540 | True                |               0 |                         0 |                   0 |                      0 |                  0 |                     0 |
| reported_runs_compat | S3         | 20260521_163747_paper_S3_reported_runs_compat | Prisoners Dilemma                                  |             27 |                       20 |           20 |                  200 |                108000 |                     540 |              108000 |                   540 | True                |               0 |                         0 |                   0 |                      0 |                  0 |                     0 |
| reported_runs_compat | S4         | 20260521_163931_paper_S4_reported_runs_compat | Battle of Sexes, Prisoners Dilemma, Ultimatum Game |             12 |                       20 |           20 |                  200 |                 48000 |                     240 |               48000 |                   240 | True                |               0 |                         0 |                   0 |                      0 |                  0 |                     0 |
| integrated_model     | S1         | 20260521_173035_paper_S1_integrated_model     | Battle of Sexes, Prisoners Dilemma, Ultimatum Game |             48 |                       20 |           20 |                  200 |                192000 |                     960 |              192000 |                   960 | True                |               0 |                         0 |                   0 |                      0 |                  0 |                     0 |
| integrated_model     | S2         | 20260521_173426_paper_S2_integrated_model     | Battle of Sexes, Prisoners Dilemma, Ultimatum Game |             27 |                       20 |           20 |                  200 |                108000 |                     540 |              108000 |                   540 | True                |               0 |                         0 |                   0 |                      0 |                  0 |                     0 |
| integrated_model     | S3         | 20260521_174014_paper_S3_integrated_model     | Prisoners Dilemma                                  |             27 |                       20 |           20 |                  200 |                108000 |                     540 |              108000 |                   540 | True                |               0 |                         0 |                   0 |                      0 |                  0 |                     0 |
| integrated_model     | S4         | 20260521_174430_paper_S4_integrated_model     | Battle of Sexes, Prisoners Dilemma, Ultimatum Game |             12 |                       20 |           20 |                  200 |                 48000 |                     240 |               48000 |                   240 | True                |               0 |                         0 |                   0 |                      0 |                  0 |                     0 |

## Ignored runs

Two early reported S1 directories were incomplete config-only attempts, and one complete manual S1 run is a duplicate of the final scripted S1 run. The official set uses the latest complete scripted run per scenario/mode.

| root                  | run_dir                                       | status   | reason                                                                                     |   files_count |
|:----------------------|:----------------------------------------------|:---------|:-------------------------------------------------------------------------------------------|--------------:|
| paper_runs_reported   | 20260521_160703_paper_S1_reported_runs_compat | ignored  | incomplete run, only config or failed pre-output run                                       |             1 |
| paper_runs_reported   | 20260521_161642_paper_S1_reported_runs_compat | ignored  | incomplete run, only config or failed pre-output run                                       |             1 |
| paper_runs_reported   | 20260521_161912_paper_S1_reported_runs_compat | ignored  | complete duplicate of official reported S1; same summary_for_paper hash as 20260521_163020 |            12 |
| paper_runs_reported   | 20260521_163020_paper_S1_reported_runs_compat | official |                                                                                            |            12 |
| paper_runs_reported   | 20260521_163508_paper_S2_reported_runs_compat | official |                                                                                            |            12 |
| paper_runs_reported   | 20260521_163747_paper_S3_reported_runs_compat | official |                                                                                            |            12 |
| paper_runs_reported   | 20260521_163931_paper_S4_reported_runs_compat | official |                                                                                            |            12 |
| paper_runs_integrated | 20260521_173035_paper_S1_integrated_model     | official |                                                                                            |            12 |
| paper_runs_integrated | 20260521_173426_paper_S2_integrated_model     | official |                                                                                            |            12 |
| paper_runs_integrated | 20260521_174014_paper_S3_integrated_model     | official |                                                                                            |            12 |
| paper_runs_integrated | 20260521_174430_paper_S4_integrated_model     | official |                                                                                            |            12 |
