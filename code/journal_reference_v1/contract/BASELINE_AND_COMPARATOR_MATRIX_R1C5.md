# BASELINE_AND_COMPARATOR_MATRIX_R1C5

Matrix ID: `EMBORA-BCM-2026-09-24-R1C5`. Normative for baseline policies, condition roster and comparator scope. Spec/claim IDs: `EMBORA-MSJ1-2026-09-24-R1C5`, `EMBORA-CC-2026-09-24-R1C5`. All proposed runs remain blocked; no baseline was executed.

<a id="b01"></a>

## B01 — Exact baseline policies

Baselines are stateless functions of public observation/history, using legal action objects from YAML. They have no simulated v,m,f,S; those quantities are null/not applicable, never zero-valued pseudo-data. They cannot support an internal-state superiority comparison. Policies have no opponent-private access, learned parameters or hidden initialization.

| ID | Game/role | First action | Every later legal history |
|---|---|---|---|
| PD_AllC | PD/player, either seat | C | C |
| PD_AllD | PD/player, either seat | D | D |
| PD_TFT | PD/player, either seat | C | opponent's last public action |
| PD_WSLS | PD/player, either seat | C | own previous action if previous own payoff is 3 or 5, otherwise other PD action |
| BoS_Opera | BoS/player, either seat | O | O |
| BoS_Fight | BoS/player, either seat | F | F |
| BoS_Convention | BoS/player, either seat | F-20 | F-20 (round resets every episode) |
| UG_Offer2 | UG/proposer | offer 2 | offer 2 |
| UG_Offer4 | UG/proposer | offer 4 | offer 4 |
| UG_Offer5 | UG/proposer | offer 5 | offer 5 |
| UG_Offer8 | UG/proposer | offer 8 | offer 8 |
| UG_Cycle | UG/proposer | first legal offer | offer grid element indexed by (t−1) mod grid length, zero-based |
| UG_AcceptAll | UG/responder | accept current offer | accept current offer |
| UG_RejectAll | UG/responder | reject current offer | reject current offer |
| UG_Threshold4 | UG/responder | accept iff offer≥4 | same current-offer rule; equality accept |
| UG_Threshold5 | UG/responder | accept iff offer≥5 | same current-offer rule; equality accept |

`Model_Neutral` below denotes a model opponent, not a baseline alias: hybrid, neutral personality/intensity, equal priorities, neutral initialization, full variant, and the same explicitly named adapter convention, with S03 model policies. Primary/reference cells require `normative_resisted_inequity_v1`. Emotional_only and rational_only are explicit model-kind comparisons using the complete S03 policy matrix; they are not clean one-switch ablations and are not labelled optimal agents.

### B01-A — UG adapter comparator identities

| Comparator status | Adapter ID | Config key | Allowed use | Pairing rule |
|---|---|---|---|---|
| reference | `UG-ADAPTER-C3-NORM-RESISTED-INEQUITY-v1` | `normative_resisted_inequity_v1` | `confirmatory_frame`, `sensitivity`, `structural_fixture` | primary frame key |
| sensitivity A | `UG-ADAPTER-C3-SENS-ZERO-EXCHANGE-v1` | `sensitivity_zero_exchange_v1` | `sensitivity` only | otherwise identical to reference; never mixed in one trajectory |
| sensitivity B | `UG-ADAPTER-C3-SENS-NEUTRAL-NO-EXCHANGE-v1` | `sensitivity_neutral_no_exchange_v1` | `sensitivity` only | otherwise identical to reference; never mixed in one trajectory |

A/B are semantic sensitivity adapters, not agents or empirical baselines. `selected_adapter_convention` and `run_purpose` are explicit pair-key fields with no default. All baseline responder/proposer policies remain stateless and unchanged; the selected adapter solely generates a model agent's candidate and realized q and, under F-35, its value-sensitive responder proposal. A/B outside sensitivity, implicit selection or mixed candidate/realized adapters invalidate the cell.

<a id="b02"></a>

## B02 — Frozen deterministic condition frame

Primary frame ID `DF-C3-NEUTRAL-200` is a **finite design census**, not a sample of humans or all possible simulator states. Each focal model begins with neutral primary state (S01/YAML). Its factors are every personality × intensity × priority profile listed in YAML: 3×3×5=45 profiles. Factors are equally weighted within each game-role stratum. The opponent is fixed by the row below; there is no threshold-near selection or removal of zero-effect cells. All profiles are crossed even when they yield identical behavior.

