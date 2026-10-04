# MODEL_SPEC_JOURNAL_V1_R1C6

- Specification ID: `EMBORA-MSJ1-2026-10-04-R1C6-v1.1`
- Review package ID: `EMBORA-R0PKG-2026-10-04-C6-v1.1`
- Claim contract: `EMBORA-CC-2026-09-24-R1C5`
- Status: **C6 NUMERICAL CANDIDATE / NOT_ADOPTED; TARGETED R0 AND AUTHOR U1 ADDENDUM PENDING**
- Model family: prospective `journal_reference_v1`; no implementation or empirical evidence is asserted.
- Normative UG adapter: `normative_resisted_inequity_v1`. C2 adapters A/B are sensitivity-only and cannot be selected as the reference rule.

<a id="s00"></a>

## S00 — Authority, scope and normative ownership

C6 v1.1 responds only to R0-C6-P1-01/P2-01/P2-02 under Coordinator disposition EMBORA-COORD-R0C6-DISPOSITION-2026-10-04-v1.0. Preexisting P2-C5-P1-01 remains CONFIRMED OPEN. C5 was independently reviewed PASS_TO_U1 and author U1 APPROVED. C5 artifacts and U1 remain unchanged. Author has not adopted C6. Owner arithmetic checks are specification fixtures, not production conformance, independent R0 or empirical evidence.
NUMERICAL_CONTRACT_C6.md is the sole proposed numerical policy; PARAMETER_TABLE_R1C6.yaml is the derivative schema. Other normative scientific sources below retain exact C5 bytes/IDs under UPSTREAM_C5. Their historical pending labels do not determine live gates. Claims/frame/adapters remain pinned.

Normative ownership is exclusive:

| Subject | Sole normative source |
|---|---|
| Equations, branches, clipping, event timing, payloads, invariants, test-oracle definitions | This file, S01–S12; formula IDs F-01…F-35 |
| Numeric constants, closed enums, parameter domains, serialized reference defaults | `PARAMETER_TABLE_R1C6.yaml` |
| Exact baseline policies, comparator scope, deterministic condition frame and pairing roster | `BASELINE_AND_COMPARATOR_MATRIX_R1C5.md`, B01–B05 |
| Estimands, exclusions, rankings, multiplicity, sensitivity and claim promotion | `CLAIM_CONTRACT_R1C5.md`, C0–C5 |
| Historical formula/code provenance and mapping to future acceptance tests | `FORMULA_CODE_TRACEABILITY_R1C5.csv`; pointers are historical, not new code |

Tables of numeric examples are derived oracles, never an alternative definition. A mismatch between an oracle and its normative formula is a defect requiring a new version, not permission to choose one silently. Other documents reference these sources instead of redefining formulas.

Frozen C1-C5 remain unchanged. Exact changes and unchanged section hashes are in C5_TO_C6.diff and PINNED_SECTIONS_C6.json; dependencies in AUTHOR_IMPACT_AND_DEPENDENCIES_C6.md. No scientific equation, constant, adapter, F-35 scientific choice, claim or finite frame changes.

<a id="s01"></a>

## S01 — Numeric and state domain

Write clip[a,b](z)=min(b,max(a,z)). Validate finite inputs and declared domains before clipping. Scientific equations and exact rational fixtures remain real layer I oracles, including +/-7/40. NUMERICAL_CONTRACT_C6 defines layer R (real equations on rounded inputs) and layer B (ordered executable graph). Continuous implementation comparisons retain abs/rel 1e-12 against independent B; I/R/B bounds are separate diagnostics. Identity, votes, categories and branches are exact, branch tolerance zero. F-35 retains fixed-K math.fsum and N-only sign/tie. The numerical policy explicitly defines RN nodes, identity, no FMA/fast-math/reassociation and qualified runtime assumptions; no universal bitwise promise.

State x_i(t-1) is the immutable state entering round t; x_i(t) is the state after its single outcome update. This eliminates C1's ambiguous reuse of t as both the first round and the initialized state. The ordered value keys K are `material, fairness, relationship, safety` (YAML). v_k∈[0,1], desired d_k=1, raw priorities p_k are positive finite reals, mood m∈[-.5,.5], fatigue f∈[0,1]. Resources and aggregates are derived, never independently chosen:

- **F-06:** pbar_k=clip[p_min,p_max](p_k)/Σ_l clip[p_min,p_max](p_l). Sum in K order. No second priority renormalization in appraisal.
- **F-24:** r=1−f.
- **F-25:** W=Σ_k pbar_k v_k.
- **F-26:** Wtilde=clip[wellbeing_min,wellbeing_max](2W−1).
- **F-27:** S=lambda_W Wtilde+lambda_m m−lambda_f f.
- **F-28:** Initialize primary fields from YAML and derive every dependent field through F-06/F-24–27. Under reference defaults the derived oracle is (pbar_k=.25,r=1,W=.5,Wtilde=0,S=0).

The lambda parameters in the behavioral model are fixed at reference values. C3 readout sensitivity never feeds an alternative S into decisions. Priority sensitivity is a model-parameter intervention and requires new paired trajectories later; it is not a relabelling of existing states.

Legal state ≠ reachable state from neutral initialization. A state injected for a structural oracle is labelled `structural_fixture`; claims about prevalence use only trajectories starting in the prespecified frame. No free changes to v,m,f are permitted in confirmatory episodes.

<a id="s02"></a>

## S02 — Games, roles and outcomes

Agent identity is 1 or 2; seat is 1 or 2; seat assignment is an explicit bijection. In UG seat 1 is proposer, seat 2 responder. A role swap starts a separate reset episode. Agent identities retain their assigned personality/priority settings through a swap. History is in seat order.

<a id="s02-pd"></a>

### S02-PD

Simultaneous C/D game. Payoff table in seat order:

| a1 | a2 | π1 | π2 |
|---|---|---:|---:|
| C | C | 3 | 3 |
| C | D | 0 | 5 |
| D | C | 5 | 0 |
| D | D | 1 | 1 |

<a id="s02-bos"></a>

### S02-BoS

Simultaneous O/F game:

| a1 | a2 | π1 | π2 |
|---|---|---:|---:|
| O | O | 3 | 2 |
| O | F | 0 | 0 |
| F | O | 0 | 0 |
| F | F | 2 | 3 |

**F-20:** c_t=O for odd t, F for even t; round origin is 1 on every reset. Both model proposals equal c_t for all kinds and legal states. The confirmatory horizon is even (YAML). For T=2h both convention agents receive 5h; for T=2h+1 they receive (5h+3,5h+2). Odd T is allowed only in structural parity fixtures. A payoff imbalance under a nonconvention opponent is not fixed by even T; seat-specific reporting remains mandatory.

