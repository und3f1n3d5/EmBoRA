# Debugging

## Invalid action

Check `role_for()` and `get_legal_actions()`. In Ultimatum Game, proposer must only choose `offer(...)`; responder must only choose `accept` or `reject`.

## Hidden fallback

Use `--strict` for paper or validation runs. Fallback is only for debugging with `--allow-fallback`. Check `fallback_used` and `errors_count` in CSV and validation report.

## Negative mood saturation

Inspect `agent_i_delta_*`, `agent_i_signed_urgency_*`, `agent_i_reaction_intensity`, fatigue and duplicate-observe counts. Positive deltas should not produce negative appraisal reactions.

## Unknown scenario

S5/S6 are explicitly marked legacy placeholders. Unknown result directories should be archived or documented before being used in article materials.

## NaN/inf

Run `validation_report.json`. If NaN/inf appears, inspect adapter payoffs and normalization ranges first.

## Duplicate updates

`agent_i_duplicate_update_count` must be zero. A positive value indicates that `observe()` was called twice for the same agent/round.
