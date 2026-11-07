# AUTHOR_VERIFICATION_NOTE_U1_R1C5

- Record ID: `EMBORA-AVN-U1-2026-09-24-R1C5`
- Package: `EMBORA-R0PKG-2026-09-24-C5`
- Status: prepared for human verification; **not signed, not accepted, not U1 approval**.

The responsible author authorized the C3 semantics and the narrow C4 repair. R0 C4 returned REVISE; final U1 remains closed until targeted R0 C5, Coordinator consolidation, and an explicit human decision. Fields below are not completed on the author's behalf.

| What the author must understand | Evidence to inspect | Author record |
|---|---|---|
| Normative rejection semantics: no material exchange, failed agreement, fairness=`1-fairness_accept(o)` as resisted inequity. | MODEL_SPEC S05/S10; UG_REJECTION_SEMANTICS sections 2–4; N rows in the 84-vector CSV | Not verified / not accepted |
| Raw targets use only legal observable offer/action/role/payoffs and never priorities, values, impulse or appraisal. | MODEL_SPEC S04/S05; CSV invariance columns; SELF_REVIEW SR02 | Not verified / not accepted |
| Priority-to-choice path: side-effect-free candidate appraisal; one `math.fsum(p_clip*z)` numerator owns branch/category; zero tie rejects; normalized D is diagnostic only. | MODEL_SPEC S03-U/F-35; worked profiles in UG semantics sections 5–7 | Not verified / not accepted |
| No circularity/double counting: candidate projections are discarded; realized F-05..F-11 executes once and is not added to N/D. Material/safety directional redundancy is disclosed. | MODEL_SPEC S03-U/S06; UG semantics sections 5 and 7 | Not verified / not accepted |
| Selected adapter is explicit and solely generates candidate/realized q; A/B are sensitivity-only; all 84 vectors and prohibited contexts are specified. | MODEL_SPEC S09/S10/S12; PARAMETER_TABLE adapter_contract; UG CSV | Not verified / not accepted |
| F-35 vote is state-invariant; N/B reject only on tie boundary; A always accepts; N/B proposals match; material_only retains nonmaterial candidate votes. | MODEL_SPEC S03-U; UG semantics section 7; CLAIM C2 | Not verified / not accepted |
| Claims remain candidates: C2a/C2b/C3 may be null or fragile; no strategic-reflection, human-psychology, novelty or performance claim was added. | CLAIM_CONTRACT C0–C5; CHANGELOG | Not verified / not accepted |

Minimum human replay before approval:

1. Check offers 2,5,8 for both roles against F-31C3 and the CSV.
2. Recompute offer-2 projected appraisals from neutral v and confirm `z=(+1,-1,+1,+1)`.
3. Confirm `N_VS=2,0.0,2` and `D_VS=2/3,0.0,2/3`; confirm N-derived zero tie rejects and no normalized resummation occurs.
4. Confirm neutral hybrid selects R and accepts all offers, while the disclosed high-intensity fixture selects E.
5. Check one-sided legal neighbors of the fairness-high tie accept; note that a legal strict-negative neighbor cannot exist under clipping.
6. Confirm no future offer/response or opponent private state is used and replay the labelled structural C2 witness without claiming neutral reachability.

Evidence reviewed by author: **not recorded**. Responsible author/date/comments: **blank**. Final decision: **PENDING**.

Internal R0 is AI-assisted red-team review, not independent human peer review. This note authorizes no implementation, tests, pilot, experiment, manuscript claim or submission. Final AI-use disclosure and publication compliance remain later-gate tasks.