BoS is deterministic coordination and adapter/state control. Its model actions cannot identify arbitration, override or any state-to-action effect even when an opponent uses another policy. State and threshold variation remain observable diagnostics. No emergent-coordination or alternation-novelty claim.

<a id="s02-ug"></a>

### S02-UG

Sequential game with endowment E and exact integer offer grid O from YAML. One proposer offer o and one responder y∈{accept,reject} form a round. If accepted, payoffs are (E−o,o); otherwise (0,0). No offer zero, fractional offer, hidden counteroffer or within-round role change is legal. Every grid member is distinct, ordered, and exactly equal to the frozen grid; the adapter uses the same grid.

<a id="s03"></a>

## S03 — Pre-decision quantities and proposals

All formulas use x_i(t−1), with interventions S08 already projected where applicable.

**F-12:** For hybrid and emotional_only, iota=clip[impulse_min,impulse_max](chi_2(b_m m+b_f f+b_W(W−W_center))). For rational_only set iota=0; log both `impulse_mode=zero_by_kind` and the resulting zero. This retains C1's kind difference and is not an ablation. All proposals are still computed for trace. No fixed baseline needs an internal model state.

**F-13:** theta=clip[theta_min,theta_max](chi_1(1−a_f f)+M(m)+R(r)), where M(m)=m_negative_offset if m<m_negative_cut, m_positive_offset if m>m_positive_cut, and 0 otherwise; R(r)=resource_offset if r<resource_cut, otherwise 0. Equalities choose zero modifiers. chi mappings and all constants have their sole values in YAML.

<a id="s03-p"></a>

### S03-P — Exact model policy matrix

| Game / role | Emotional proposal aE | Rational proposal aR |
|---|---|---|
| PD, hybrid or emotional_only | F-15: C iff iota≥pd_emotional_cut, else D | F-16: C iff S≥pd_rational_state_cut, else D |
| PD, rational_only | F-15 evaluated at zero impulse, diagnostic | F-16: D |
| BoS, every kind and seat | F-20: c_t | F-20: c_t |
| UG proposer, hybrid or emotional_only | F-17 below | F-19: ug_hybrid_system2_offer |
| UG proposer, rational_only | F-17 at zero impulse, diagnostic | F-19: ug_rational_only_offer |
| UG responder, every kind | F-18/F-35 value-sensitive current-action evaluation | F-19: accept (all legal offers are positive) |

**F-17:** z=ug_offer_center+clip[ug_proposer_impulse_min,ug_proposer_impulse_max](iota). Select the o∈O minimizing the lexicographic pair (|o−z|,o). Thus lower offer wins an exact distance tie. Enumeration order is irrelevant.

**F-18, value-sensitive responder proposal:** for the current legal offer, evaluate the two legal current actions by F-35. The E-branch proposal `aE` is the resulting value-sensitive action. The label E is retained as a branch/schema identifier; this rule is not claimed to be a validated human emotion model. The R proposal remains the simple payoff-oriented F-19 rule that accepts every positive legal offer. Neither rule predicts a future offer or opponent response, and neither is a strategic best response.

**F-14:** Hybrid chooses aE iff |iota|>theta, otherwise aR. Equality chooses R. Emotional_only chooses aE; rational_only chooses aR. Log selected branch independently of proposal equality. `proposals_differ` compares exact canonical action objects. Selected E with aE=aR does not identify a behavioral arbitration effect.

<a id="s03-u"></a>

### S03-U — F-35 current-action appraisal and exhaustive choice oracle

For a UG responder with current legal offer `o`, enumerate only the two legal present actions `a in {accept,reject}`. `selected_adapter_convention` is required explicitly before agent construction and is the sole source of both candidate and realized raw vectors for the whole run. For each action obtain `q^(a)(o,role)` from that selected adapter and compute a side-effect-free one-step projection from the same immutable pre-state. Normative N is allowed for `confirmatory_frame`, `sensitivity` and `structural_fixture`; A/B are allowed only for `run_purpose=sensitivity`. An implicit adapter, A/B in confirmatory or structural context, a per-action override, or any candidate/realized adapter mismatch fails hard before the affected round is executed.

`vhat_k^(a)=clip[0,1]((1-alpha)v_k+alpha q_k^(a))`, `Deltahat_k^(a)=vhat_k^(a)-v_k`, and `uhat_signed,k^(a)` by the exact F-07/F-08 branch and denominator rules. No projection is committed, logged as an outcome, or allowed to affect the opponent.

Define `cmp(x,y)=+1` if `x>y`, `0` if `x=y`, and `-1` if `x<y`, with exact branch comparisons. Then:

- **F-35:** `z_k(o)=cmp(uhat_signed,k^(accept),uhat_signed,k^(reject))`. Let `p_clip,k` be the validated post-clipping binary64 priority in frozen K order. Compute `N_VS=math.fsum(p_clip,k*z_k for k in K)`, `P_VS=math.fsum(p_clip,k for k in K)`, and the diagnostic `D_VS=N_VS/P_VS` by one binary64 division.
- The branch and its logged sign/tie category are derived only from `N_VS`: accept iff `N_VS>0.0`; reject iff `N_VS<0.0`; `N_VS==0.0` is `tie_reject`. No epsilon, tolerance, sign check on `D_VS`, or resummation of normalized `pbar_k*z_k` is permitted.
- `P_VS>0`; therefore the real-valued signs of `N_VS` and normalized `D_VS` are algebraically equivalent. `D_VS` remains in `[-1,1]` and is logged only as a scale-normalized diagnostic.
- Priorities occur exactly once in F-35. They do not enter raw targets, candidate projections or channel comparisons. Division by `P_VS` does not introduce a second weighting.

The directional comparison prevents larger numeric range in one operational channel from silently determining all trade-offs. It intentionally discards between-channel cardinal magnitude at the final vote; that design choice is a falsifiable contract limitation. F-09 remains the cardinal post-outcome valence after the actually realized action and is not added to F-35.

The following partition is valid for **every legal pre-state**, not only `v_k=.5`. For fixed `v`, the real-valued F-07/F-08 signed-appraisal map is strictly increasing in candidate `q` on `[0,1]`, including `v=0`, `v=1` and epsilon-denominator branches. Hence `z_k=sign(q_accept,k-q_reject,k)` and is independent of current value state, mood, fatigue, personality and intensity. Offers 2 and 8 under N/B have `(material:+1,fairness:-1,relationship:+1,safety:+1)`; offers 3–7 have `(+1,+1,+1,+1)`. Therefore:

| Priority profile | offer 2 | offers 3–7 | offer 8 | exact N_VS / D_VS at 2/8 |
|---|---|---|---|---:|
| equal | accept | accept | accept | `2 / 1/2` |
| material_high | accept | accept | accept | `2 / 2/3` |
| fairness_high | reject (tie) | accept | reject (tie) | `0.0 / 0.0` |
| relationship_high | accept | accept | accept | `2 / 2/3` |
| safety_high | accept | accept | accept | `2 / 2/3` |

