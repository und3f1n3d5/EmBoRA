"""Synthetic precomputed PAP controls only. No generated trajectory or Engine import."""
import copy
import importlib.util
import math
from pathlib import Path
import sys
import pytest
from journal_reference_v1 import pap_metrics as m


def config(game='PD',seat=1,variant='full',kind='hybrid'):
    role=('proposer' if seat==1 else 'responder') if game=='UG' else 'player'
    return dict(game=game,horizon=4,focal_agent_id=1,condition_id='synthetic-condition',pair_id='synthetic-pair',
                run_purpose='structural_fixture',selected_adapter_convention='normative_resisted_inequity_v1',
                agents=[dict(agent_id=2,seat=3-seat,role='responder' if role=='proposer' else 'proposer' if game=='UG' else 'player',controller_type='baseline',baseline_id='test-control'),
                        dict(agent_id=1,seat=seat,role=role,controller_type='model',variant=variant,kind=kind,initial_primary_state={'v':.5})])


def records(c,payoffs=(5,0,5,0),states=(-1,-1,-1,-1),actions=None):
    a=m.focal(c);idx=a['seat']-1;game=c['game'];T=len(payoffs);c['horizon']=T
    if actions is None:actions=[{'name':'C'} if game=='PD' else {'name':'O'} if game=='BoS' else {'name':'offer','offer':2} if a['role']=='proposer' else {'name':'accept'} for _ in range(T)]
    out=[]
    for i,(p,S,action) in enumerate(zip(payoffs,states,actions),1):
        state={'S':S,'f':0.,'m':0.,'Wtilde':S,'W':.5,'r':1.,'v':{k:.5 for k in ('material','fairness','relationship','safety')}}
        d={'aE':copy.deepcopy(action),'aR':copy.deepcopy(action),'selected_branch':'R','theta':.5,'theta_reference':.5,
           'choice':{'category':'tie_reject','N_VS':0.,'D_VS':0.}}
        u={'Csup_raw':0.,'Csup_applied':0.,'fatigue_preclip':0.,'mood_preclip':0.}
        r={k:c[k] for k in ['game','condition_id','pair_id','run_purpose','selected_adapter_convention']}
        r.update(round=i,failure_status=None,actions_by_seat=[{'name':'C'}, {'name':'C'}],payoffs_by_seat=[0.,0.],
                 post_states_by_seat=[None,None],pre_states_by_seat=[{'S':999.},{'S':999.}],decisions_by_seat=[None,None],updates_by_seat=[None,None])
        for key,val in [('actions_by_seat',action),('payoffs_by_seat',p),('post_states_by_seat',state),('decisions_by_seat',d),('updates_by_seat',u)]:r[key][idx]=copy.deepcopy(val)
        out.append(r)
    return out


def pair(game='PD',seat=1):
    f=config(game,seat);s=config(game,seat,'no_mood');rf=records(f);rs=records(s,(0,0,0,0),(1,1,1,1),[{'name':'C'},{'name':'D'},{'name':'C'},{'name':'D'}] if game=='PD' else None)
    return f,s,rf,rs


def test_post_round_no_S0_and_focal_identity_seat_binding():
    f,s,rf,rs=pair(seat=2);a=m.episode_metrics(f,rf);b=m.episode_metrics(s,rs);p=m.pair_metrics(a,b)
    assert a['P']==2.5 and a['Q']==-1 and b['Q']==1
    assert p['delta_P']==2.5 and p['delta_S']==-2
    assert p['normalized_delta_P']==.5 and p['normalized_delta_Q']==-.5
    assert p['tau_A']==2 and p['I_A']==1 and p['D_A']==.5
    assert p['category']=='strict_discordant' and p['strict_discordance']==1
    assert all(r['post_states_by_seat'][0] is None for r in rf)


