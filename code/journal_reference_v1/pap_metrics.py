"""PAP-native pure postprocessing v1.0. No Engine, execution or validation authority.

Inputs must already have passed the applicable native artifact validator.
These checks enforce metric shape/pairing/completeness, not full scientific replay.
Definitions: METRIC_AND_FAILURE_SCHEMA_C5_v1.0 sections2–4, current C6 PAP.
"""
import copy
import json
import math
from collections import Counter

VERSION = 'EMBORA-PAP-NATIVE-METRICS-v1.0'
MAX_PAYOFF = {'PD':5, 'BoS':3, 'UG-P':8, 'UG-R':8}
CATEGORIES = ('strict_discordant','strict_concordant','both_tied','payoff_only_tied','state_only_tied')
SWITCHES = ('no_suppression','no_mood','no_fatigue','fixed_threshold','material_only')


class MetricError(ValueError): pass


def finite(value):
    if type(value) not in (int,float) or not math.isfinite(value):
        raise MetricError('Missing, nonnumeric or nonfinite metric input')
    return float(value)


def canonical(value):
    try:return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)
    except (TypeError,ValueError) as e:raise MetricError('Invalid metric input object') from e


def rank_sign(value, threshold=1e-9):
    value=finite(value);threshold=finite(threshold)
    if threshold<=0:raise MetricError('Positive rank cutoff required')
    return 1 if value>threshold else -1 if value < -threshold else 0


def tie_category(rp,rq):
    if any(type(x) is not int or x not in (-1,0,1) for x in (rp,rq)):raise MetricError('Invalid rank signs')
    if rp==0 and rq==0:return 'both_tied'
    if rp==0:return 'payoff_only_tied'
    if rq==0:return 'state_only_tied'
    return 'strict_discordant' if rp*rq==-1 else 'strict_concordant'


def nearest_rank(values,p):
    p=finite(p);xs=sorted(finite(x) for x in values)
    if not xs or not 0<=p<=1:raise MetricError('Empty/invalid quantile')
    return xs[max(1,math.ceil(p*len(xs)))-1]