For fairness_high, binary64 inputs `(0.5,1.5,0.5,0.5)` and fixed-order votes `(+1,-1,+1,+1)` yield `math.fsum(0.5,-1.5,0.5,0.5)==0.0`; the exact scientific fixture and executable tie/category therefore agree. Recomputing the sign from normalized sixths is forbidden because it recreates the C3 cancellation defect. Permuting serialized map keys changes neither the K-vector nor the result.

This tie is the boundary of the legal clipped-priority domain: `N_VS=p_m+p_r+p_s-p_f>=3p_min-p_max=0`. Replacing `p_f=1.5` by its immediate lower binary64 neighbor, or replacing any other `.5` by its immediate higher neighbor, gives `N_VS>0` and accept. No legal priority perturbation gives `N_VS<0`; a negative-number branch oracle is therefore helper-level only and must not be described as a legal model state.

Executable qualification: arbitrary nextafter targets need not remain strictly ordered after rounding. The frozen UG grid retains its exact votes by the C6 separation proof (same-offer/channel minima N=1/5, A=1/4, B=1/10; global executable margin alpha_B/10 - 2*(8eta/epsilon_B+4alpha_B*eta/epsilon_B)>0.0349999958255614). Code still compares rounded appraisals, not raw q. Candidate and realized paths share the same helper and exact q=v identity; vhat preserves the IEEE input-v sign of zero while Delta and signed/absolute urgency are +0. Actual I/conversion/total residuals are unavailable for unknown-origin rows; the reference/schema keep R/B/B-R and do not invent I. Fixture enumeration supplements, rather than replaces, the uniform proof.

Under sensitivity A all four votes are positive for every legal offer, so A always proposes accept. N and B have identical proposal partitions across the legal grid, although their candidate magnitudes, realized updates, subsequent state/history and F-14 branch selection can differ. For the responder the material and safety action gaps are both `o/8`: they cast the same payoff direction under separately named priorities. This is directional redundancy, not repeated multiplication of `pbar`. The `material_only` switch acts at F-32 on realized applied targets; it does not delete fairness, relationship or safety from F-35 candidate voting.

F-14 still owns final arbitration. Neutral hybrid has `iota=0` and selects R, so it accepts every offer even where the fairness-high E proposal rejects. A legal active fixture is `v_k=.5,m=-.5,f=0`, neutral personality, high intensity: `iota=-.75`, `theta=.63`, so E is selected. Holding offer, state and history fixed at offer 2, material_high and relationship_high accept while fairness_high rejects by the exact tie rule. Emotional_only produces the same profile-specific final actions without needing a branch-selection fixture. These examples prove structural representability only, not neutral-start prevalence.

Role boundary: F-35 exists only for the responder because the current response deterministically selects between two present outcomes. The proposer continues to use F-17/F-19 and cannot evaluate an unobserved future response. Adding responder F-35 therefore does not create forward planning, opponent modelling, recursive reasoning or strategic reflection.

Proposer helper boundary oracle: over iota∈[−1.5,1.5], offers selected are 3 at iota=−1.5, 4 for −1.5<iota≤−.5, 5 for −.5<iota≤.5, 6 for .5<iota≤1.5. Offer 3 and the outer impulse clips are unreachable under the production-state envelope. Offers 2,7,8 remain legal baseline offers, not missing actions. Post-U1 tests must distinguish legal action grid from actions producible by one policy.

<a id="s04"></a>

## S04 — Exact payload, event order and mutation contract

<a id="s04-o"></a>

### S04-O — Observation allowlist

The decision API receives only `{public_observation, own_pre_state}`. `own_pre_state` is an immutable copy of S01 fields for that agent, including its own fixed d,p,personality,intensity; no opponent internals. Strict public observation fields:

| Field | Type / meaning |
|---|---|
| schema_id | exact YAML observation version |
| game | exact enum |
| round | integer 1…T |
| horizon | configured integer T |
| agent_id, seat, role | validated identity/seat/role relationship |
| game_parameters | exact game descriptor: PD/BoS payoff table; UG endowment and grid |
| legal_actions | exact ordered canonical actions for role |
| history | immutable list of complete public rounds 1…t−1 |
| current_offer | absent for PD/BoS and UG proposer; required integer for UG responder |

Each public history entry contains exactly `{round, actions_by_seat, payoffs_by_seat}`; UG actions include the realized offer and response. The realized actions reveal past responses, but do not reveal how either proposal was formed. `round` is consecutive; a truncated, duplicated or future history is invalid.

Deny every other field, including opponent v,d,p,m,f,r,W,Wtilde,S, personality/intensity, opponent aE/aR/iota/theta/selected branch, current response/acceptance/payoffs, raw or applied q, appraisal, post-state, future history, RNG state and trace/logger object. UG proposer cannot read current responder state or future response. UG responder can read the actual current offer only, not the proposer's private pre-state/decision trace. Extra nested fields fail too. These restrictions are implemented by constructing a fresh typed payload, never filtering a shared mutable result object in place.

<a id="s04-e"></a>

### S04-E — F-29, normative sequence

1. Validate complete config before constructing agents. At each round validate identities, legal pre-state and complete t−1 history. Snapshot both pre-states and history; use frozen references.
2. PD/BoS: build both observations from that same history. Decide seat 1 then seat 2; both decisions are pure, so this computational order provides no information advantage. Validate each returned proposal/action.
3. UG: build proposer observation; compute and validate both proposer proposals and final offer; create a **fresh** responder observation with `current_offer` equal to that validated final offer; decide and validate responder proposals and response. No state update or external game execution occurs between decisions.
4. Assert exact final action identities and parameters again; execute external game **once**. It returns a single immutable public outcome consistent with S02.
5. Construct **both** immutable GameResult objects from the same outcome before either agent updates. Fields are `{schema_id,game,round,agent_id,seat,role,actions_by_seat,payoffs_by_seat}`. Check payoffs against S02; reject malformed/out-of-range outcomes instead of clipping them into q.
6. Compute seat 1 post-state/trace from its saved pre-state and result, then seat 2 from its saved pre-state and result. Neither may observe the other's updated state. Exactly one update per agent per round. Reject duplicate or stale observation **before** any mutation.
7. Atomically commit both post-states, append one public history entry and one complete private round record. If any stage fails, mark episode invalid, preserve failure evidence; do not partially commit a round or silently resume.

`decide()` cannot mutate even a `last_decision` field or consume model RNG; the orchestrator owns pending decision traces. Fixed baselines are pure functions of observation/history. No outcome update happens on an offer alone. After commit, the next round can read the previous public outcome.

<a id="s04-l"></a>

### S04-L — Required private log

