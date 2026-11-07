# SELF_REVIEW_C5

- Package candidate: `EMBORA-R0PKG-2026-09-24-C5`; parent `EMBORA-R0PKG-2026-09-20-C4`.
- Owner disposition: `R0-C3-P1-01` **ADDRESSED / PENDING R0 VERIFICATION**; latest independent R0 C4 **REVISE**; U1 **NOT APPROVED**.

## Static acceptance

1. S03-U, S09, S10, YAML context_matrix, B01, B03 and 84 CSV rows: same 3×run-purpose matrix. N admits `confirmatory_frame`, `sensitivity`, `structural_fixture`; A and B admit `sensitivity` only. PASS.
2. Required `selected_adapter_convention` and `run_purpose` have no default. Missing/implicit selection, prohibited purpose, candidate/realized mismatch and per-action override are fail-hard in S03-U/S09/YAML/B01/B03. PASS.
3. Canonical B03 key includes both exact fields. Two keys differing only by adapter or only by purpose compare unequal, including N confirmatory vs N sensitivity. PASS.
4. CSV: 84 rows; `UGC5-` ID substitution reversed reproduces the C4 file bytes exactly. All 84 numeric/rational cells, payoff values and allowed-purpose strings equal C4. PASS.
5. Protected F-31/F-32 and all other formula/numeric blocks unchanged after live version-reference substitution. Claim, comparator frame, exclusion of refocus/planning/opponent modelling/strategic reflection unchanged. PASS.

The checks are documented in the changelog and package manifest; independent review must replay them. No executable software tests, pilots or experiments were performed. P0=0; owner-resolved P1=0 pending reviewer confirmation; open P2=0.
