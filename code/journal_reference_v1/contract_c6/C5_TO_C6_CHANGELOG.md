# C5 to C6 delta classification

C6 is a numerical candidate, not approved. Exact line diff is C5_TO_C6.diff; PINNED_SECTIONS_C6.json gives section byte hashes.

| Kind | Delta | Scientific consequence |
|---|---|---|
| Numerical semantics | Separate I/R/B/O; 1e-12 now compares O to independent B | New executable acceptance contract requires review and author addendum |
| Numerical semantics | Literal RN F05/F07/F08 for nonidentity; common exact q=v identity | Preserves real identity and material_only exact-zero requirement; no snapping |
| Numerical semantics | Bound diagnostics separate from implementation tolerance; replace exact-alpha executable guard with derived envelope | Slight rounded over-alpha values are not clipped; all real inequalities retained |
| Numerical qualification | Real monotonicity versus rounded separation proof; endpoint stagnation and conversion saturation | No universal strict binary64 monotonicity/reachability promise; frozen UG votes retained |
| Numerical qualification | Explicit RN order/underflow/runtime/FMA restrictions and audit acceptance | No universal cross-runtime bitwise claim |
| Metadata | Package/spec/parameter/observation/result/numeric-evidence IDs | New downstream bindings after adoption, no new model mode or parameter |
| Authority metadata | C6 pending review/adoption, current C5 U1 retained | Does not invent author adoption or close P1 |
| Pinned scientific content | Game/payoff/grid, all real formula bodies, F35 N/P/D rule, adapter IDs/context, priorities/constants, claims/frame, event timing, variants | Preserved; exact upstream copies and hashes included |

Changed spec sections: S00/S01/S03-U/S06/S06-D/S12/S14, plus header identities. S03-U adds executable qualification and labels real strict monotonicity; the F35 rule paragraphs are byte-retained. S06 adds evaluation policy, S06-D labels real proofs and adds rounded bounds. S12 distinguishes scientific and executable numerical checks. S00/S14 change current gate/ownership metadata.

Pinned section text: S02 and game subsections, S03 and proposal matrix S03-P, S04 and all event/observation/leak subsections, S05 and all adapter/table subsections, S07, S08, S09, S10, S11 (including F34 hash), S13. Their exact hashes appear in PINNED_SECTIONS_C6.json. Some inherited headings/pending labels intentionally retain C5 historical provenance.

Parameter diff is limited to IDs/status, executable candidate urgency domain qualification and serialization numerical-policy annotations. Constants, enums, profiles, initial fields, adapter context, F35 branch/tie/priority rule, comparison tolerance and branch tolerance are structurally equal to C5. Unknown effective config fields remain rejected. Numeric evidence metadata is carried in manifests/reports, not as a new freely configurable top-level model field.

C5 scientific claims/roster are carried byte-for-byte, under their original IDs; no new claim contract is invented. Their references to C5 remain historical scientific anchors; a future adopted code/evidence manifest must bind those anchors alongside the reviewed C6 numerical spec. No old C5 source file is replaced by this derivative.