One round record holds identity/config/spec IDs; the explicit selected adapter ID/key and run purpose; immutable input observations or their reconstructable serialized content; both pre-states; iota and theta; for UG responder both candidate raw vectors with their adapter ID, projected `vhat/Deltahat/uhat_signed`, K-ordered `z`, binary64 `p_clip`, `N_VS`, `P_VS`, diagnostic `D_VS`, and one `N_VS`-derived category in `{positive_accept,negative_reject,tie_reject}`; aE,aR,selected branch,proposals_differ,final actions; both realized outcomes; realized raw q with the same selected adapter ID and applied q_star; Δ,u_signed,u,V,L,k_star,rho; sigma,Csup_raw,Csup_applied; preclip mood/fatigue; committed post-states; intervention ID/target agent; event counters; failure status. Candidate projections and realized-update fields are distinct and cannot overwrite each other. `D_VS` never supplies its own sign/tie label. `k_star` is a value-key enum or JSON null (never string `none`). Distinct fields `iota` and `rho` are mandatory.

<a id="s05"></a>

## S05 — Outcome-to-value adapter

<a id="s05-g"></a>

### S05-G — F-01–F-04, simultaneous games

Use exact legal payoffs from S02. For each seat i, min_i,max_i are extrema over all legal outcomes. **F-01:** n_i=clip[0,1]((π_i−min_i)/(max_i−min_i)); if max_i=min_i the helper convention is 1, but that branch is unreachable for the three declared games. q_material=n_i.

For PD/BoS only, **F-02:** q_fairness=1−|n_i−n_j|. This is explicitly an operational payoff-equality score; PD mutual defection and BoS mismatch may have value 1. RD4 changes UG, not those historical simultaneous-game mappings; do not describe equality as social desirability.

**F-03 (PD/BoS):** B_i(a_i)=max_{a_j}π_i(a_i,a_j), L_i(a_i)=min_{a_j}π_i(a_i,a_j). q_relationship=clip[0,1]((π_i−L_i)/(B_i−L_i)). Equal-slice helper convention is 1; all PD/BoS own-action slices have positive range. This is conditional partner support, not a relationship-quality measure.

**F-04 (all games):** g_i=max_{a'_i}π_i(a'_i,a_j)−π_i(a_i,a_j); G_i=max over all legal outcomes of g_i. q_safety=clip[0,1](1−g_i/G_i), with helper fallback 1 if G_i=0. G_i>0 in each declared game/role. Safety names *inverse normalized ex-post unilateral regret*, not physical or psychological safety.

For sequential UG, F-04 fixes the **realized response** when evaluating alternative proposer offers; it does not query how the responder would react to a different offer. For the responder it fixes the current offer and compares accept/reject. It is a descriptive payoff-table counterfactual, not a best response to a complete contingent strategy. This retained C1 convention is now explicit; any strategic-policy regret would be a different model.

Derived simultaneous-game q oracles (K order), completing AT-ADAPTER-PDBOS:

| Game/outcome | q seat 1 | q seat 2 |
|---|---|---|
| PD CC | (.6,1,1,0) | (.6,1,1,0) |
| PD CD | (0,0,0,.5) | (1,0,1,1) |
| PD DC | (1,0,1,1) | (0,0,0,.5) |
| PD DD | (.2,1,0,1) | (.2,1,0,1) |
| BoS OO | (1,2/3,1,1) | (2/3,2/3,1,1) |
| BoS OF | (0,1,0,1/3) | (0,1,0,1/3) |
| BoS FO | (0,1,0,0) | (0,1,0,0) |
| BoS FF | (2/3,2/3,1,1) | (1,2/3,1,1) |

Their payoff ranges are [0,5] (PD) and [0,3] (BoS); maximum regret is 2 (PD both seats) and 3 (BoS both seats). No declared game exercises a zero-payoff-range or zero-max-regret branch.

<a id="s05-u"></a>

### S05-U — F-31C3, normative UG outcome mapping

For legal offer `o` define the observable, priority-free quantities

`b(o)=1-|E-2o|/E` (accepted division balance), `r(o)=1-b(o)=|E-2o|/E` (resisted inequity), and `I_acc=1` for accept, `0` for reject. Under normative adapter ID `UG-ADAPTER-C3-NORM-RESISTED-INEQUITY-v1` / config key `normative_resisted_inequity_v1`, for either role:

`q_material=pi_i/o_max`;

`q_fairness=I_acc*b(o)+(1-I_acc)*r(o)`;

`q_relationship=I_acc`;

`q_safety=F-04`.

For rejection, payoffs are zero, hence `q_material=0`; failed agreement is preserved as `q_relationship=0`; fairness is offer/action-dependent `r(o)`, never a constant and never a function of priorities, values, impulse or appraisal. For acceptance, fairness is the realized balance `b(o)` and relationship is agreement `1`. The same numeric fairness consequence applies to both roles, but role semantics differ: for the responder rejection records resistance to the currently observed inequity; for the proposer it records that the proposed inequity did not become an accepted division. It is an outcome score, not moral praise or blame.

All raw targets depend only on `(E,O,o,role,action,legal payoffs)`. They cannot read `p,pbar,v,d,m,f,W,S,iota,theta,V,L,k_star`, proposal branch, future offers or future history. Priority dependence begins only at F-09 for a realized outcome and at F-35 for responder action evaluation.

Derived UG extrema: payoff range [0,8] for either role; G_proposer=6 and G_responder=8. Accepted safety is 1−(o−2)/6 for proposer and 1 for responder; rejected safety is 1 for proposer and 1−o/8 for responder. These are table oracles, not a second definition.

Bounds: `b,r,q_relationship,q_safety in [0,1]`; legal-grid `b in [.4,1]`, `r in [0,.6]`. `r` is nondecreasing in inequity `|E-2o|`, symmetric about `E/2`, zero at offer 5 and .6 at legal endpoints 2 and 8. It is not monotone in the raw offer across both sides of equality; claiming raw-offer monotonicity is a falsifier. At hypothetical full-allocation endpoints 0/10, outside the frozen grid, `r=1`; those are boundary proofs, not legal actions.

Derived UG extrema remain: payoff range [0,8] for either role; `G_proposer=6`, `G_responder=8`. Accepted safety is `1-(o-2)/6` for proposer and 1 for responder; rejected safety is 1 for proposer and `1-o/8` for responder. F-04 fixes the realized response and does not model strategic reaction.

<a id="s05-t"></a>

### S05-T — Complete UG legal-outcome and sensitivity tables

