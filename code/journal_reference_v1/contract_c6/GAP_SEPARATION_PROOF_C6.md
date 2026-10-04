# Corrected F-35 separation proof — C6 v1.1, 2026-10-04

Status: owner derivation; R0-C6-P1-01 addressed / pending independent recheck. No author adoption or independent closure.

## Definition and exact enumeration

For one selected adapter J, one current offer o, and one channel k, define g(J,o,k)=abs(q_accept(J,o,k)-q_reject(J,o,k)). It does not compare targets across offers/channels. F31/F04 responder formulas give accepted vector (o/8,b(o),1,1), b(o)=1-|10-2o|/10. Rejection is (0,1-b,0,1-o/8) for N, (0,0,0,1-o/8) for A, and (0,1/2,1/2,1-o/8) for B.

Independent exact-rational enumeration in derive_gap_proof.py imports neither the projection reference nor production. All 84 pairs (3 adapters × 7 offers × 4 channels), their signs and exact fractions are in GAP_SEPARATION_DERIVATION_C6.json. The minima are:

| Adapter | Material minimum | Fairness minimum | Relationship minimum | Safety minimum | Overall minimum |
|---|---:|---:|---:|---:|---:|
| N | 1/4 | 1/5 | 1 | 1/4 | 1/5 |
| A | 1/4 | 2/5 | 1 | 1/4 | 1/4 |
| B | 1/4 | 1/10 | 1/2 | 1/4 | 1/10 |

B fairness at o=3 or 7 is 3/5−1/2=1/10. This contradicts the published v1.0 floor of 1/8 and alpha_B/8; the scientific votes themselves do not change. That false bound remains only in the immutable parent/history and explicit defect descriptions, never as an active premise in v1.1.

## Uniform argument, including boundaries

Fix any binary64 v∈[0,1] and the prescribed a=alpha_B, e=epsilon_B. Let f_v(q) be the **real** signed appraisal on those fixed rounded state/parameter inputs. For q≤v, f_v(q)=a(q-v)/max(e,v); for q≥v, f_v(q)=a(q-v)/max(e,1-v). The formulas agree at q=v with value zero. No production saturation occurs because |f_v(q)|≤a<1. Both denominators are ≤1, so either nonempty piece has slope ≥a; both are ≥e, so slope ≤a/e. Integrating over an interval, including one crossing identity, gives |f_v(qa)-f_v(qr)|≥a|qa-qr| and the exact target-order sign. At v=0 only the gain piece is nonempty; at v=1 only the loss piece is nonempty. Epsilon branches also retain both bounds. These facts do not require neutral reachability or a sample sweep.

The adapter bound is derived from its literal graph: 2o and 10−2o are exact small integers; abs is exact; division by 10 contributes at most eta, and subtraction from 1 at most another eta. The normative rejection fairness complement adds at most eta. Material o/8, its safety complement, and constants 0/1/1/2 are exactly representable. Thus every target error is at most 3eta; 4eta is a uniform conservative bound. This is an arithmetic derivation rather than a fitted fixture tolerance.

Let eta=2^-52. Literal raw-adapter evaluation differs from each exact rational target by ≤4eta; its appraisal contribution is therefore ≤4a*eta/e per action. The unchanged rounded-projection bound gives ≤8eta/e additional arithmetic error per action; exact q=v identity is included and has B=R by numerical value. IEEE signed-zero metadata do not affect numeric inequality or vote. Write C=8eta/e+4a*eta/e. For either target order, the signed executable appraisal gap in that same direction is at least a*g−2C. Thus the global floor is:

`M = alpha_B/10 − 2*(8eta/epsilon_B + 4alpha_B*eta/epsilon_B)`.

Using exact dyadic a=3152519739159347/9007199254740992 and e=4722366482869645/4722366482869645213696 yields

`M = 2977470355436251719876380149867 / 85070591730234612016238747975680`

`M = 0.0349999958255614251889652092986496316055332163687227760540860… > 0`.

N-specific margin is 0.0699999958255614229685191600483365507582698801870821510540860…; A-specific margin is 0.0874999958255614218582961354231800103346382120962618385540860…. These independently computed values agree with the Reviewer's corrected margin as a check; the Reviewer output is not used as the expected oracle.

This is a uniform positive separation over all legal v, including endpoints, raw-target or rounded-target identity, epsilon branches, subnormal/nextafter states and heterogeneous four-channel states. If an adapter rounding perturbation crosses q=v, continuity and the a/e Lipschitz bound still apply. Generic arbitrary nextafter targets need not preserve strict ordering; the conclusion is only for the frozen same-offer/channel pairs with the enumerated gaps. A/B arithmetic fixtures retain sensitivity-only production permissions.

## Observable consequence and checks

For N/B at offers 2/8, votes remain (+1,-1,+1,+1); at 3–7 all positive. A votes remain all positive. The implementation must still compare rounded appraisals, not substitute sign(raw targets). Exact fixed-K math.fsum N/P, N-only branching/category, exact-zero tie-reject, diagnostic-only D, branch tolerance zero and existing clipped priority bounds remain unchanged.

The source derives positive rational boundary/identity/epsilon gaps for each pair and saves every actual static check. The separate projection reference checks all 840 inherited F-35 cases. These are bounded scalar/static specification checks; they are not production conformance, trajectory evidence, P2 completion or author adoption.
