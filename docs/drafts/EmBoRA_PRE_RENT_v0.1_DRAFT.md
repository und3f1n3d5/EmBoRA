# EmBoRA PRE-RENT v0.1 — DRAFT

Date: 2026-11-22. Status: DRAFT / IMPLEMENTATION_NOT_APPLIED / TESTS_NOT_RUN / NOT_FROZEN.
Scope updated by the author: prepare a draft only, without execution.

This document records a proposed minimal implementation delta and an operations annex for Coordinator review. It does not enable a new implementation, grant execution authority, qualify a server, authorize rental, or establish U2. No Python, Engine, archive, restore, cleanup, pilot or recovery command was executed for this delivery. The execution environment was unavailable. The accepted branch and draft PR are unchanged; this document is isolated on a documentation draft branch.

## 1. Source and evidence anchors

| Domain | Exact anchor |
|---|---|
| Accepted analysis/dispatch source | d7672956730b5693c1eec3cfd297952c8c065cda |
| Accepted source tree | ab4825081be1f7812701e1e2fa645a05aba3e95d |
| Accepted full inventory | 545 files; SHA256 1c722a8168019e1f23d8fce9beaaab1f0cc50ff9356ebad3e682db07a70e2217 |
| Pinned native validator | deea6aa72e003da646887e2a41029fbf2ef9c506 |
| Native validator tree | 606dc8b4c19ef30c48b98d33c044330a966a5f33 |
| Native validator inventory | 534 files; SHA256 97e91964adea2a2970639133fe9f1138ae4713dca4f5c8557bc52a659a46ad96 |
| Previously qualified reference runtime | SHA256 01d30d872a3a4c6a3ca9cbeed142f1d8f6f2b9f4848a0cdd4780115e519b0e4a |
| Canonical PAP | EMBORA-P3-PAP-2026-10-18-C6-P2v1.4-v1.0; 25030 bytes; SHA256 e093a94888ef4f510aeb4cfd3e035022245d260672a204c7d8361988fef40b80 |
| Unchanged allocation proposal | ALLOCATION_PROPOSAL_C6_v1.0; raw SHA256 f968317096afe0ac9a5a14dc0d673a583b70693c067d352064a72b9e691c9bee |
| Existing analysis schema | ANALYSIS_C6_v1.0.json; 17679 bytes; SHA256 4dc323322f511824a813555c84b8de18d45b005bc613ea7342baac23cca9bd67 |
| Existing accounting schema | ACCOUNTING_C6_v1.0.json; 7485 bytes; SHA256 2b299f9522686dbde4325df76949ed1e48463fc7793a69e6b53b2030f77681a5 |

These are accepted historical anchors, not a new local clean-checkout or runtime qualification receipt. Files were inspected through GitHub at the accepted commit. No new executable source tree, inventory or runtime is claimed.

Initial01 generation remains b9bbaaddc2fddb4e92bbdca24952f3566d93e470, tree 325ef04e416edcd3b6fa18f059bffb242b90c87d, runtime e340a5b64c3f46d2e490264db11a3d49cc82eb12818ead960ea92dce8f50b908. Validator identity is separate. Its permission is consumed.

The author decision of 2026-11-08 adopts alternative divisor 4 and supersedes the earlier unresolved disposition and costly storage recommendation. It does not change the canonical PAP bytes. CE01 and bounded R1-ANALYSIS/R1-DISPATCH acceptance are reused in their accepted scopes. No full-R1 claim follows.

## 2. Proposed minimal implementation and protocol delta

Proposed addendum ID: EMBORA-ALT-READOUT4-ADDENDUM-v1.0-DRAFT.
The scientific choice of divisor 4 is adopted; this technical binding is a draft.

Inspected callables:
- code/journal_reference_v1/pap_metrics.py: alternative_readout, pair_metrics, matched, rank_sign, tie_category, inventory_metrics, registered_cells, cell_summary.
- code/journal_reference_v1/analysis_admission.py: admitted_analysis, write_export, main.
- code/journal_reference_v1/batch_accounting.py: verify_initial_replay_policy, verify_allocations, reconcile_native, audit.

Current implementation: alternative_readout computes registered raw post-round Q but returns unavailable normalized/rank fields. admitted_analysis exports unavailable alternatives under the closed ANALYSIS_C6_v1.0 schema. Therefore changing only the raw helper's status string would not enable admitted normalized outputs.

