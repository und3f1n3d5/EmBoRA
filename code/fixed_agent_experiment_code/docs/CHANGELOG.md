# Changelog

## Architecture alignment snapshot

- Added `agent_core/` as the single source of truth for model schema, adapter, appraisal, state updates, DQN-like modules and agent classes.
- Added `ModelMode`: `reported_runs_compat` and `integrated_model`; deprecated `paper_v10_compat` alias is normalized.
- Enforced two-phase loop: `decide()` has no state/learning side effects; `observe()` is the only update point.
- Implemented focal-agent `GameValueAdapter` for PD, BoS and UG.
- Replaced ideal-gap mood appraisal with delta-based signed urgency.
- Centralized well-being and overall-state calculations; well-being is order-invariant.
- Added role-specific Ultimatum Game action spaces.
- Added strict/fallback policy and validation reports.
- Added manifests with SHA-256 code snapshot IDs.
- Added tests, documentation and `examples/minimal_run.py`.

## Compatibility notes

Legacy agent files remain in the archive for reference and backward compatibility, but the experiment runner uses the architecture-aligned core. Results from `integrated_model` should be described as a new architecture version, not a direct v11 reported-run reproduction.
