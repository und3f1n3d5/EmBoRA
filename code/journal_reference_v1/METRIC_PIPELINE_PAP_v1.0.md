# PAP native metric pipeline v1.0

Interface EMBORA-PAP-NATIVE-METRICS-v1.0. Definitions are unchanged:
METRIC_AND_FAILURE_SCHEMA_C5_v1.0 sections2–4 as inherited by
EMBORA-P3-PAP-2026-10-18-C6-P2v1.4-v1.0 (PAP SHA256e093a94888ef4f510aeb4cfd3e035022245d260672a204c7d8361988fef40b80).
The parent pure helpers exist outside the repository in the config-binding
package; this module supplies typed native bindings, completeness and summaries.
Legacy CSV experiment_metrics is a different interface and is not a native PAP reader.

## Input and acceptance boundary

Inputs must already pass the applicable native artifact validation, with an
externally verified generation/validation/runtime/protocol/permission binding.
This pure module imports no Engine and performs no game, replay, artifact admission,
permission or selected-attempt/recovery decision. It does not replace the validator.
Missing native metric fields reject; all registered IDs are supplied explicitly.
Do not infer a complete scientific frame from the subset of files that arrived.
Complete here means complete relative to that exact declared metric inventory;
full-frame/pairing/provenance acceptance remains a separate R1 obligation.

For initial01 generation staysb9bbaadd; reviewed historical validator staysdeea6aa7.
The metric implementation is a third identity. Do not use a moving analysis HEAD
as the old validator: the reviewed historical policy intentionally permits only
its original declared delta. Neither that policy nor any execution guard is changed.

## Callables and native fields

- episode_metrics(config,rounds): focal_agent_id maps to explicit seat; reads only
  committed rounds1..T and actions_by_seat/payoffs_by_seat/post_states_by_seat,
  decisions_by_seat and updates_by_seat. Initial/pre-state S0 is not an observation.
  Baseline opponent null state is ignored; focal baseline pseudo-S is prohibited.
- pair_metrics(full,comparison): full-minus-switch meanP/meanpost-S; payoff
  normalization PD5/BoS3/UG8 and primary Q/4. Rank equality at±1e-9 is tie.
  Five exhaustive categories; kind controls remain separately labelled descriptive.
  tau_A=T+1 without divergence; IA/DA/UG-P offer distance/6; proposal/E/R/theta/
  reference-theta/state first differences and inclusive prior disagreement diagnostics.
- episode_metrics also supplies branch selection/disagreement, exact-N vote categories,
  separate D_VS, raw/applied costs, override/nonzero rates and fatigue clip fractions.
  These observables do not establish psychological validity or causal mediation.
- summary/nearest_rank: arithmetic math.fsum mean; conventional median; nearest-rank
  p10/p90; raw sign shares without the ranking cutoff; no excluded null/adverse cases.
- inventory_metrics: extract a full run once per bounded condition group; all dependent
  contrasts refer to that same full. Missing/invalid full invalidates every dependent
  contrast; no imputation, resumed rounds, deduplication or silent denominator reduction.
- registered_cells/configs/contrasts: expected cells derive from the predeclared registry,
  not observed successes. cell_summary returns fixed expectedN, incomplete status and
  unavailable rates when any cell is missing/invalid; all valid ties remain inN.
  Primary discordance, secondary strict-only denominator, tau frequency/survival,
  no-divergence mass and required distributions are computed without inferential claims.

Process one complete6/8member condition group at a time; emit compact run/contrast
metrics externally and release raw series before the next group. Do not retain the
entire scientific raw frame in RAM. Keep source logs and provenance unchanged.

## Explicit remaining gaps

alternative_readout computes only registered raw terminal/last-half/lambda27/component
readouts, one axis at a time. Alternative-readout normalizedQ/rank/discordance is
unavailable pending PAP-owner disposition: current PAP section6 calls divisor4
an unadopted candidate. Primary Q/4 is unchanged; no replacement convention is chosen.
Profile/horizon/adapter reports require their actual registered generated conditions,
not posthoc relabelling. No pilot effects are used to select any readout.

T-C1 and T-C2a evidence-domain joins/paper rendering, the final provenance/accepted-attempt
selection wrapper and independent full-frame sign-off are external requirements.
This module exposes reviewable metric callables; it is not a scientific Results table,
production execution service, full R1 acceptance, freeze or U2 permission.