| Stratum | Focal role/seats | Opponents, each included once per profile/seat | Horizon/parity | Conditions | Claims |
|---|---|---|---|---:|---|
| PD | player, both seats in separate episodes | PD_AllC, PD_AllD, PD_TFT, PD_WSLS, Model_Neutral | reference T; both seats | 45×5×2=450 | C1; C2a diagnostics/C2b; C3; C4 secondary |
| BoS | player, both seats in separate episodes | BoS_Opera, BoS_Fight, BoS_Convention | reference even T, t1=O | 45×3×2=270 | C1; state diagnostics; C3 only; no behavioral arbitration/override evidence |
| UG-P | proposer, seat 1 | UG_AcceptAll, UG_RejectAll, UG_Threshold4, UG_Threshold5, Model_Neutral as responder | reference T; role fixed | 45×5=225 | C1; C2a/C2b; C3; C4 secondary |
| UG-R | responder, seat 2 | UG_Offer2, UG_Offer4, UG_Offer5, UG_Offer8, UG_Cycle, Model_Neutral as proposer | reference T; role fixed | 45×6=270 | C1; C2a/C2b and offer-response checks; C3; C4 secondary |

Total = 1,215 conditions. UG role strata have different opponent rosters and are never pooled as interchangeable observations; report both. Identity exchange while preserving roles is an invariance test, not another independent condition. Role swaps are covered by the separately specified UG-P and UG-R strata; no claim of matched role symmetry across these different rosters.

<a id="b03"></a>

## B03 — Exact contrasts and pairing

| Contrast family | Per condition | Number of contrasts / episodes | Purpose |
|---|---:|---:|---|
| focal hybrid full vs each of 5 YAML switches, opponent unchanged | 5 contrasts; 6 model configurations | 6,075 pairs; 7,290 distinct condition/configuration episodes | C2b (four central switches), C4 (no_suppression); C3 |
| full hybrid vs emotional_only; full hybrid vs rational_only | 2 contrasts; reuses full reference | 2,430 contrasts; 2,430 additional episodes | descriptive architecture controls; not C3 single-switch attribution |

The above counts are design arithmetic only and do not authorize compute. Primary C2b behavioral reporting excludes the 270 BoS conditions; four central switches ×945 eligible conditions =3,780 declared full/switch contrasts. BoS is retained as an explicit null action control, not silently dropped from the overall roster. C3 uses all five switches, all four strata, with no stateless-baseline S values. Total base-frame planned model episodes including kind controls:9,720; sensitivity blocks are additional and separately budgeted at U2.

Canonical condition key is the tuple `(frame_id,game,focal_role,focal_seat,focal_personality,focal_intensity,priority_profile,opponent_policy_id,horizon,selected_adapter_convention,run_purpose)`. A switch pair adds `contrast_id` and target focal identity; the common condition key excludes variant. Different `selected_adapter_convention` or `run_purpose` values always define distinct condition identities, including N confirmatory versus N sensitivity; missing or mismatched selection is invalid, never a key alias. Kind comparisons add a distinct `contrast_family=kind_control`. Run keys add variant/kind plus replicate/stream keys if later authorized. Checks require identical source initialization, payoff/grid parameters, role assignment, opponent configuration and exogenous schedule; only the declared focal intervention varies. Self-play with both agents ablated is outside this roster.

Finite deterministic cell weights are equal per stratum; repeated execution or matching trajectory hashes do not change weights. Opponent feedback to a changed history is allowed. No resampling of favorable starts. No separate code implementation per variant. Every frame cell appears in the accounting, including no proposal disagreement, no final action divergence, clipped null effects and adverse payoffs.

Post-U1 PAP must compile this roster into a machine-checkable condition list, justify sensitivity/run budget, and preregister any truly stochastic extension. The current default has no active RNG source and no stochastic sample size. Adding a stochastic population is a new protocol decision with stream independence/precision requirements in Claim C5, not an implicit interpretation of existing seed labels.

<a id="b04"></a>

## B04 — Frozen-L2 modern-analogue mapping