`UG_OUTCOME_TABLE_R1C5.csv` is the exhaustive adapter-indexed authority matrix: 84 unique rows = 3 adapters x 7 offers x 2 actions x 2 roles, with payoffs, all four targets and allowed run purposes. Exactly one row is admitted for each `(selected adapter,role,offer,action)` in an authorized context. Accepted target values coincide across adapters but remain separately keyed vectors; rejected values follow the selected adapter. The compact tables here summarize the same matrix. q order is K. Each V,L entry shown for A/B is the exact neutral-state oracle with equal priorities and YAML reference alpha; A/B never define the C3 reference rule. From any listed q the neutral oracle has `Delta_k=alpha(q_k-.5)`, `u_signed_k=2Delta_k`, `rho=chi_2*V`, and `k_star` by F-10. These are algebraic specification oracles, not run evidence.

All fractions below are exact. Decimal examples elsewhere are exact terminating equivalents.

| o | y | q proposer | V proposer | L proposer | q responder | V responder | L responder |
|---:|---|---|---|---|---|---|---|
| 2 | accept, all adapters | (1, 2/5, 1, 1) | 49/200 | 7/25 | (1/4, 2/5, 1, 1) | 91/800 | 189/800 |
| 3 | accept, all adapters | (7/8, 3/5, 1, 5/6) | 1099/4800 | 1099/4800 | (3/8, 3/5, 1, 1) | 273/1600 | 343/1600 |
| 4 | accept, all adapters | (3/4, 4/5, 1, 2/3) | 511/2400 | 511/2400 | (1/2, 4/5, 1, 1) | 91/400 | 91/400 |
| 5 | accept, all adapters | (5/8, 1, 1, 1/2) | 63/320 | 63/320 | (5/8, 1, 1, 1) | 91/320 | 91/320 |
| 6 | accept, all adapters | (1/2, 4/5, 1, 1/3) | 133/1200 | 203/1200 | (3/4, 4/5, 1, 1) | 217/800 | 217/800 |
| 7 | accept, all adapters | (3/8, 3/5, 1, 1/6) | 119/4800 | 889/4800 | (7/8, 3/5, 1, 1) | 413/1600 | 413/1600 |
| 8 | accept, all adapters | (1/4, 2/5, 1, 0) | -49/800 | 189/800 | (1, 2/5, 1, 1) | 49/200 | 7/25 |
| 2 | reject normative | (0, 3/5, 0, 1) | — | — | (0, 3/5, 0, 3/4) | — | — |
| 3 | reject normative | (0, 2/5, 0, 1) | — | — | (0, 2/5, 0, 5/8) | — | — |
| 4 | reject normative | (0, 1/5, 0, 1) | — | — | (0, 1/5, 0, 1/2) | — | — |
| 5 | reject normative | (0, 0, 0, 1) | — | — | (0, 0, 0, 3/8) | — | — |
| 6 | reject normative | (0, 1/5, 0, 1) | — | — | (0, 1/5, 0, 1/4) | — | — |
| 7 | reject normative | (0, 2/5, 0, 1) | — | — | (0, 2/5, 0, 1/8) | — | — |
| 8 | reject normative | (0, 3/5, 0, 1) | — | — | (0, 3/5, 0, 0) | — | — |
| 2 | reject A | (0, 0, 0, 1) | -7/40 | 7/20 | (0, 0, 0, 3/4) | -7/32 | 49/160 |
| 3 | reject A | (0, 0, 0, 1) | -7/40 | 7/20 | (0, 0, 0, 5/8) | -77/320 | 91/320 |
| 4 | reject A | (0, 0, 0, 1) | -7/40 | 7/20 | (0, 0, 0, 1/2) | -21/80 | 21/80 |
| 5 | reject A | (0, 0, 0, 1) | -7/40 | 7/20 | (0, 0, 0, 3/8) | -91/320 | 91/320 |
| 6 | reject A | (0, 0, 0, 1) | -7/40 | 7/20 | (0, 0, 0, 1/4) | -49/160 | 49/160 |
| 7 | reject A | (0, 0, 0, 1) | -7/40 | 7/20 | (0, 0, 0, 1/8) | -21/64 | 21/64 |
| 8 | reject A | (0, 0, 0, 1) | -7/40 | 7/20 | (0, 0, 0, 0) | -7/20 | 7/20 |
| 2 | reject B | (0, 1/2, 1/2, 1) | 0 | 7/40 | (0, 1/2, 1/2, 3/4) | -7/160 | 21/160 |
| 3 | reject B | (0, 1/2, 1/2, 1) | 0 | 7/40 | (0, 1/2, 1/2, 5/8) | -21/320 | 7/64 |
| 4 | reject B | (0, 1/2, 1/2, 1) | 0 | 7/40 | (0, 1/2, 1/2, 1/2) | -7/80 | 7/80 |
| 5 | reject B | (0, 1/2, 1/2, 1) | 0 | 7/40 | (0, 1/2, 1/2, 3/8) | -7/64 | 7/64 |
| 6 | reject B | (0, 1/2, 1/2, 1) | 0 | 7/40 | (0, 1/2, 1/2, 1/4) | -21/160 | 21/160 |
| 7 | reject B | (0, 1/2, 1/2, 1) | 0 | 7/40 | (0, 1/2, 1/2, 1/8) | -49/320 | 49/320 |
| 8 | reject B | (0, 1/2, 1/2, 1) | 0 | 7/40 | (0, 1/2, 1/2, 0) | -7/40 | 7/40 |

Required semantic checks:

- Offer 5: acceptance has fairness 1 and agreement 1; rejection has fairness 0 and agreement 0. Equal zero payoffs after rejection do not imply fairness.
- Offers 2 and 8: accepted balance is .4 and rejected resisted-inequity score is .6. The fairness channel therefore favors rejection at both equally inequitable legal endpoints, while material, relationship and responder safety favor acceptance.
- Offers 3 and 7: accepted fairness .6 exceeds rejected fairness .4. The action preference flips between inequity .4 and .6; the frozen integer grid contains no equality case.
- Rejected offers 2 and 8 give the proposer the same normative vector `(0,.6,0,1)`. This role-specific consequence does not imply the offer was optimal or virtuous; it exposes F-04's realized-response limitation.
- A `zero_exchange` uses rejected fairness/relationship `(0,0)`; B `neutral_no_exchange` uses `(.5,.5)`. Their IDs and config keys are distinct from the normative adapter; mixed-row execution is invalid.
- BoS mismatch still gives fairness 1 and relationship 0. C3 changes no PD/BoS semantics and authorizes no psychological generalization.

<a id="s06"></a>

## S06 — Values, appraisal and direct-domain coverage

**F-32:** q is the immutable validated output of S05. Compute a separate applied q_star: under full and all variants except material_only, q_star=q; under material_only, q_star_material=q_material and q_star_k=v_k for the other three keys. Never mutate q. Both vectors and switch identity are logged. In subsequent rounds raw q may differ if earlier interventions changed actions; same-q invariance is a same-input, one-step assertion.

