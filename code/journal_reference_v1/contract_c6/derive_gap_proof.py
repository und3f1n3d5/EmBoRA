"""Exact same-offer/channel gap derivation; no production/reference imports."""
from fractions import Fraction as F
from decimal import Decimal,localcontext
from pathlib import Path
import json,sys

def derive(out):
    E=10;offers=range(2,9);keys=('material','fairness','relationship','safety')
    eta=F(1,2**52)
    # Exact dyadic constants obtained from the specified binary64 literals, not observations.
    a=F(3152519739159347,9007199254740992)
    e=F(4722366482869645,4722366482869645213696)
    perturbation=8*eta/e+4*a*eta/e
    rows=[];mins={};checks=[]
    def appraisal(v,q):
        delta=a*(q-v)
        if delta==0:return F(0)
        return delta/max(e,1-v if delta>0 else v)
    for adapter in ('N','A','B'):
        for o in offers:
            balance=F(1)-F(abs(E-2*o),E)
            accept=(F(o,8),balance,F(1),F(1))
            reject=(F(0),1-balance if adapter=='N' else F(0) if adapter=='A' else F(1,2),F(1,2) if adapter=='B' else F(0),1-F(o,8))
            for k,qa,qb in zip(keys,accept,reject):
                gap=abs(qa-qb);assert gap>0
                rows.append(dict(adapter=adapter,offer=o,channel=k,accept=str(qa),reject=str(qb),signed_gap=str(qa-qb),absolute_gap=str(gap)))
                mins[adapter]=min(mins.get(adapter,gap),gap)
                # Static rational boundary, exact identity and epsilon cases; no recurrence episode.
                states={F(0),F(1),F(1,2),qa,qb,e/2,1-e/2,e,1-e}
                for v in sorted(states):
                    d=appraisal(v,qa)-appraisal(v,qb)
                    assert (d>0)==(qa>qb) and abs(d)>=a*gap
                    checks.append(dict(adapter=adapter,offer=o,channel=k,v=str(v),signed_appraisal_gap=str(d),real_gap_floor=str(a*gap)))
    assert mins=={'N':F(1,5),'A':F(1,4),'B':F(1,10)}
    global_min=min(mins.values());margins={k:a*g-2*perturbation for k,g in mins.items()}
    assert all(x>0 for x in margins.values())
    with localcontext() as c:
        c.prec=60
        dec=lambda x:str(Decimal(x.numerator)/Decimal(x.denominator))
        result=dict(status='OWNER_DERIVATION_PENDING_INDEPENDENT_RECHECK',definition='abs(q_accept-q_reject) for one adapter, one current offer, one channel, UG responder',pairs=rows,minima={k:str(v) for k,v in mins.items()},global_minimum=str(global_min),alpha_B=str(a),epsilon_B=str(e),eta=str(eta),arithmetic_error_per_projection=str(8*eta/e),adapter_target_error_bound=str(4*eta),adapter_appraisal_error_per_projection=str(4*a*eta/e),total_perturbation_per_projection=str(perturbation),real_appraisal_floors={k:str(a*g) for k,g in mins.items()},uniform_margins={k:{'fraction':str(v),'decimal':dec(v)} for k,v in margins.items()},global_margin_decimal=dec(min(margins.values())),static_boundary_identity_epsilon_checks=checks,production_imports=0,trajectories=0)
    Path(out).write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ['pairs','static_boundary_identity_epsilon_checks']},indent=2))
if __name__=='__main__':derive(sys.argv[1])
