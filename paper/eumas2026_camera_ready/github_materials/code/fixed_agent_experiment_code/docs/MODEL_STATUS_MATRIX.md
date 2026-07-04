# Model status matrix

| Mechanism | reported_runs_compat | integrated_model | Notes |
|---|---:|---:|---|
| External game execution | behavior-driving | behavior-driving | Game is executed once per round by the runner. |
| Learned / DQN-like action modules | behavior-driving/logged | behavior-driving/logged | Compact two-layer DQN-like modules are present; current smoke runs use deterministic eval mode. |
| Mood, fatigue, resources, well-being, overall state | behavior-driving/logged | behavior-driving/logged | State affects thresholds and later actions. |
| Game-to-values adapter | diagnostic/explanatory | behavior-driving | Same production formula in both modes; status flag differs. |
| Appraisal: delta, urgency, valence, load, focus | diagnostic/explanatory | behavior-driving | Delta-based signed urgency prevents artificial negative mood from positive gains. |
| Suppression cost | diagnostic proxy | behavior-driving optional component | Current integrated update can include suppression cost. |
| Refocus | planned/future | planned/future | Kept as control concept; not hidden as a game action. |
| Belief/world-model update | planned/future | planned/future | Not claimed as implemented. |
| Human/observer validation | planned/future | planned/future | Not part of this code snapshot. |
| S5/S6 scenarios | legacy/exploratory | legacy/exploratory | Explicit placeholders only; not used for v11 claims. |