@pytest.mark.parametrize('stratum,max_payoff',[('PD',5),('BoS',3),('UG-P',8),('UG-R',8)])
def test_predeclared_payoff_divisors(stratum,max_payoff):
    game='UG' if stratum.startswith('UG') else stratum;seat=2 if stratum=='UG-R' else 1
    f=config(game,seat);s=config(game,seat,'no_mood')
    a=m.episode_metrics(f,records(f,[max_payoff]*4,[1]*4));b=m.episode_metrics(s,records(s,[0]*4,[-1]*4))
    result=m.pair_metrics(a,b);assert result['normalized_delta_P']==1 and result['normalized_delta_Q']==.5


@pytest.mark.parametrize('x,expected',[(0,0),(1e-9,0),(-1e-9,0),(math.nextafter(1e-9,math.inf),1),(math.nextafter(-1e-9,-math.inf),-1)])
def test_cutoff_equality_and_nearest_neighbors(x,expected):assert m.rank_sign(x)==expected


@pytest.mark.parametrize('rp,rq,cat',[(1,-1,'strict_discordant'),(-1,1,'strict_discordant'),(1,1,'strict_concordant'),(-1,-1,'strict_concordant'),(0,0,'both_tied'),(0,1,'payoff_only_tied'),(0,-1,'payoff_only_tied'),(1,0,'state_only_tied'),(-1,0,'state_only_tied')])
def test_five_exhaustive_rank_categories(rp,rq,cat):assert m.tie_category(rp,rq)==cat


def test_nearest_rank_even_odd_medians_and_sign_shares():
    d=m.summary(list(range(10,101,10)));assert d['median']==55 and d['p10']==10 and d['p90']==90 and d['mean']==55
    assert m.summary([3,1,2])['median']==2
    assert m.summary([-1,0,1])['positive']==m.summary([-1,0,1])['negative']==m.summary([-1,0,1])['zero']==1/3


def test_no_divergence_and_UG_proposer_distance():
    f=config('UG',1);s=config('UG',1,'no_mood');af=[{'name':'offer','offer':x} for x in [2,4,8,8]];ab=[{'name':'offer','offer':x} for x in [2,8,2,8]]
    a=m.episode_metrics(f,records(f,[8,6,2,0],[0,1,2,1],af));b=m.episode_metrics(s,records(s,[8,2,8,0],[0,0,0,0],ab));p=m.pair_metrics(a,b)
    assert p['offer_distance']==pytest.approx(5/12) and p['D_A']==.5 and p['tau_A']==2
    same=m.pair_metrics(a,m.episode_metrics(s,records(s,[8,6,2,0],[0,1,2,1],af)))
    assert same['tau_A']==5 and same['I_A']==same['D_A']==0 and same['category']=='both_tied'


def test_all_cell_denominator_categories_survival_and_no_dedup():
    f,s,rf,rs=pair();p=m.pair_metrics(m.episode_metrics(f,rf),m.episode_metrics(s,rs));same=copy.deepcopy(p);same.update(condition_id='second-condition',tau_A=5,I_A=0,D_A=0,category='both_tied',strict_discordance=0)
    rows=[{'contrast_id':'a','status':'VALID','metrics':p},{'contrast_id':'b','status':'VALID','metrics':same}]
    d=m.cell_summary(['a','b'],rows,4);assert d['P_A']==d['D']==.5 and d['categories']['both_tied']['fraction']==.5
    assert sum(v['count'] for v in d['categories'].values())==2 and sum(v['fraction'] for v in d['categories'].values())==1
    assert d['tau_frequency']=={'1':0,'2':1,'3':0,'4':0,'5':1};assert d['survival']=={'0':1,'1':1,'2':.5,'3':.5,'4':.5}
    assert d['no_divergence_mass']==.5 and d['strict_only_discordance']==1
    rows[1]['metrics']=copy.deepcopy(p);rows[1]['metrics']['condition_id']='second-condition';assert m.cell_summary(['a','b'],rows,4)['N_valid']==2
    d=m.cell_summary(['a','b'],rows[:1],4);assert d['N_expected']==2 and d['N_valid']==1 and d['P_A'] is d['D'] is None