Proposed diff, not applied:
1. Add a small versioned alternative-pair readout to pap_metrics.py. Reuse matched, alternative_readout, rank_sign and tie_category. For an admitted complete full/comparison pair:
   - Q_lambda = mean(lambda_W * Wtilde + lambda_m * m - lambda_f * f).
   - Q_component = mean(Wtilde), mean(m), or mean(-f).
   - delta_Q_alternative = Q_full - Q_comparison.
   - normalized_delta_Q_alternative = delta_Q_alternative / 4, fixed and non-configurable.
   - normalized_delta_P = (P_full - P_comparison) / MAX_PAYOFF[stratum], where PD=5, BoS=3, UG-P/UG-R=8.
   - rank signs use the existing strict comparisons to +/-1e-9; equality is tie. The existing five categories and strict-discordance rule are reused.
2. Add a versioned alternatives sidecar/export binding, proposed EMBORA-ADMITTED-ALTERNATIVES-C6-v1.1. It must run the existing admitted_analysis/native provenance/whole-group selection path before computing alternatives; a supplied PASS JSON is insufficient. Bind exact admission bytes, accepted base export bytes, protocol/addendum bytes, native inventories, validator and actual analysis successor identity.
3. Give that sidecar a new closed schema. Do not populate forbidden fields in the old ANALYSIS_C6_v1.0 envelope. Preserve old exports and verification unchanged. Missing/invalid full or comparison makes the dependent alternative unavailable; preserve expected contrast membership and all-cell denominators.
4. Keep batch_accounting, native permission/authority, CE01 policy bridge, allocation bytes, batch composition and 258 plans unchanged.

No numerical dynamics, adapters, scientific enums or permission changes. Primary delta_S and primary Q/4 retain their current meaning. Do not rename an alternative delta_Q as physical delta_S. Signed -f is applied once. Do not derive a divisor from observed range, lambda sum or pilot effects.

Registered lambda grid remains (.5,1,2) x (0,.5,1) x (0,.5,1), all 27 rows including the primary repeat. Components remain Wtilde, m, minus_f. Use post-round t=1..T, no S0. Lambda/component axes use the registered primary T200/mean/reference-cutoff context. Preserve separate terminal, last-half and cutoff axes and all existing adapter/horizon/profile restrictions; do not form new cross-products. No trajectory execution is needed.

Any persistence/aggregate output must use the already registered definition; divisor adoption does not authorize a new persistence estimand. Its exact schema mapping must be checked during implementation. Do not fill unsupported aggregate fields merely to complete a schema.

### Targeted synthetic oracles — expected, NOT RUN

For positive normalized payoff rank:
| Raw alternative full-minus-comparison delta | Normalized alternative | Expected category |
|---|---|---|
| +3.999996e-9 | +9.99999e-10 | state_only_tied |
| +4e-9 | +1e-9 | state_only_tied |
| +4.000004e-9 | +1.000001e-9 | strict_concordant |
| -3.999996e-9 | -9.99999e-10 | state_only_tied |
| -4e-9 | -1e-9 | state_only_tied |
| -4.000004e-9 | -1.000001e-9 | strict_discordant |

Use exactly constructed binary64 cutoff*4 and adjacent values for equality/boundary tests. Add negative-payoff and zero-payoff controls to cover all five categories. Verify primary-repeat lambda equals primary Q/4, negative-f orientation, full reuse, missing-full dependency, no S0, and unchanged mean/window/cutoff guards. Test the admitted sidecar, not only the pure helper. Schema/hash/identity/authority failures must remain reject.

## 3. Operations annex — DRAFT FOR COORDINATOR ACCEPTANCE

One sequential batch only. Preserve pairing, allocation order, whole groups and all mandatory logs. No scheduler or parallel batches. Existing accounting remains authoritative; archiving never converts failure to COMPLETE or unhalts dispatch.

Per-batch sequence:
1. Verify actual free space, exact source/runtime/proposal/batch inputs, existing sequential ledger tip and permission state. An allocation is not permission.
2. Execute only if separately authorized in the future. Preserve output and unsuccessful/partial/crash evidence unchanged. Current task authorizes no such execution.
3. Run required pinned native validation; preserve actual argv/cwd/source/runtime/permission digest, exits, stdout/stderr and resources in their declared domains.
4. Create one lossless archive SET: native.zip contains exactly the immutable native directory's files under relative names, as required by existing reconcile_native. evidence.zip contains external validation receipts, checkpoint/accounting chain, commands/logs and failed evidence. An external manifest lists both archive byte sizes/SHA256 and each payload relative path/size/SHA256. Do not add evidence files inside the native ZIP and break its accepted exact-file-set contract. Do not create an additional large outer ZIP.
5. Check archive file set, duplicate names, CRC and every payload hash/size against the source inventory. Restore to a fresh empty staging directory and compare bytes/inventory, including failed evidence. Check before and after source inventories for concurrent change. Reject absolute/traversal paths, symlinks and unsupported file types rather than silently dropping them.
6. For a valid complete native queue, call the existing actual reconcile_native and audit path with its trusted pins; preserve its native-derived checkpoint. For failed/unverified/incomplete native data, archive everything and remain halted. Archival success is not scientific/native acceptance.
7. Transfer both archives and the manifest/receipts to the laptop. On the laptop independently hash both archives, verify CRC/file-set/payload hashes and restore/read back. Record actual laptop verification and an explicit operator confirmation receipt referencing those exact archive hashes and the server batch identity. A server-created assertion, transfer exit 0 alone or a copied confirmation template is not confirmation.
8. Only after that confirmation, permit removal of explicitly enumerated redundant server raw/restored/archive copies. Retain the small manifest, source/runtime/input references, ledger/checkpoints, validation/restoration/confirmation/cleanup receipts. Never delete the only verified archive, failed originals without a complete retained archive, an active output or arbitrary paths.
9. Next reservation still requires the existing accounting audit and all of its checkpoint rules. Failure/overshoot/late-failure or unresolved checkpoint blocks it. No automatic replay/repair allowance is added.

