# P2 pre-implementation record — 2026-10-03 C5 v1.0

Actual base: 2af7e4cedcbdf18c773af9573fdc540560761c01, origin/main HEAD observed live. Base dirty state: empty. Task branch/worktree: journal_reference_v1. No AGENTS.md or CONTRIBUTING found in the repository. ToR 03 requires this branch name.

Authority: EMBORA-U1-DECISION-2026-10-03-C5-v1.0; frozen EMBORA-MSJ1-2026-09-24-R1C5. Changes are implementation/diagnostic only. All legacy files remain byte-identical. New path implements exact policies, neutral S=0, selected adapter contract, pure candidate appraisal, single realized update and atomic round order. No old results are new evidence; every journal trajectory would require new, separately authorized runs.

Expected invariants: fixed K; binary64 math.fsum numerator owns F-35 category/action; exact zero rejects; no candidate mutation; raw q reads only legal outcome; one adapter/run; closed schemas; no unknown/default adapter; material_only affects only realized q_star; both results/update computations precede atomic commit; all five switches share one path; no model RNG or legacy imports.

Permitted execution: conformance helper/structural fixtures and necessary short golden episodes only. No census, pilot, sensitivity trajectories or parameter search.

Baseline command: python -m pytest -q code/fixed_agent_experiment_code/tests. Initial collection: 9 errors because torch is absent and legacy dqn module accesses nn.Module after import failure. This is an environment finding, not a journal code regression. Restore dependency, preserve source.

Remote write probe: git push --dry-run origin journal_reference_v1 failed: fatal: could not read Username for 'https://github.com': terminal prompts disabled. Remote publication pending authenticated access. Local git implementation remains possible.
