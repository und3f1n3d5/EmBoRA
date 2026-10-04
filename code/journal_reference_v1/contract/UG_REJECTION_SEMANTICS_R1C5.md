# UG_REJECTION_SEMANTICS_R1C5

- Decision ID: `EMBORA-UGSEM-2026-09-24-R1C5`
- Specification: `EMBORA-MSJ1-2026-09-24-R1C5`
- Status: C4 contract repair preserving normative C3 semantics; targeted R0 C5 pending; not implemented, tested or U1-approved.

## 1. Separation invariant

The C3 path has four non-interchangeable layers:

1. Observable facts/action: endowment `E=10`, legal offer `o in {2,...,8}`, role, `accept|reject`, and deterministic legal payoff.
2. Raw value-relevant consequences `q=(material,fairness,relationship,safety)`, computed only from layer 1.
3. Priority weighting: `pbar` is applied after raw consequences are fixed.
4. Candidate action evaluation/choice and, after the realized action, appraisal/state update.

Changing priorities, current values, mood, fatigue, impulse, branch selection or appraisal while holding layer 1 fixed must leave raw q byte-identical. Failure is a C1 falsifier.

## 2. Three compared minimal adapters

Let `b(o)=1-|E-2o|/E` be accepted division balance and `r(o)=1-b(o)=|E-2o|/E` be resisted inequity. All adapters share accepted targets `(payoff/o_max,b(o),1,F-04)` and the same material/safety rejection targets.

| Formalization | ID / config key | Rejection fairness | Rejection relationship | Assessment |
|---|---|---:|---:|---|
| C3 normative | `UG-ADAPTER-C3-NORM-RESISTED-INEQUITY-v1` / `normative_resisted_inequity_v1` | `r(o)` | 0 | Selected: offer/action-sensitive, bounded, priority-free, parsimonious complement of accepted balance. |
| A zero_exchange | `UG-ADAPTER-C3-SENS-ZERO-EXCHANGE-v1` / `sensitivity_zero_exchange_v1` | 0 | 0 | Retained sensitivity. It cannot distinguish rejection of equal and highly unequal offers. |
| B neutral_no_exchange | `UG-ADAPTER-C3-SENS-NEUTRAL-NO-EXCHANGE-v1` / `sensitivity_neutral_no_exchange_v1` | .5 | .5 | Retained sensitivity. It is constant and its relationship .5 does not encode failed agreement. |

No fourth adapter, convex mixture or per-offer switch is admitted. `selected_adapter_convention` is mandatory and has no default. It is the sole source of candidate and realized q for the run. N is allowed for `run_purpose` in `{confirmatory_frame, sensitivity, structural_fixture}`; A/B only for `run_purpose=sensitivity`. Missing selection, A/B outside sensitivity, or candidate/realized mismatch fails hard. A/B are not alternative reference defaults.

## 3. Normative formula and channel meanings

For action `accept`:

- `q_material=payoff_i/8`;
- `q_fairness=b(o)`;
- `q_relationship=1` because agreement occurred;
- `q_safety=F-04` inverse normalized ex-post unilateral regret.

For action `reject`:

- `q_material=0` because no exchange occurred;
- `q_fairness=r(o)` because the inequitable proposed split was resisted;
- `q_relationship=0` because agreement failed;
- `q_safety=1` for proposer and `1-o/8` for responder under the existing realized-response F-04 convention.

The fairness label now covers two action-contingent fairness-relevant consequences: realized balance on acceptance and resistance to inequity on rejection. It does not mean moral worth, procedural justice, desert, entitlement or punishment. The complement is symmetric: rejecting an advantageous but unequal offer 8 receives the same fairness score as rejecting offer 2. This is coherent with the existing symmetric balance channel but is a disclosed limitation.

## 4. Bounds, monotonicity and extreme cases

- Every raw target lies in `[0,1]`.
- On the legal grid, `b(o)` lies in `[.4,1]` and `r(o)` in `[0,.6]`.
- `r(o)` is nondecreasing in inequity `|E-2o|`, symmetric around 5, zero at 5, and .6 at legal endpoints 2 and 8.
- It is decreasing in raw offer on 2..5 and increasing on 5..8. Any assertion of global raw-offer monotonicity is false.
- Hypothetical offers 0 and 10 would give `r=1`, but they are outside the legal grid and cannot appear in an episode.
- Offer 5: accept `(fairness,relationship)=(1,1)`; reject `(0,0)`.
- Offers 2/8: accept fairness .4; reject fairness .6.
- Offers 3/7: accept fairness .6; reject fairness .4.

`UG_OUTCOME_TABLE_R1C5.csv` enumerates all `3 x 7 x 2 x 2 = 84` adapter/offer/action/role vectors and their allowed contexts. No future offer, unobserved response or opponent private state appears in a row.

## 5. Priority-to-choice path without circularity

For the responder only, F-35 builds two side-effect-free one-step projections from the same pre-state, one for each current legal action under the run's single explicitly selected adapter. N is used for `run_purpose` in `{confirmatory_frame, sensitivity, structural_fixture}`; A/B affect both candidate evaluation and realized update only in separately keyed sensitivity runs. F-35 compares projected signed appraisal per channel and records `z_k in {-1,0,+1}`.

Executable inputs are the post-clipping binary64 priorities `p_clip,k`. In fixed K order compute:

- `N_VS = math.fsum(p_clip,k * z_k)`;
- `P_VS = math.fsum(p_clip,k)`;
- `D_VS = N_VS / P_VS`, diagnostic only.