Cleanup guard prerequisites are conjunctive: archive hashes match + complete payload inventory/CRC/readback + laptop verification + explicit confirmation + batch identity/path match + no active writer + retained accounting/evidence. Missing, stale, mismatched or malformed evidence => deny cleanup. A separate deletion allowlist must contain only that batch's redundant server copies. No unrestricted rm command is provided in this untested draft.

Future analysis: copy the retained archive set back, verify the external manifest and archive hashes, restore into a new directory, verify payloads and required native identity, then use the admitted analysis path. Preserve original generation identity, failed evidence and protocol bytes. Do not regenerate traces to replace missing archives.

## 4. Storage calculation — no compression credit

Units are bytes; 1 GiB = 1,073,741,824 B. Provider “150 GB” is treated as 150,000,000,000 B until measured otherwise.

Let B be the full largest batch raw domain; use its existing 44 GiB proposed cap, not a predicted compression ratio. Let E be companion evidence outside that domain. With full raw + ZIP_STORED archive + full restore, peak is:

    3 * B + 3 * E + H + O

H is archive/manifest/filesystem overhead; O is OS, source, runtime and retained operator metadata. At pre-batch free-space admission, already occupied O is excluded from actual free bytes and must not be subtracted twice. Allow for filesystem allocation/inodes and transient files, not merely apparent payload length.

| Quantity | Bytes |
|---|---:|
| B = 44 GiB | 47244640256 |
| 3 * B | 141733920768 |
| Illustrative archive/manifest allowance H | 4194304 |
| 3 * B + H | 141738115072 |
| Nominal 150 GB remaining for O + 3E and other overhead | 8261884928 |
| DRAFT planning envelope O + 3E + remaining overhead = 8 GiB | 8589934592 |
| Total with that envelope | 150328049664 |
| Shortfall against nominal 150 GB | 328049664 |

The 4 MiB H and 8 GiB combined envelope are explicit planning allowances, not measured bounds or an OS qualification. Actual file count/path lengths/evidence/allocated space can require more. Enforce measured available bytes before creating each additional copy; stop on shortage and preserve data. Logs may not be truncated to fit an estimate.

150 GB is conditionally sufficient only if actual non-batch occupancy plus evidence/overheads fit within the remaining ~8.262 GB. Under the illustrative 8 GiB envelope it is short by 328,049,664 B: the arithmetic minimum is 150,328,049,664 usable bytes, or 151 decimal GB before any extra filesystem reserve. A modest 160 GB nominal disk is the DRAFT recommendation for the full-restore order, subject to measured usable/free bytes. It is not a rental or qualification. A 150 GiB offer is a different capacity and must be measured.

For an 11 GiB raw-cap batch, the same three-copy calculation plus 4 MiB and 8 GiB is 44,027,609,088 B. Do not change batch composition to obtain that smaller bound.

4 vCPU / 8 GB RAM remains a candidate, with one worker; no GPU, RAID or paid backup. Existing proposed native RSS cap is 4 GiB, leaving a conditional host margin; no new-host peak/runtime guarantee follows. Run native validation/archive/restore sequentially. Pilot compression and historic readback timings are observations, not capacity/throughput guarantees.

The laptop must have measured free space for retained archive sets and any local restore. A nominal 1 TB laptop does not guarantee retention of every uncompressed batch. Preserve actual cumulative archive sizes, reserve transfer/restore space, and stop or choose additional author-approved storage before it fills. No compression assumption closes this gap. Do not delete the server's only verified copy on a full laptop.

## 5. Commands for the future operator — DRAFT, NOT EXECUTED

These establish exact source anchors only. They do not install/qualify the accepted runtime or authorize trajectories.