def summary(values):
    xs=[finite(x) for x in values]
    if not xs:raise MetricError('Missing summary observations')
    ys=sorted(xs);n=len(xs)
    return dict(n=n,mean=math.fsum(xs)/n,median=ys[n//2] if n%2 else (ys[n//2-1]+ys[n//2])/2,
                p10=nearest_rank(xs,.1),p90=nearest_rank(xs,.9),min=ys[0],max=ys[-1],
                positive=sum(x>0 for x in xs)/n,zero=sum(x==0 for x in xs)/n,negative=sum(x<0 for x in xs)/n)


def first_difference(a,b,equal=lambda x,y:canonical(x)==canonical(y)):
    if not a or len(a)!=len(b):raise MetricError('Incomplete paired series')
    return next((t for t,(x,y) in enumerate(zip(a,b),1) if not equal(x,y)),len(a)+1)


def close(a,b):
    if isinstance(a,dict) and isinstance(b,dict):return a.keys()==b.keys() and all(close(a[k],b[k]) for k in a)
    if isinstance(a,list) and isinstance(b,list):return len(a)==len(b) and all(close(x,y) for x,y in zip(a,b))
    return math.isclose(finite(a),finite(b),abs_tol=1e-12,rel_tol=1e-12)


def focal(config):
    agents=[a for a in config['agents'] if a['agent_id']==config['focal_agent_id']]
    if len(agents)!=1 or agents[0]['controller_type']!='model':raise MetricError('Explicit stateful focal model required; no baseline pseudo-state')
    return agents[0]


def episode_metrics(config,rounds):
    """Read only post-round t1..T, focal identity mapped to its explicit seat."""
    try:
        a=focal(config);T=config['horizon'];game=config['game']
        if type(a['seat']) is not int or a['seat'] not in (1,2):raise MetricError('Invalid focal seat')
        seat=a['seat']-1
        expected_role=('proposer' if seat==0 else 'responder') if game=='UG' else 'player'
        if a['role']!=expected_role:raise MetricError('Focal role/seat mismatch')
        if type(T) is not int or T<=0 or type(rounds) is not list or len(rounds)!=T or seat not in (0,1):
            raise MetricError('Incomplete episode or seat')
        stratum=('UG-P' if a['role']=='proposer' else 'UG-R') if game=='UG' else game
        if stratum not in MAX_PAYOFF:raise MetricError('Unknown stratum')
        actions=[];payoffs=[];states=[];decisions=[];updates=[]
        for t,r in enumerate(rounds,1):
            if type(r['round']) is not int or r['round']!=t or r['failure_status'] is not None:
                raise MetricError('Incomplete/noncommitted or misordered round')
            if any(r[k]!=config[k] for k in ('game','condition_id','pair_id','run_purpose','selected_adapter_convention')):
                raise MetricError('Native round/config identity mismatch')
            for k in ('actions_by_seat','payoffs_by_seat','post_states_by_seat','decisions_by_seat','updates_by_seat'):
                if type(r[k]) is not list or len(r[k])!=2:raise MetricError('Seat-ordered native pair required')
            action=r['actions_by_seat'][seat]
            if stratum=='UG-P':
                if set(action)!={'name','offer'} or action['name']!='offer' or type(action['offer']) is not int or not 2<=action['offer']<=8:
                    raise MetricError('Illegal proposer action')
            elif set(action)!={'name'} or action['name'] not in {'PD':('C','D'),'BoS':('O','F'),'UG-R':('accept','reject')}[stratum]:
                raise MetricError('Illegal focal action')
            state=r['post_states_by_seat'][seat]
            if not isinstance(state,dict):raise MetricError('Missing focal post-state')
            for k in ('S','f','m','Wtilde','r','W'):finite(state[k])
            if not isinstance(state['v'],dict) or set(state['v'])!={'material','fairness','relationship','safety'}:raise MetricError('Missing dynamic value map')
            for x in state['v'].values():finite(x)
            d=r['decisions_by_seat'][seat];u=r['updates_by_seat'][seat]
            if not isinstance(d,dict) or not isinstance(u,dict):raise MetricError('Missing focal decision/update')
            for k in ('theta','theta_reference'):finite(d[k])
            for k in ('aE','aR','selected_branch'):canonical(d[k])
            for k in ('Csup_raw','Csup_applied','fatigue_preclip','mood_preclip'):finite(u[k])
            actions.append(copy.deepcopy(action));payoffs.append(finite(r['payoffs_by_seat'][seat]))
            states.append(copy.deepcopy(state));decisions.append(copy.deepcopy(d));updates.append(copy.deepcopy(u))
        disagreement=[canonical(d['aE'])!=canonical(d['aR']) for d in decisions]
        clips=Counter('below0' if u['fatigue_preclip']<0 else 'above1' if u['fatigue_preclip']>1 else 'within' for u in updates)
        votes=None
        if stratum=='UG-R':
            votes=Counter()
            for d in decisions:
                n=finite(d['choice']['N_VS'])
                category='positive_accept' if n>0 else 'negative_reject' if n<0 else 'tie_reject'
                if d['choice']['category']!=category:raise MetricError('Vote category must follow exact numerator sign')
                votes[category]+=1
        return dict(interface_id=VERSION,config=copy.deepcopy(config),T=T,stratum=stratum,P=math.fsum(payoffs)/T,
                    Q=math.fsum(s['S'] for s in states)/T,mean_f=math.fsum(s['f'] for s in states)/T,
                    branch_disagreement_rate=sum(disagreement)/T,branch_counts=dict(Counter(d['selected_branch'] for d in decisions)),
                    vote_categories=None if votes is None else dict(votes),
                    D_VS=None if votes is None else summary([d['choice']['D_VS'] for d in decisions]),
                    cost_raw_mean=math.fsum(u['Csup_raw'] for u in updates)/T,cost_applied_mean=math.fsum(u['Csup_applied'] for u in updates)/T,
                    nonzero_cost_rate=sum(u['Csup_raw']!=0 for u in updates)/T,nonzero_applied_cost_rate=sum(u['Csup_applied']!=0 for u in updates)/T,
                    proposal_override_rate=sum(canonical(d['aE'])!=canonical(ac) for d,ac in zip(decisions,actions))/T,
                    fatigue_preclip_mean=math.fsum(u['fatigue_preclip'] for u in updates)/T,mood_preclip_mean=math.fsum(u['mood_preclip'] for u in updates)/T,
                    fatigue_clip_fractions={k:clips[k]/T for k in ('below0','within','above1')},
                    series=dict(actions=actions,payoffs=payoffs,states=states,decisions=decisions,disagreement=disagreement))
    except (KeyError,TypeError,IndexError) as e:raise MetricError('Missing/malformed native metric field') from e


def matched(full,comparison,family):
    a=copy.deepcopy(full['config']);b=copy.deepcopy(comparison['config']);fa=focal(a);fb=focal(b)
    if fa['variant']!='full' or fa['kind']!='hybrid':raise MetricError('Reference must be hybrid/full')
    if family=='single_switch':
        if fb['kind']!='hybrid' or fb['variant'] not in SWITCHES:raise MetricError('Unregistered switch')
        fb['variant']='full'
    elif family=='kind_control':
        if fb['variant']!='full' or fb['kind'] not in ('emotional_only','rational_only'):raise MetricError('Unregistered kind control')
        fb['kind']='hybrid'
    else:raise MetricError('Unknown contrast family')
    if canonical(a)!=canonical(b):raise MetricError('Unmatched condition/initial state/role/adapter/horizon/opponent')


def pair_metrics(full,comparison,family='single_switch',cutoff=1e-9):
    if cutoff not in (1e-10,1e-9,1e-8):raise MetricError('Unregistered metric cutoff')
    matched(full,comparison,family);T=full['T'];f=full['series'];c=comparison['series'];stratum=full['stratum']
    divergence=[canonical(a)!=canonical(b) for a,b in zip(f['actions'],c['actions'])];tau=first_difference(f['actions'],c['actions'])
    dp=full['P']-comparison['P'];dq=full['Q']-comparison['Q'];xp=dp/MAX_PAYOFF[stratum];xq=dq/4
    rp=rank_sign(xp,cutoff);rq=rank_sign(xq,cutoff)
    def decision_difference(keys):return first_difference([[d[k] for k in keys] for d in f['decisions']],[[d[k] for k in keys] for d in c['decisions']])
    def threshold_difference(k):return first_difference([d[k] for d in f['decisions']],[d[k] for d in c['decisions']],close)
    dynamic=lambda s:{k:s[k] for k in ('v','m','f','r','W','Wtilde','S')}
    def conditioned(disagreement):
        seen=False;prior=0;same=0
        for hit,dis in zip(divergence,disagreement):
            seen=seen or dis;prior+=bool(hit and seen);same+=bool(hit and dis)
        n=sum(divergence)
        return dict(with_prior_disagreement_all_rounds=prior/T,with_same_round_disagreement_all_rounds=same/T,
                    divergent_rounds=n,with_prior_disagreement_given_divergence=None if not n else prior/n,
                    with_same_round_disagreement_given_divergence=None if not n else same/n)
    descriptor=focal(comparison['config'])
    return dict(interface_id=VERSION,T=T,stratum=stratum,contrast_family=family,
                condition_id=full['config']['condition_id'],pair_id=full['config']['pair_id'],
                comparison_variant=descriptor['variant'],comparison_kind=descriptor['kind'],rank_cutoff=cutoff,
                tau_A=tau,I_A=int(tau<=T),D_A=sum(divergence)/T,
                delta_P=dp,delta_S=dq,delta_f=full['mean_f']-comparison['mean_f'],normalized_delta_P=xp,normalized_delta_Q=xq,
                rank_P=rp if family=='single_switch' else None,rank_Q=rq if family=='single_switch' else None,
                category=tie_category(rp,rq) if family=='single_switch' else None,strict_discordance=int(rp*rq==-1) if family=='single_switch' else None,
                offer_distance=math.fsum(abs(a['offer']-b['offer'])/6 for a,b in zip(f['actions'],c['actions']))/T if stratum=='UG-P' else None,
                offer_distance_NA=None if stratum=='UG-P' else 'role_not_applicable',
                tau_proposal=decision_difference(('aE','aR')),tau_E=decision_difference(('aE',)),tau_R=decision_difference(('aR',)),
                tau_threshold=threshold_difference('theta'),tau_threshold_reference=threshold_difference('theta_reference'),
                tau_state=first_difference([dynamic(s) for s in f['states']],[dynamic(s) for s in c['states']],close),
                divergence_conditioned_full=conditioned(f['disagreement']),divergence_conditioned_comparison=conditioned(c['disagreement']),
                BoS_behavior_identifiability='not_identifiable' if stratum=='BoS' else 'applicable')


def cell_summary(expected_ids,rows,T):
    """No silently reduced denominator or complete-frame claim with missing cells."""
    if not expected_ids or len(set(expected_ids))!=len(expected_ids):raise MetricError('Explicit unique expected contrast IDs required')
    if len({r['contrast_id'] for r in rows})!=len(rows) or set(r['contrast_id'] for r in rows)-set(expected_ids):raise MetricError('Duplicate/unknown contrast')
    by_id={r['contrast_id']:r for r in rows};missing=[k for k in expected_ids if k not in by_id or by_id[k]['status']!='VALID'];N=len(expected_ids)
    out=dict(interface_id=VERSION,status='INCOMPLETE' if missing else 'COMPLETE',N_expected=N,N_valid=N-len(missing),missing_or_invalid_ids=missing,
             P_A=None,D=None,categories=None,strict_only_discordance=None,distributions=None,tau_frequency=None,survival=None,no_divergence_mass=None)
    if missing:return out
    values=[by_id[k]['metrics'] for k in expected_ids]
    if (any(v['T']!=T for v in values) or len({(v['stratum'],v['contrast_family'],v['comparison_variant'],v['comparison_kind'],v['rank_cutoff']) for v in values})!=1
            or len({v['condition_id'] for v in values})!=N):raise MetricError('Mixed or duplicate-condition reporting cell')
    cats=Counter(v['category'] for v in values);ranks=all(v['contrast_family']=='single_switch' for v in values)
    strict=cats['strict_discordant']+cats['strict_concordant']
    out.update(P_A=math.fsum(v['I_A'] for v in values)/N,D=cats['strict_discordant']/N if ranks else None,
               categories={k:dict(count=cats[k],fraction=cats[k]/N) for k in CATEGORIES} if ranks else None,
               strict_only_discordance=(cats['strict_discordant']/strict if strict else None) if ranks else None,
               distributions={k:summary([v[k] for v in values]) for k in ('D_A','delta_P','delta_S','delta_f')},
               tau_frequency={str(t):sum(v['tau_A']==t for v in values) for t in range(1,T+2)},
               survival={str(t):sum(v['tau_A']>t for v in values)/N for t in range(T+1)},
               no_divergence_mass=sum(v['tau_A']==T+1 for v in values)/N)
    out['distributions']['offer_distance']=summary([v['offer_distance'] for v in values]) if values[0]['stratum']=='UG-P' else None
    return out


def inventory_metrics(configs,rounds_by_run,contrasts,invalid_reasons=None):
    """One extraction/run; all registered contrasts, including failed-full dependents.

    configs and contrasts are the exact registered inventory, not an inferred subset.
    Native validation/accepted-attempt selection remains an external prerequisite.
    """
    invalid_reasons=invalid_reasons or {}
    if set(rounds_by_run)-set(configs) or set(invalid_reasons)-set(configs):raise MetricError('Unknown run IDs')
    if len({c['contrast_id'] for c in contrasts})!=len(contrasts):raise MetricError('Duplicate contrast IDs')
    runs={};rows=[]
    for run_id,config in configs.items():
        if run_id in invalid_reasons:runs[run_id]=dict(status='INVALID',reason=invalid_reasons[run_id]);continue
        if run_id not in rounds_by_run:runs[run_id]=dict(status='MISSING',reason='ARTIFACT_INCOMPLETE');continue
        try:runs[run_id]=dict(status='VALID',metrics=episode_metrics(config,rounds_by_run[run_id]))
        except MetricError as e:runs[run_id]=dict(status='INVALID',reason=str(e))
    for contrast in contrasts:
        row=dict(contrast_id=contrast['contrast_id'],full_run_id=contrast['full_run_id'],comparison_run_id=contrast['comparison_run_id'],metrics=None)
        if any(row[k] not in runs for k in ('full_run_id','comparison_run_id')):raise MetricError('Unregistered contrast run reference')
        a=runs[row['full_run_id']];b=runs[row['comparison_run_id']]
        if a['status']!='VALID' or b['status']!='VALID':row.update(status='INVALID',reason='Missing/invalid paired side; preserve both originals')
        else:
            try:
                metrics=pair_metrics(a['metrics'],b['metrics'],contrast['contrast_family'])
                if any(k in contrast and contrast[k]!=metrics[k] for k in ('condition_id','pair_id','stratum')):
                    raise MetricError('Registered contrast identity mismatch')
                row.update(status='VALID',metrics=metrics)
            except MetricError as e:row.update(status='INVALID',reason=str(e))
        rows.append(row)
    return dict(interface_id=VERSION,run_inventory=runs,pair_metrics=rows,requested_runs=len(configs),
                extracted_runs=sum(r['status']=='VALID' for r in runs.values()),full_reuse='single extraction, multiple dependent contrasts',
                artifact_acceptance_authorized=False,experimental_rounds_executed=0)


def registered_cells(configs,contrasts,pair_rows):
    """Assemble every declared cell; never infer expected IDs from observed files."""
    groups={};known={c['contrast_id'] for c in contrasts}
    if len(known)!=len(contrasts) or set(r['contrast_id'] for r in pair_rows)-known:
        raise MetricError('Duplicate/unknown registered contrast inventory')
    for c in contrasts:
        f=configs[c['full_run_id']];s=configs[c['comparison_run_id']];a=focal(s)
        stratum=('UG-P' if focal(f)['role']=='proposer' else 'UG-R') if f['game']=='UG' else f['game']
        key=(c['block'],stratum,c['contrast_family'],a['variant'],a['kind'],f['horizon'],f['selected_adapter_convention'],f['run_purpose'])
        groups.setdefault(key,[]).append(c['contrast_id'])
    result=[]
    for key,ids in groups.items():
        wanted=set(ids)
        rows=[r for r in pair_rows if r['contrast_id'] in wanted]
        result.append(dict(cell_key=list(key),summary=cell_summary(ids,rows,key[5])))
    return result


def alternative_readout(episode,aggregation='mean',weights=None,component=None):
    """Registered raw readouts only. No unresolved alternative rank divisor chosen."""
    s=episode['series'];T=episode['T'];indices=list(range(T))
    if aggregation=='terminal':indices=[T-1]
    elif aggregation=='last_half':
        if T%2:raise MetricError('Even horizon required for registered last-half readout')
        indices=list(range(T//2,T))
    elif aggregation!='mean':raise MetricError('Unknown aggregation')
    if aggregation!='mean' and (weights is not None or component is not None):raise MetricError('No unregistered combined readout axes')
    if weights is not None and component is not None:raise MetricError('No unregistered combined readout')
    if weights is not None:
        if len(weights)!=3:raise MetricError('Three registered lambda weights required')
        weights=tuple(finite(v) for v in weights)
        if tuple(weights) not in [(w,m,f) for w in (.5,1,2) for m in (0,.5,1) for f in (0,.5,1)]:raise MetricError('Unregistered lambda row')
        q=[weights[0]*x['Wtilde']+weights[1]*x['m']-weights[2]*x['f'] for x in s['states']]
    elif component is not None:
        if component not in ('Wtilde','m','minus_f'):raise MetricError('Unknown component')
        q=[-x['f'] if component=='minus_f' else x[component] for x in s['states']]
    else:q=[x['S'] for x in s['states']]
    return dict(P=math.fsum(s['payoffs'][i] for i in indices)/len(indices),Q=math.fsum(q[i] for i in indices)/len(indices),
                post_round_indices=[i+1 for i in indices],rank_convention_status='PAP_OWNER_DISPOSITION_REQUIRED',
                normalized_delta_Q=None,rank_Q=None,strict_discordance=None)