**F-05:** v'_k=clip[0,1]((1−alpha)v_k+alpha q_star_k); Δ_k=v'_k−v_k. The clip is a bounded model operation, not validation. For valid inputs the convex combination is already in [0,1]. C6 executable graph adds common exact q_star=v identity and ordered literal RN nodes otherwise; no alpha-bound snap.

**F-07/F-08:** u_signed_k=min(1,|Δ_k|/max(epsilon,|d_k−v_k|)) if Δ_k>0; −min(1,|Δ_k|/max(epsilon,v_k)) if Δ_k<0; 0 if Δ_k=0. u_k=|u_signed_k|.

**F-09:** V=Σ pbar_k u_signed_k; L=Σ pbar_k u_k, evaluated in K order.

F-09 is evaluated once after the realized outcome and drives post-outcome reaction/state. F-35 is evaluated before the responder action over two side-effect-free candidate projections and drives only the E proposal. They share the priority vector but never add their scores together: candidate projections are discarded after choice, and the realized update is computed afresh from the one realized q. This temporal separation is the no-double-counting invariant.

**F-10:** w_k=pbar_k u_k. If every w_k=0, k_star=null. Otherwise choose the first key in YAML K order attaining max w_k; strict arithmetic equality, no fuzzy tie. Reordering serialized map fields must not alter the result. A tie between material and fairness selects material; a fairness/relationship tie with smaller other scores selects fairness.

**F-11:** rho=clip[reaction_min,reaction_max](chi_2·kappa·V). rho is post-outcome; it cannot change the current decision.

<a id="s06-d"></a>

### S06-D — F-07/F-08 domain proof and corrected R0 wording

The real-valued production model has d=1 and Δ=alpha(q_star−v), alpha fixed between 0 and 1. If v=1 then Δ≤0: a **positive** gain at exact desired value is unreachable. If v=0 then Δ≥0: a **negative** loss at zero is unreachable. From strictly interior neutral initialization and alpha<1, exact endpoints remain unattainable in finite exact-arithmetic time, though legal injected endpoint states are valid fixtures.

It does **not** follow that the epsilon-denominator branch is unreachable. In-domain counterexample: v=1−epsilon/2,q_star=1 gives Δ=alpha·epsilon/2>0 and denominator epsilon, so u_signed=alpha/2. Similarly v=epsilon/2,q_star=0 gives u_signed=−alpha/2. These are legal injected states; neutral-reachable finite-horizon prevalence is unknown. The broad epsilon-unreachable assertion in R0 is refined, not copied as a false proof.

For Δ>0, q_star−v≤1−v; for Δ<0, v−q_star≤v. Hence |u_signed|≤alpha under this update, including the epsilon case. The outer saturation at 1 is unreachable in production with fixed alpha<1. Likewise L≤alpha and |V|≤alpha; the generic [-1,1] output envelope is conservative. With current chi_2, rho clipping is unreachable in production. F-12 clipping is also inactive inside its tighter S03-U envelope. These clips are defensive helper branches, not active mechanisms offered as C3 evidence.

C6 executable qualification: exact-alpha inequalities above are real statements, not hard rounded scalar guards. Rounded vhat in [0,1] and urgency in [-1,1] remain exact guards; |u_B|<=alpha_B+8*2^-52/epsilon_B is a derived diagnostic envelope, never a comparison tolerance or clip. C6 independently separates input/arithmetic residuals, preserves exact identity and proves fixed-alpha rounded endpoint nonreachability, interior stagnation and finite input-conversion saturation. Neutral-frame prevalence remains unknown.

Helper domain for urgency tests is independently supplied finite prev,current,desired∈[0,1], epsilon>0, without requiring F-05 correspondence. Gain at prev=desired=.5,current=.6 activates epsilon and saturates at 1: valid helper-only, invalid production d and recurrence. A loss with prev=0,current<0 is invalid even as a helper and must fail, not be coerced. Helper tests do not count as production branch reachability.

<a id="s07"></a>

## S07 — Override proxy and common state update

**F-21:** sigma=1[aE≠a]; Csup_raw=sigma·|iota|. For no_suppression only, Csup_applied=0; otherwise Csup_applied=Csup_raw. Sigma is a proposal-override indicator; no subjective suppression is inferred.

**F-22:** m_preclip=mood_decay·m+rho/mood_scale; m'=clip[mood_min,mood_max](m_preclip).

**F-23:** f_preclip=f+fatigue_load_rate·L+fatigue_impulse_rate·min(impulse_abs_max,|iota|)/impulse_abs_max+suppression_cost_rate·Csup_applied−recovery_rate·(1−min(1,L)); f'=clip[0,1](f_preclip).

After any S08 projection, recompute F-24–27 from v',m',f'. Do not update aggregates from stale components. Constraints on all final fields are checked before commit.

At identical pre-state, observation, decision trace, outcome and exogenous inputs, full and no_suppression have identical current actions and raw q. Before fatigue clipping their fatigue difference equals suppression_cost_rate·Csup_raw. After clipping use the difference of the two clipped preclip values, not the unclipped increment. If sigma=0 their one-step outputs are identical. This null is **not** a statement about unequal states inherited from prior rounds: existing divergence can persist during a later sigma=0 round.

<a id="s08"></a>

## S08 — Single-path switch semantics

One immutable `variant` enum is allowed; no stacked switches. A causal contrast changes only the focal agent's variant; opponents retain their explicit reference configuration and respond normally to public history. All paths must share constructor, policy, adapter, update, logger and engine after U1.

| Variant | Sole intervention point |
|---|---|
| full | no intervention |
| no_suppression | F-21 cost application; raw sigma and cost retained |
| no_mood | project m to zero at initialization and each committed update; use that zero in all pre-decision formulas and aggregates; record unprojected mood update as diagnostic |
| no_fatigue | project f to zero and r to one at initialization and each committed update; use those values throughout pre-decision formulas/aggregates; record unprojected fatigue diagnostic |
| fixed_threshold | replace F-13 by clip[theta_min,theta_max](chi_1); still log F-13 reference threshold as a diagnostic |
| material_only | only F-32 applied targets |

For no_mood/no_fatigue, a one-step mechanism fixture starts from an identical *source* state but explicitly logs the projected decision state; unlike no_suppression these interventions can change same-round decisions. Confirmatory pairs initialize from the same neutral state, so no initial projection difference arises. “One switch” refers to one mechanistic intervention with all its specified descendants, not one arithmetic term everywhere.

Changing the UG adapter convention is a separate model-semantics sensitivity, not one of these five causal ablations. It must pair all other fields and must not be mixed into a full/ablation contrast. Historical mode comparisons are not single-path causal evidence.

<a id="s09"></a>

## S09 — Closed configuration and fail-hard validation

