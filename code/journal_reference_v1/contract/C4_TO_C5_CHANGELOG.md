# C4_TO_C5_CHANGELOG

- Delta ID: `EMBORA-DELTA-2026-09-24-C5`; parent `EMBORA-R0PKG-2026-09-20-C4`.
- Scope: registered `R0-C3-P1-01` schema/text repair. C3/C4 scientific semantics remain authoritative.

## Contract edits (line locations in C4 → C5)

| Artifact | C4 line | C5 line | Exact change |
|---|---:|---:|---|
| MODEL_SPEC S09 | 379 | 379 | Explicit machine enums for N and A/B run purposes. |
| MODEL_SPEC S10 | 393–395 | 393–395 | N use is exactly `confirmatory_frame`, `sensitivity`, `structural_fixture`; A/B exactly `sensitivity`. |
| PARAMETER_TABLE | 20 | 20 | Enum declaration key becomes `selected_adapter_convention`; required config field, selection source, and context matrix keep their exact values. |
| BASELINE B01 | 36–38 | 36–38 | Allowed-use rows use exact run-purpose enums. |
| BASELINE B03 | 68 | 68 | Condition tuple names `selected_adapter_convention` and `run_purpose`; explicit identity and fail-hard rule. |
| UG_REJECTION_SEMANTICS | 28, 63 | 28, 63 | Authorized N and A/B contexts use exact enums, including N sensitivity. |

All core files receive new `R1C5` filenames/live provenance IDs and references; CSV row IDs change `UGC4-` to `UGC5-`. CSV outcome data and allowed-purpose cells are byte-identical after the row-ID substitution. `AUTHOR_VERIFICATION_NOTE_U1_R1C5.md` changes live package ID and U1 gate status, without completing author approval. The draft brief similarly records R0 C4=`REVISE` and the pending C5 recheck. Source C4 artifacts and prior R0 results were not altered. Every other copied scientific paragraph, formula and coefficient remains unchanged after those enumerated schema and provenance substitutions.

Review disposition: owner **ADDRESSED / PENDING R0 VERIFICATION**. The independent R0 C4 verdict `REVISE` remains the latest reviewer verdict.