`N_VS>0.0` accepts; `N_VS<0.0` rejects; `N_VS==0.0` is a tie and rejects. The logged category comes from N and cannot be recomputed from D or a second normalized-term sum. No epsilon is used. Since `P_VS>0`, the mathematical normalized score is sign-equivalent, while the numerator representation avoids the C3 binary64 cancellation defect.

Candidate projections never mutate state. After the final action, the realized raw q is recomputed through the same selected adapter and F-05..F-11 run once. Candidate `N_VS/D_VS` and realized `V` are not added, averaged or fed into each other. This is why using the same fixed priority vector in two temporally distinct evaluations is not double counting of one update.

## 6. Worked profiles at the same offer

Use offer 2 and common pre-state `v_k=.5`. The projected signed appraisals are:

- accept: `(-7/40,-7/100,7/20,7/20)`;
- reject: `(-7/20,7/100,-7/20,7/40)`.

Thus `z=(+1,-1,+1,+1)` in K order. Normalized profile weights and decisions are:

| Profile | p_clip | N_VS | D_VS | E proposal |
|---|---|---:|---:|---|
| material_high | `(1.5,.5,.5,.5)` | `2` | `2/3` | accept |
| fairness_high | `(.5,1.5,.5,.5)` | `0.0` | `0.0` | reject by exact tie rule |
| relationship_high | `(.5,.5,1.5,.5)` | `2` | `2/3` | accept |

With `m=-.5,f=0`, neutral personality and high intensity, all three common states have `iota=-.75`, `theta=.63`, so hybrid selects E and the final actions differ exactly as above. In `emotional_only`, E is final directly. In neutral hybrid, R is selected and all profiles accept; this masking null is mandatory.

If rejection is externally fixed for diagnostic comparison, post-outcome F-09 valence from neutral v is `-77/400` for material_high, `-21/400` for fairness_high, and `-77/400` for relationship_high. The fairness profile therefore evaluates the same rejection less negatively, while F-35 regards reject as non-worse and resolves the exact action tie toward reject. C3 does not claim that post-outcome valence is positive.

## 7. Analytic reductions and limits

For fixed legal `v`, F-05 followed by F-07/F-08 is strictly increasing in q on `[0,1]`. Below v the slope is `alpha/max(epsilon,v)>0`; above v it is `alpha/max(epsilon,1-v)>0`; both pieces meet at zero. This remains true at v=0 and v=1. Therefore `z=sign(q_accept-q_reject)` for every legal state. The F-35 directional vote does not depend on current values, mood, fatigue, personality or intensity. F-14/state history remains a separate source of branch selection and later dynamics.

Consequences:

1. At N/B endpoint offers, `N_VS=p_m+p_relationship+p_safety-p_fairness`. Clipping implies `N_VS>=3(0.5)-1.5=0`; normative rejection occurs only at the tie boundary. There is no legal negative-side priority neighbor. With fairness replaced by `nextafter(1.5,-inf)=0x1.7ffffffffffffp+0`, N is `2^-52`; with material replaced by `nextafter(.5,+inf)=0x1.0000000000001p-1`, N is `2^-53`; both accept. A helper-level negative N tests the reject branch without being mislabelled a legal model fixture.
2. Adapter A has four positive votes and always proposes accept on the legal grid.
3. N and B have identical proposal partitions on the legal grid, despite different q magnitudes, state updates and possible later/F-14 consequences.
4. Responder material and safety action gaps are both `o/8`; they vote in the same payoff direction. They retain separate named weights, but this is directional redundancy, not `pbar` double counting.
5. `material_only` changes realized applied nonmaterial targets at F-32. It does not remove nonmaterial raw candidate vectors or votes from F-35.

Prospective oracle: repeat every adapter/offer/profile proposal at neutral v, an interior nonneutral v, all-zero v and all-one v; proposal partitions must be invariant. N/B proposals must match cell-for-cell. These are structural oracles, not claims of trajectory prevalence.

## 8. No strategic-reflection claim

F-35 compares only two deterministic current consequences available to the responder after observing the current offer. It has no future horizon, transition rollout, counteroffer, proposer-response function, opponent state, belief, recursion, learning or equilibrium calculation. The proposer remains unable to query a future response. Calling this planning, opponent modelling or strategic reflection is a contract violation.

## 9. Falsifiers

The C3 semantics fail if any of the following occurs:

1. raw q changes when only priorities/state/impulse/appraisal changes;
2. any target leaves `[0,1]` or any legal table row disagrees with F-31C3;
3. rejected relationship is nonzero under the normative adapter;
4. rejected fairness is not symmetric/monotone in inequity as specified;
5. priorities enter raw targets, `N_VS` weights a vote more than once, or D is used as a second branch sum;
6. candidate evaluation mutates state or uses a future/unobserved input;
7. `N_VS==0.0` is not logged as tie/reject, sign/category is recomputed from D, or exact F-14 equality does not select R;
8. A/B is used outside sensitivity, selection is implicit, candidate/realized adapters differ, adapters are mixed within a trajectory, or IDs/keys alias;
9. the worked profile partition fails algebraic replay;
10. state-dependent F-35 vote, strict-negative legal normative score, independent N/B proposal partitions, or removal of nonmaterial candidate votes by `material_only` is claimed;
11. C3 is described as strategic reflection or as an empirical/psychological finding.