YAML contains all effective reference defaults; no fallback strings, aliases, coercion of types or unknown keys. A preparation layer may resolve *only* entries marked `default` into a fully serialized effective config. Required identifiers, game, both identities/seats/roles, baseline ID if relevant, `selected_adapter_convention` and `run_purpose` have no inferred default. Adapter selection occurs once per run before agent construction. N is valid for `run_purpose` in `{confirmatory_frame, sensitivity, structural_fixture}`; A/B are valid only for `run_purpose=sensitivity`. Candidate and realized q generation must both dispatch through that one selected adapter; a second candidate/realized adapter field is not a legal override. Missing or implicit selection, A/B in confirmatory/structural, per-row/per-action switching and any trace whose candidate or realized adapter differs from selection all fail hard. Construction receives a complete effective config, never implicit defaults. Allowed effective top-level fields are exactly the union of YAML `required_no_default` and `common_default_resolution`; model-agent fields are exactly the union of `required_agent_fields` and `model_agent_resolved_fields`; baseline-agent fields are exactly `required_agent_fields` plus `baseline_id`. Each agent's p is resolved from its selected priority profile **before** initial-state serialization; a supplied p that conflicts with that profile fails. The equal-p initial defaults apply only to the equal profile. Direct structural state/helper fixtures may supply positive raw p under S01 without pretending to be confirmatory frame configurations. Initial state fields and every derived field are serialized in the manifest after recomputation.

Validate (i) unknown game/kind/personality/intensity/variant/role; (ii) role-seat mismatch or duplicate identity; (iii) empty, repeated, shuffled or altered action grid; (iv) missing action fields, unknown action name, extraneous params, invalid integer offer, Boolean-as-integer, NaN/Inf; (v) horizon invalid or odd confirmatory BoS; (vi) malformed histories/payloads; (vii) missing value keys, out-of-domain state, inconsistent derived fields; (viii) unknown model mode, training=true, non-null DQN/refocus config; (ix) more than one variant; (x) missing/unknown/implicit adapter, any A/B adapter in a non-sensitivity run, or adapter mismatch across selection/candidate/realized fields; (xi) candidate q inconsistent with the selected adapter, role, current offer or action; (xii) projected quantities or votes inconsistent with that q/pre-state; (xiii) `N_VS`, `P_VS`, `D_VS`, category or action inconsistent with the declared binary64 `math.fsum` sequence.

Configuration errors fail before round 1; dynamically invalid actions/payloads fail before execution of that round, and duplicate outcomes before mutation. No output is replaced by first legal action, D, F, neutral personality or offer 5. Unknown/missing enum values are never accepted as defaults. A configured model clip remains legal only within validated input domains. An invalid episode is preserved as a failed artifact and cannot silently count as a valid observation.

<a id="s10"></a>

## S10 — Adapter identities and sensitivity boundary

Exactly three minimal formalizations are retained; only one is normative:

| Status | ID | Config key | Rejection fairness | Rejection relationship | Use |
|---|---|---|---|---|---|
| normative C3 | `UG-ADAPTER-C3-NORM-RESISTED-INEQUITY-v1` | `normative_resisted_inequity_v1` | `1-b(o)` | 0 | `confirmatory_frame`, `sensitivity`, `structural_fixture` |
| sensitivity A | `UG-ADAPTER-C3-SENS-ZERO-EXCHANGE-v1` | `sensitivity_zero_exchange_v1` | 0 | 0 | `sensitivity` only |
| sensitivity B | `UG-ADAPTER-C3-SENS-NEUTRAL-NO-EXCHANGE-v1` | `sensitivity_neutral_no_exchange_v1` | .5 | .5 | `sensitivity` only |

All three share accepted targets, material targets and F-04 safety. A/B preserve their exact C2 meanings for comparability; B's relationship .5 is explicitly inconsistent with the normative failed-agreement encoding and is therefore never a reference rule. The explicit selected adapter is the only legal constructor for both candidate and realized vectors. No convex mixture, per-row switching, candidate/realized mismatch or implicit fallback is legal.

The normative formula is selected because it is the only examined option that makes rejection fairness depend on observed inequity while leaving event meaning independent of priorities. Its limitation is explicit: it treats resistance to advantageous and disadvantageous inequity symmetrically, because the existing fairness channel is itself symmetric about equality. A role-asymmetric desert, entitlement or spite construct would be a new formula and requires a new revision/literature boundary; it is not smuggled into C3.

<a id="s11"></a>

## S11 — Stochastic unit, deterministic evidence and prospective protocol

**F-33:** The independent unit is defined by an explicitly declared independent randomization/data-generating process, not by a seed label or hash. Deterministic fixed-frame episodes are a census/sweep: multiple executions of the same condition create no sampling n. Rounds are repeated measures, and two seats in one dyad are not independent samples.

If a later approved protocol introduces stochastic opponents or sampled conditions, each independent draw/stream cluster is identified in advance. Within a paired full/switch contrast, reuse the same exogenous stream, addressed by condition, replicate, round, actor and event type; independent pairs use independently initialized streams. Do not use a single consumption-order stream that desynchronizes when actions diverge. Opponent reactions to changed public histories are part of the simulator's total effect, not leakage. A random draw not causally connected to any generated input does not make an episode stochastic.

**F-34:** A trajectory hash is SHA-256 of canonical serialized game/role/action/payoff/state content, excluding episode IDs, labels, stream IDs and timestamps. It diagnoses exact duplicates/determinism; it does not define a sample or cause deletion. Distinct independent draws may coincide; different trajectories may remain dependent. Independent-identical and dependent-different examples must both be in the later statistics-validator acceptance set. Hash equality cannot prove stochastic independence or its absence.

The finite frame, metrics and pairing contracts are fixed in B01–B05 and C0–C5. Full executable PAP remains after U1 and before U2: code/config manifests, precision justification, any stochastic generator and stream algorithm, sampling size, family registration, failure handling and sensitivity execution order must be frozen before pilot interpretation/confirmatory data. No stochastic generator is enabled by the present reference defaults.

<a id="s12"></a>

## S12 — Acceptance oracles (specified, NOT RUN)

