# CONFORMANCE_TEST_REPORT — 2026-10-03_C5_v1.0

Status: **REVISE**; 143 passed, 1 failed of 144 tests. No full S12 or C1 success.

Failing test: `test_AT_URGENCY_near_epsilon_frozen_scientific_oracle[gain_near_desired]`. Direct scientific oracle 7/40=.175; observed .1749999999356433; residual 6.435668664650507e-11 > frozen 1e-12. See P2-C5-P1-01; dependent coverage halted, not waived/xfail.

Commands actually executed:

```bash
# From repo root:
python -m compileall -q code/journal_reference_v1
PYTHONPATH=code python -m pytest -q code/journal_reference_v1/tests
# From code/fixed_agent_experiment_code, on both base and task worktree:
python -m pytest -q tests
```

Syntax passes. Legacy baseline and worktree each give 15 passed; legacy git tree is byte-identical. Initial attempts recorded missing torch collection errors; after dependency restoration, a repo-root legacy test invocation gave 11 passed/4 failed because tests locate main.py relative to cwd. Correct cwd resolves that invocation issue without source changes.

Coverage is bounded: 84/84 raw UG rows and allowed contexts; prohibited A/B contexts; 8 simultaneous-game q outcomes×2 seats; config/type negatives; scalar policy/threshold/focus helpers; F-35 numerator exact tie, two legal positive neighbors, helper negative and map ordering; fixed-input unit descriptors; package integrity and import isolation. The independent expected values come from frozen rational CSV/tables and direct scalars, not observed code outputs.

S12 actual inventory:

| Acceptance ID | Actual status | Limits |
|---|---|---|
| AT-INIT | PARTIAL_PASS | State helper and derived/default serialization; constructor/reset engine not certified |
| AT-GAMES | PARTIAL_PASS | All legal adapter outcome payoffs and malformed action helpers; full grid/role/payload set not yet covered |
| AT-BOS | PARTIAL_PASS | Convention helper 1→O,2→F only; parity episodes not run |
| AT-UG-POLICY | NOT_RUN | Dependent candidate/policy coverage halted |
| AT-UG-CHOICE | PARTIAL_PASS | Numerator helper tie/neighbors/negative and map permutations only; candidate projections not certified |
| AT-UG-OFFER | PARTIAL_PASS | Frozen intervals/ties/permutation helper and external offer types |
| AT-EVENT | NOT_RUN | Draft engine; no episodes executed |
| AT-LEAK | NOT_RUN | Draft closed payloads; exhaustive leakage/spies not executed |
| AT-UG-ADAPTER | PARTIAL_PASS | 84/84 exact rational rows, every allowed row context, prohibited A/B contexts; full candidate/realized/raw-purity integration not tested |
| AT-ADAPTER-PDBOS | PASS_ENUMERATED_OUTCOMES | 8 outcomes ×2 seats; direct frozen q table |
| AT-URGENCY | FAIL | near-epsilon gain direct 7/40 oracle outside tolerance; near-zero loss and wider-helper cases pass |
| AT-FOCUS | PARTIAL_PASS | Two explicit ties and all-zero null helpers |
| AT-THRESHOLD | PARTIAL_PASS | Exact cuts, branch equality and specified scalar witness; full trace/switch episode not executed |
| AT-PD | PARTIAL_PASS | Direct helper equality and kind matrix |
| AT-STATE | PARTIAL_PASS | Derived initial state only; realized recurrence and clips not certified |
| AT-SUPPRESSION | NOT_RUN | Dependent realized updates halted |
| AT-MATERIAL | NOT_RUN | Draft q_star intervention not certified |
| AT-SWITCH | NOT_RUN | Draft single path not certified |
| AT-INVALID | PARTIAL_PASS | Required fields, 19 config negatives, action types, JSON duplicates/nonfinite; full trace/payload/round negatives not yet run |
| AT-RNG | PARTIAL_PASS | Fixed-input independent cluster descriptors only; F34 hash examples not run |
| AT-BASELINE | NOT_RUN | Draft B01 policies not certified |
| AT-CLAIMS | NOT_RUN | Normative contract read; no empirical claims or evidence map created |
| AT-LEGACY | PARTIAL_PASS | AST import isolation; unchanged legacy tree and 15/15 legacy tests; object/fallback integration audit still pending |
| AT-PACKAGE | PASS | Exact ZIP/manifest anchors, CRC, entries, 13 hashes/sizes and 84 rows |

No episodes, pilot, frame census, frequency/effect analysis, calibration or stochastic population were run. No claims of universal correctness, psychological validity, C1–C4 support, independent review or U2 closure.
