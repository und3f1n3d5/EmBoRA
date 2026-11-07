# DRAFT_FINAL_U1_BRIEF_C5

- Brief ID: `EMBORA-U1-BRIEF-2026-09-24-C5`
- Package: `EMBORA-R0PKG-2026-09-24-C5`
- Specification: `EMBORA-MSJ1-2026-09-24-R1C5`
- Claim contract: `EMBORA-CC-2026-09-24-R1C5`
- Status: draft for Coordinator after targeted R0 C5; **not U1 approval**.

## Proposed C3 scientific decision, C4/C5 contract repair

Adopt one normative UG rejection adapter:

`fairness_reject(o)=1-fairness_accept(o)=|10-2o|/10`, `material_reject=0`, `relationship_reject=0`, with safety retained from F-04.

This makes the raw event meaning depend on the observed offer/action, not on the agent's priorities. A `zero_exchange` and B `neutral_no_exchange` remain separate sensitivity adapters and cannot be reference defaults. The explicitly selected run adapter is the sole candidate/realized q source; A/B are valid only for sensitivity runs.

## Why the responder path also changes

C2 could already express a same-offer priority-dependent response indirectly through `pbar -> W -> iota -> h`; C3 is **not** justified by universal C2 impossibility. A structural C2 witness from the issue register is offer 6 with `v=(1,0,1/2,1/2)`, `m=-79/300`, `f=1/5`, pessimistic/high: material_high gives `W=2/3`, `iota=-37/80`, `h=237/40` and accepts; fairness_high gives `W=1/3`, `iota=-43/80`, `h=243/40` and rejects; both select E because `theta=761/2000`. This is a legal injected state only, with no neutral-reachability claim.

C3's actual distinction is a direct inspectable comparison of current action consequences plus an equal-value worked witness. It replaces only the UG responder E proposal with F-35:

1. compute priority-free accept/reject targets for the current offer;
2. form side-effect-free one-step appraisals from the same pre-state;
3. compare the two actions per channel;
4. aggregate post-clipping binary64 priorities once as `N_VS=math.fsum(p_clip*z)` in fixed K order;
5. accept for positive N, reject for negative N, and reject an exact `N_VS==0.0` tie; log `D_VS=N_VS/math.fsum(p_clip)` as diagnostic only.

The rational proposal remains accept-all-positive. Hybrid arbitration remains F-14. Candidate projections never mutate state; the realized outcome is updated once. This is present-action evaluation, not planning or opponent modelling.

## Decisive worked example

At offer 2 and neutral values, channel comparison is `(+1,-1,+1,+1)`. Material_high and relationship_high have `N_VS=2`, `D_VS=2/3` and accept. Fairness_high has binary64 `N_VS=0.0`, `D_VS=0.0` and rejects by the declared tie rule. With the common legal high-intensity/negative-mood fixture, hybrid selects E, so final actions differ. Neutral hybrid selects R and accepts all offers; this masking null is retained.

The directional vote is prospectively state-invariant. Under clipped priorities normative N/B rejection exists only on this endpoint tie boundary; A always proposes accept; N and B share proposal partitions. Material and responder safety vote in the same payoff direction without priority double counting. `material_only` leaves nonmaterial candidate votes intact. F-14 and state/history still govern branch selection and later trajectories.

## Claim and evidence boundary

- C1 gains F-31C3/F-35 correspondence obligations.
- C2a gains a structural priority-to-choice witness and raw-q invariance test.
- C2b keeps the same 1,215-cell finite frame and estimands; UG-R behavior may change and may still be null in some profiles/branches.
- C3 ranking remains an unconfirmed operational candidate; normative/A/B adapter results are separate sensitivity blocks.
- C0 novelty, comparator scope, stochastic-unit rules and secondary C4 claim do not expand.

No code, tests, pilot, experiment or findings exist. R0 C4 returned REVISE with P0=0, blocking P1=1, P2=0. C5 owner addresses the remaining P1 through exact context and condition keys; independent R0 C5 verification is pending.

## Author decision after R0

If targeted R0 C5 returns `PASS_TO_U1`, the responsible author should either:

- explicitly adopt the preserved C3 formula, C5 selected-adapter/numeric contract, disclosed limits and claim contract, then authorize implementation/correspondence tests only; or
- request a new revision. Any formula, tie, adapter-status or claim-scope change requires a new version and substantive re-review.

U1 must not authorize pilots or experiments before the later experiment gate.