| Test ID | Direct oracle and coverage domain |
|---|---|
| AT-INIT | Constructor/reset from YAML yields F-28 values; inconsistent S/r/W supplied values fail. Production. |
| AT-GAMES | Enumerate PD 4, BoS 4, UG 14 outcomes ×2 seats; payoffs exactly S02; wrong role/grid/action fails. Production legal outcomes. |
| AT-BOS | t=1→O,t=2→F; T=2h→(5h,5h), T=2h+1 imbalance 1; odd confirmatory T rejected; all state/switch/kind proposals remain equal. Structural fixture and control. |
| AT-UG-POLICY | Exhaustive offer x YAML-priority-profile F-35 oracle for neutral, interior, v=0 and v=1 states; N/B proposal partitions invariant across all legal v; A always accepts. At 2/8 fairness_high `N_VS==0.0`, category `tie_reject`, `D_VS==0.0`; material_high/relationship_high `N_VS=2,D_VS=2/3` and accept; offers 3–7 accept. Neutral hybrid R-selection null and injected/high-intensity selected-E fixture both retained. |
| AT-UG-CHOICE | For each legal offer, recompute selected-adapter candidate q, projections and z; compute `N_VS=math.fsum(p_clip*z)` and `P_VS=math.fsum(p_clip)` in K order, then one diagnostic division. Sign/category/action come only from N. Serialized map permutations are canonicalized to K. Fairness_high endpoint tie rejects; each of the two one-sided legal binary64 neighbors accepts; helper-level negative N rejects but is not a legal-priority fixture. No candidate projection mutates state or enters realized F-09. |
| AT-UG-OFFER | F-17 all four intervals/ties in S03-U; lower-distance tie stable under enumeration permutation; fractional/out-of-grid external offer fails. |
| AT-EVENT | Spies require exact S04-E ordering, both results before updates, one execute and one update/agent; decide leaves all fields unchanged; invalid/duplicate update fails before mutation. |
| AT-LEAK | Enumerate S04-O allowlist; add each denied field at top/nested levels and require failure; hold public payload fixed while changing opponent private data and require identical own trace. |
| AT-UG-ADAPTER | Enumerate all 84 selected-adapter vectors in UG_OUTCOME_TABLE (3x7x2x2), each admitted exactly in its authorized context; all targets in [0,1]; N r monotone in |E-2o|, symmetric endpoints and offer-5 zero; three IDs/keys distinct; role swap retains seat semantics; priorities/state/impulse changes leave raw rows identical. Candidate and realized vectors both equal the selected-adapter row. |
| AT-ADAPTER-PDBOS | S05-G enumeration; equality score after PD DD/BoS mismatch explicitly retained; positive payoff/regret ranges verified analytically. |
| AT-URGENCY | Δ signs/zero, legal endpoints, scientific near-epsilon ±alpha/2 plus independent C6 B oracles, conversion/arithmetic diagnostics, identity/epsilon/endpoint nextafter cases; impossible endpoint signs and executable bounds; separately labelled wider-helper saturation. No fabricated production coverage. |
| AT-FOCUS | Equal positive material/fairness weights→material; fairness/relationship→fairness; all-zero→null; permuted serialized map fields leave K-ordered output unchanged. |
| AT-THRESHOLD | Exact m at both cuts and r at cut gives zero offset; below/above changes correct modifier; |iota|=theta→R; legal state fixture (.5,.9,.5, pessimistic/high) in order (m,f,W) gives iota=.2775,theta=.27725: full E=C, fixed threshold R=D. |
| AT-PD | Equality at iota emotional cut→C and S rational cut→C; rational_only always D; emotional_only aR diagnostic follows the hybrid S rule. |
| AT-STATE | F-05/06/09/11/12/22–27 scientific exact substitution plus C6 ordered executable comparison and bound diagnostics; nonnegative fatigue increment terms and recovery; saturation/zero endpoints; helper-only clipping explicitly labelled. |
| AT-SUPPRESSION | Same pre-state v=.5,m=.2,f=.5,neutral/neutral gives iota=.025,aE=C,aR=D,a=D; preclip fatigue difference=.00075. Same sigma=0 inputs give identical outputs; saturated outputs use clip difference; inherited unequal states need not reconverge. |
| AT-MATERIAL | Identical one-step input produces identical raw q and identical four-channel F-35 candidates/votes in full/material_only; q_star nonmaterial equals pre-v; exactly those realized Δ=0; material Δ unchanged; later divergence permitted. `material_only` is not a candidate-vote deletion. |
| AT-SWITCH | Each S08 intervention changes only its stated entry point and descendants; opponent configuration fixed; no_suppression cannot change current action. Full traces expose raw and projected quantities. |
| AT-INVALID | Each S09 class yields typed error at the prescribed stage; complete effective defaults serialized; no unknown legacy aliases. Missing/implicit adapter; A/B in confirmatory or structural context; selected/candidate/realized mismatch; per-action adapter switching; malformed candidate traces; and inconsistent N/P/D/category recomputation all fail hard. |
| AT-RNG | Independent two draws yielding same one-round action: two stochastic units. Two different actions from one common random draw (e.g. U and 1−U): one dependent cluster. Hashes do not change unit assignment. Deterministic seed relabelling creates zero extra sampling units. |
| AT-BASELINE | B01 policies define initial and every later action; B02 role/horizon counts; no internal-state comparison to stateless baselines; modern analogues are not relabelled local heuristics. |
| AT-CLAIMS | C1 cites frozen spec ID/hash; C2a separates raw-target invariance, E-proposal choice and selected final action; C2b retains all-cell nulls; C3 ties remain in denominator with normative/A/B sensitivities reported separately; state-invariant vote, tie-only normative rejection, A-always-accept, N/B proposal equivalence and material/safety redundancy are disclosed; no strategic-reflection or novelty promotion. |
| AT-LEGACY | Prospective reference path has no DQN/refocus imports/objects/fallback/legacy wrapper dependencies; no old results enter new evidence map. Code audit/test only after U1. |
| AT-PACKAGE | Every review file hash matches manifest, internal/external manifest bytes match, ZIP has exact declared entries; receipt records independent ZIP/manifest hashes. This administrative check may be performed now. |

Every F-01…F-35 row has a direct oracle in traceability. Future passing tests will establish bounded implementation correspondence only; these specifications do not assert that any test currently passes.

<a id="s13"></a>

## S13 — Scientific interpretation and carry-forward limitations

All model mechanisms remain THEORETICAL_ONLY/PLANNED. The integrated path is a simulation construct. Mood/fatigue/values are operational variables; no human construct validity, full rationality, learning, refocus, opponent model, recursion, planning, strategic reflection, equilibrium convergence or universal advantage. C3 structural examples do not guarantee prevalence, C3 metric construction does not guarantee discordance, and the C4 contract repair creates no empirical result.

L2 covers a finite screened corpus up to 2026-09-16 (42 screened,28 included; Scopus/WoS unavailable). The contribution target is the exact integration with transparent traceability and paired causal diagnostics. Component mechanisms, affective UG and BoS turn taking are prior art. See B04 for primary-source comparator mapping; no broad priority statement is authorized.

<a id="s14"></a>

## S14 — Gate boundary

Owner does not close P2-C5-P1-01, R0 C6 or author adoption. Independent targeted R0 must challenge graph, error bounds, identity, reachability, labels, F-35 separation, full diff and pinned sections. Coordinator verifies the exact reviewed package before short author U1 addendum. C6 is not a baseline for Engineer/PAP before adoption. No pilot, full runs, code freeze, claim promotion or submission is authorized.