def test_full_reuse_missing_full_and_invalid_dependents():
    f,s,rf,rs=pair();k=config(kind='emotional_only');rk=records(k)
    configs={'full':f,'switch':s,'kind':k};contrasts=[dict(contrast_id='x',full_run_id='full',comparison_run_id='switch',contrast_family='single_switch'),dict(contrast_id='y',full_run_id='full',comparison_run_id='kind',contrast_family='kind_control')]
    d=m.inventory_metrics(configs,{'full':rf,'switch':rs,'kind':rk},contrasts);assert d['extracted_runs']==3 and all(r['status']=='VALID' for r in d['pair_metrics'])
    assert d['pair_metrics'][1]['metrics']['category'] is None
    for source,invalid in [({'switch':rs,'kind':rk},{}),({'full':rf,'switch':rs,'kind':rk},{'full':'SPEC_ORACLE'})]:
        d=m.inventory_metrics(configs,source,contrasts,invalid);assert all(r['status']=='INVALID' and r['metrics'] is None for r in d['pair_metrics'])


@pytest.mark.parametrize('field',['horizon','pair_id','selected_adapter_convention','run_purpose','agents'])
def test_unmatched_pair_rejects(field):
    f,s,rf,rs=pair();a=m.episode_metrics(f,rf);b=m.episode_metrics(s,rs)
    if field=='agents':b['config']['agents'][0]['baseline_id']='changed-opponent'
    else:b['config'][field]='changed'
    with pytest.raises(m.MetricError):m.pair_metrics(a,b)


@pytest.mark.parametrize('mutation',[lambda r:r.pop(),lambda r:r[0].update(round=0),lambda r:r[0].update(round=True),lambda r:r[0].update(failure_status='error'),lambda r:r[0]['payoffs_by_seat'].__setitem__(0,float('nan')),lambda r:r[0]['post_states_by_seat'].__setitem__(0,None)])
def test_missing_invalid_native_never_imputed(mutation):
    c=config();r=records(c);mutation(r)
    with pytest.raises(m.MetricError):m.episode_metrics(c,r)


def test_prior_disagreement_is_inclusive_and_never_future_conditioned():
    f,s,rf,rs=pair();rf[1]['decisions_by_seat'][0]['aR']={'name':'D'}
    p=m.pair_metrics(m.episode_metrics(f,rf),m.episode_metrics(s,rs));d=p['divergence_conditioned_full']
    assert d['with_prior_disagreement_all_rounds']==.5 and d['with_same_round_disagreement_all_rounds']==.25
    assert d['with_prior_disagreement_given_divergence']==1


def test_cost_clip_summaries_and_BoS_null_control():
    c=config('BoS');r=records(c)
    for i,x in enumerate(r):x['updates_by_seat'][0].update(Csup_raw=[0,1,1,0][i],Csup_applied=0,fatigue_preclip=[-.1,0,.5,1.1][i])
    a=m.episode_metrics(c,r);assert a['cost_raw_mean']==.5 and a['cost_applied_mean']==0 and a['nonzero_cost_rate']==.5
    assert a['fatigue_clip_fractions']=={'below0':.25,'within':.5,'above1':.25}
    s=copy.deepcopy(c);s['agents'][1]['variant']='no_suppression';b=m.episode_metrics(s,records(s));p=m.pair_metrics(a,b)
    assert p['BoS_behavior_identifiability']=='not_identifiable' and p['I_A']==0 and p['offer_distance'] is None


def test_registered_alternative_readouts_do_not_choose_rank_convention():
    c=config();e=m.episode_metrics(c,records(c,[1,2,3,4],[-1,-.5,.5,1]))
    assert m.alternative_readout(e,'terminal')['P']==4
    h=m.alternative_readout(e,'last_half');assert h['P']==3.5 and h['Q']==.75 and h['post_round_indices']==[3,4]
    assert h['rank_Q'] is h['normalized_delta_Q'] is h['strict_discordance'] is None
    assert len([m.alternative_readout(e,weights=(w,mood,f)) for w in (.5,1,2) for mood in (0,.5,1) for f in (0,.5,1)])==27
    with pytest.raises(m.MetricError):m.alternative_readout(e,weights=(7,1,1))


def test_no_engine_import_and_no_artifact_acceptance():
    assert 'journal_reference_v1.engine' not in sys.modules