Literature authority: [L2 novelty matrix](https://drive.google.com/file/d/1IWkuo0QHMOxf-T9oyQGP7DLxcZQse6eK/view), [evidence table](https://drive.google.com/file/d/14zcntBK8Ol049phTXquZ_mBuo3dM4fMH/view), [verified bibliography](https://drive.google.com/file/d/1rM82CWT6wtz4WTI_KrIKnb_954SmDYCb/view). This is a bounded reuse of frozen L2, not new literature research. Primary-source links below are taken from that bibliography; no new metadata was invented.

| L2 analogue / primary source | Shared object and comparison dimension | Scope mismatches | Contractual treatment / affected claim |
|---|---|---|---|
| E11 [Churamani et al.2022](https://doi.org/10.3389/frobt.2022.717193) | affect perception, memory, intrinsic mood and UG proposer; inspectability of policy/state links | learned actor–critic, human–robot interaction, proposer focus; EmBoRA has no perception/training dataset or matched learned policy | closest empirical analogue; qualitative mechanism/protocol mapping only. No numeric head-to-head, superiority or first-affective-UG claim. UG-R correction is construct validity. |
| E06/E08 [Gratch–Marsella 2004](https://doi.org/10.1016/j.cogsys.2004.02.002), [EMA 2009](https://doi.org/10.1016/j.cogsys.2008.03.005) | appraisal→coping proposals/selection→action, mood; inspectable timing/state gates | appraisal/coping semantics differ; not identical repeated-game action interface | process comparator for integration/traceability; appraisal-to-action is prior art. No EMA reimplementation claimed. |
| E07 [ALMA 2005](https://doi.org/10.1145/1082473.1082478) | layered affect and behavior control | personality/affect timescales and evaluation differ | persistent-mood contribution restricted to the exact integrated recurrence/evidence contract. |
| E10 [Palkovics–Takáč 2016](https://doi.org/10.1016/j.cogsys.2016.06.001) | cognition–affect and Type1/Type2 interaction | not the same explicit game proposals or switch suite | no broad dual-process novelty. |
| E17/E18 [McKee et al.2020](https://doi.org/10.5555/3398761.3398863), [Tennant et al.2023](https://doi.org/10.24963/ijcai.2023/36) | heterogeneous social preferences/value rewards in mixed-motive/repeated games | learned reward-driven policies and training objectives differ | modern value-agent comparator; C2/C3 concern operational recurrence, not superiority over moral/SVO MARL. |
| E25 [MAVIPER 2022](https://doi.org/10.1007/978-3-031-26412-2_16) | interpretable multi-agent policies and their evidence | extracted decision trees rather than endogenous two-proposal arbitration | modern interpretability analogue for C1; no “first interpretable agent” or explanation-quality advantage. |
| E20 [Zheng et al.2025](https://doi.org/10.1103/vk6m-48zs) | role-specific UG learning/fairness | learned policies, not fixed white-box response | contemporary UG context; role correctness is not novel. |
| E22/E23 [Lau–Mui 2008](https://doi.org/10.1007/s11238-008-9100-8), [Arifovic–Ledyard 2018](https://doi.org/10.1007/s10683-018-9568-1) | repeated-BoS alternation/turn taking | learning/behavioral studies vs deterministic public convention | F-20 is a control with prior art, not a new coordination mechanism. |

No modern learned analogue is numerically implemented or approximated here. The article's contribution is therefore explicitly narrowed to traceability and within-simulator paired causal diagnostics, plus descriptive comparison against the exact simple controls. Those controls must never be renamed EMA, Churamani, SVO, moral MARL or MAVIPER. Numeric performance comparison with modern systems and a broad performance benchmark contribution are excluded. If R0/author/journal later requires such a head-to-head, it is an unresolved scope expansion requiring a new comparator protocol and authority; this qualitative table cannot satisfy a numerical-comparison requirement by itself. This limitation remains attached to R0-P1-13/SR-P1-05.

<a id="b05"></a>

## B05 — EUMAS overlap and publication boundary

Authority: frozen [reuse note](https://drive.google.com/file/d/17Izmm5ybkRmknERL4qWmsFuKU20m7G3L/view), accepted proof SHA-256 `7e5855c425522f8dafecf12dc10348fc5a7af32812035990822eb2822a094db6`, source freeze `EMBORA-SF-2026-09-16-v1.0`. The table below reconciles L2's inventory with C3; it is not a newly performed page-by-page proof audit.

| Accepted baseline / lineage per L2 | C3 treatment | Genuinely new evidence still needed |
|---|---|---|
| motivation, dual-system framing, outcome–state–decision loop | inherited context, not novelty | none may be claimed new |
| adapters, values, mood/fatigue/resource equations | lineage retained where stated; UG adapter revised F-31 | new code correspondence and channel/outcome oracles |
| PD/BoS/UG diagnostic setup | games retained; BoS control; UG responder now uses current-action value evaluation | fresh event-order, raw-target and priority-to-choice evidence |
| historical mode comparisons/results | preserved only as historical provenance | no carry-over into C1–C4; new runs after gates |
| traceability, parameter reconciliation | new explicit contract/test obligations | clean commit, environment/config lock, direct formula checks |
| single-path mechanism evidence / representative effects | new prospective C2a/C2b design | preregistration, paired trajectories and R2 |
| payoff-state analysis | C3 restricted to operational preregistered ranking | complete new distributions, nulls and sensitivity |

Exact accepted-proof paragraph/page overlap, eventual text reuse, extended-version admissibility and final disclosure route remain prospective publication tasks under SR-P1-05. No final DOI/pages/proceedings citation is supplied. At manuscript/reuse freeze the responsible owner verifies actual publication status; if still unpublished, use only the journal-permitted accepted/in-press or other disclosure route. A concrete remaining admissibility ambiguity may require author-authorized editor contact later. Neither publication permission nor policy compliance is certified by this C3 package.