```sh
git clone --branch journal_reference_v1 https://github.com/und3f1n3d5/EmBoRA.git EmBoRA
git -C EmBoRA checkout --detach d7672956730b5693c1eec3cfd297952c8c065cda
git -C EmBoRA rev-parse HEAD
git -C EmBoRA rev-parse HEAD^{tree}
git -C EmBoRA status --porcelain=v1
git -C EmBoRA worktree add --detach ../EmBoRA-native deea6aa72e003da646887e2a41029fbf2ef9c506
df -B1 .
df -i .
```

Expected source/tree are in section 1; any dirty state or mismatch blocks using the checkout as an exact clean anchor. Obtain the previously verified runtime/source recovery delivery and verify its external hashes. Use its exact reference lock and wheelhouse; do not substitute system Python or invent a runtime download URL. Offline pip install must use that delivery's exact pinned/hashes command, followed by pip check and the existing runtime qualification procedure. New-host installation is NOT_RUN; no claim of a ready installed environment is made.

For native validation/reconciliation, reuse the already reviewed exact CLI/worker arguments and required identity/trusted permission digest from the allocation/admission recovery delivery. Do not synthesize permission, trust a digest found only inside the untrusted output, or switch to report mode to obtain acceptance.

Archive command specification for the later small helper:
- Python standard library ZipFile, mode='x', compression=ZIP_STORED, allowZip64=True; stream payloads rather than read an entire batch into RAM.
- Open source read-only; reject unsafe/special paths; snapshot and recheck the complete inventory; deterministic relative names.
- Archive outputs and restore roots must be outside immutable source directories and newly created; never overwrite originals.
- SHA256 over original raw files and complete archive bytes; ZIP CRC is additional, not a replacement.
- Restore streams into a fresh staging root; compare every file and absence of extras; record actual sizes/allocated space.
- Laptop confirmation and cleanup commands remain unavailable until the guard is implemented and its focused fixtures pass. An untested deletion script is not supplied as a production-ready operation.

The draft deliberately does not present nonexistent helper/CLI commands as working installation commands. Filling this executable gap requires the focused implementation/checks below, not a broader audit.

## 6. Actual evidence and NOT_RUN

| Item | Result |
|---|---|
| Author decision and accepted-result record | Read |
| Exact accepted source inspection via GitHub | Read; no local checkout claim |
| Disk arithmetic | Calculated; not a disk-space or I/O test |
| Executable delta | NOT_APPLIED |
| Python/readout boundary tests | NOT_RUN — draft-only scope / environment unavailable |
| Admitted alternatives schema/integration negatives | NOT_RUN |
| Archive/restore/cleanup synthetic tests | NOT_RUN |
| New-host/runtime installation | NOT_RUN |
| New experimental/pilot/recovery trajectories | NOT_RUN / NOT_AUTHORIZED |
| Full audit/numerical/legacy/all-config reruns | NOT_RUN — unchanged dependencies, not needed for this draft |
| Rental/U2/freeze/merge/release | NOT_AUTHORIZED |

No new PASS receipts, test counts, measured resource guarantees or independent acceptance are claimed.

## 7. Focused completion and independent delta review

After an execution environment is available and execution of the implementation work is resumed:
1. Apply only the versioned alternative /4 pair + admitted sidecar/schema delta and a small archive/restore/confirmation/cleanup helper; preserve all section-1 accepted bytes.
2. Run only synthetic boundary/control tests and affected admitted-export tests. Check schema/identity/hash/authority negatives, missing/invalid full and unchanged all-cell membership.
3. Use small nested binary/empty/unicode-name fixtures, including failed/partial evidence: source/archive/restore inventories must match exactly. Reject missing/extra/tampered members, stale hashes, duplicate/unsafe paths, and changed source bytes.
4. Demonstrate cleanup denied before archive, before restoration, without actual laptop confirmation, with stale/wrong batch/hash, active writer or missing failed evidence. Demonstrate allowed cleanup only inside a synthetic redundant-copy allowlist after all gates; the retained archive remains recoverable.
5. Reuse closed CE01/R1-ANALYSIS/R1-DISPATCH controls where dependencies are unchanged. Do not rerun numerical/legacy/all-config/initial01 audits or trajectories.
6. Produce actual argv/exits/stdout/stderr/JSON/JUnit and exact executable successor commit/tree/inventory/runtime/schema/addendum hashes. No local runtime is currently available to generate them.

Delta-only reviewer prompt: inspect the exact future executable successor against d7672956730b5693c1eec3cfd297952c8c065cda. Verify adopted fixed alternative /4 with primary Q/4 and the scientific frame unchanged; required native provenance before new sidecar export; unchanged allocations/CE01/native guards; archive-set completeness, restore identity and laptop-confirmed cleanup gate using synthetic data only. Review operations annex and measured capacity assumptions separately. This document is a DRAFT for Coordinator acceptance, not READY_FOR_INDEPENDENT_RECHECK or full R1 PASS.