@pytest.mark.parametrize('value',[None,True,'0',float('nan'),float('inf')])
def test_invalid_scalar_rejects(value):
    with pytest.raises(m.MetricError):m.rank_sign(value)

def test_UG_vote_uses_N_only_and_exact_tie():
    c=config('UG',2);r=records(c);tiny=math.nextafter(0.,1.)
    for row,n,cat in zip(r,[-tiny,0.,tiny,1.],['negative_reject','tie_reject','positive_accept','positive_accept']):
        row['decisions_by_seat'][1]['choice'].update(N_VS=n,D_VS=0.,category=cat)
    e=m.episode_metrics(c,r);assert e['vote_categories']=={'negative_reject':1,'tie_reject':1,'positive_accept':2}
    r[0]['decisions_by_seat'][1]['choice']['category']='tie_reject'
    with pytest.raises(m.MetricError):m.episode_metrics(c,r)

def test_no_stateless_focal_pseudo_state_and_no_combined_axes():
    c=config();r=records(c);e=m.episode_metrics(c,r)
    c['agents'][1]['controller_type']='baseline'
    with pytest.raises(m.MetricError):m.episode_metrics(c,r)
    with pytest.raises(m.MetricError):m.alternative_readout(e,'terminal',weights=(1,.5,.5))

def test_duplicate_condition_and_mixed_switch_cells_reject():
    f,s,rf,rs=pair();p=m.pair_metrics(m.episode_metrics(f,rf),m.episode_metrics(s,rs))
    rows=[dict(contrast_id=k,status='VALID',metrics=copy.deepcopy(p)) for k in ['a','b']]
    with pytest.raises(m.MetricError):m.cell_summary(['a','b'],rows,4)
    rows[1]['metrics'].update(condition_id='second',comparison_variant='no_fatigue')
    with pytest.raises(m.MetricError):m.cell_summary(['a','b'],rows,4)

def test_all_tied_cell_has_no_strict_only_denominator():
    f,s,rf,rs=pair();p=m.pair_metrics(m.episode_metrics(f,rf),m.episode_metrics(s,records(s)))
    d=m.cell_summary(['a'],[dict(contrast_id='a',status='VALID',metrics=p)],4)
    assert d['D']==0 and d['strict_only_discordance'] is None and d['no_divergence_mass']==1
    assert m.summary([-1e-12,0.,1e-12])['zero']==1/3


def test_registered_cells_uses_expected_inventory_not_observed_subset():
    f,s,rf,rs=pair();c=dict(block='base',contrast_family='single_switch',contrast_id='x',full_run_id='f',comparison_run_id='s')
    d=m.inventory_metrics({'f':f,'s':s},{'f':rf,'s':rs},[c]);cells=m.registered_cells({'f':f,'s':s},[c],d['pair_metrics'])
    assert len(cells)==1 and cells[0]['summary']['N_expected']==1 and cells[0]['summary']['status']=='COMPLETE'
    cells=m.registered_cells({'f':f,'s':s},[c],[])
    assert cells[0]['summary']['status']=='INCOMPLETE' and cells[0]['summary']['N_expected']==1 and cells[0]['summary']['D'] is None


def test_diagnostic_first_times_use_post_round_and_continuous_tolerance():
    f,s,rf,rs=pair();rs=records(s,states=(-1,-1,-1,-1))
    rs[1]['decisions_by_seat'][0]['aE']={'name':'D'}
    rs[2]['decisions_by_seat'][0]['theta']=.5+2e-12
    rs[3]['post_states_by_seat'][0]['v']['material']=.5+1e-6
    rs[0]['pre_states_by_seat'][0]['S']=-999
    p=m.pair_metrics(m.episode_metrics(f,rf),m.episode_metrics(s,rs))
    assert p['tau_proposal']==p['tau_E']==2 and p['tau_R']==5
    assert p['tau_threshold']==3 and p['tau_threshold_reference']==5 and p['tau_state']==4


def test_boolean_lambda_does_not_alias_registered_numeric_weight():
    c=config();e=m.episode_metrics(c,records(c))
    with pytest.raises(m.MetricError):m.alternative_readout(e,weights=(True,.5,.5))
