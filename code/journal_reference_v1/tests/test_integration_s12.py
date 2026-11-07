"""Complete remaining bounded S12: pure integrations and necessary short episodes."""
import copy
import itertools
import math
import subprocess
import sys
from pathlib import Path
import pytest
from journal_reference_v1.schema import *
from journal_reference_v1.games import *
from journal_reference_v1.model import *
from journal_reference_v1.engine import *
from journal_reference_v1.cli import validate_artifact, validate_config_text, expected_events
from journal_reference_v1.numeric import bits
from journal_reference_v1.evidence import oracle
from fractions import Fraction as Q
from expected_oracles import raw as expected_raw, update as expected_update, derived as expected_derived, impulse as expected_impulse, threshold as expected_threshold
from test_partial_conformance import source_config, state_at, ROWS


def fixture(game='UG',variant='full',kind='hybrid',v=.5,m=0.,f=0.,profile='equal',personality='neutral',intensity='neutral',horizon=1,baseline=None):
    source=source_config(game);source['horizon']=horizon
    source['agents'][1].update(variant=variant,kind=kind,priority_profile=profile,personality=personality,intensity=intensity)
    if baseline:
        source['agents'][0]={'agent_id':1,'seat':1,'role':'proposer' if game=='UG' else 'player','controller_type':'baseline','baseline_id':baseline}
    config=prepare_config(source)
    primary=config['agents'][1]['initial_primary_state'];primary['v']=mapping((v,)*4);primary['m']=m;primary['f']=f
    validate_config(config)
    return config


def engine(config,test_id='AT-EVENT'):
    return Engine(config,P2ConformanceAuthority(U1_ID,test_id,'bounded-fixture'))


@pytest.mark.parametrize('game',['PD','BoS','UG'])
def test_AT_EVENT_spies_exact_order_single_execution_two_results_before_updates(game,monkeypatch):
    import journal_reference_v1.engine as module
    e=engine(fixture(game,horizon=2));calls=[]
    execute_original=module.execute;build_original=Result.build.__func__;update_original=Agent.prepare_update
    def execute_spy(*args):calls.append('execute');return execute_original(*args)
    def build_spy(cls,*args,**kwargs):calls.append('result');return build_original(cls,*args,**kwargs)
    def update_spy(self,*args):calls.append('update');return update_original(self,*args)
    monkeypatch.setattr(module,'execute',execute_spy);monkeypatch.setattr(Result,'build',classmethod(build_spy));monkeypatch.setattr(Agent,'prepare_update',update_spy)
    for t in (1,2):
        r=e.step();assert r['event_order']==expected_events(game)
        assert calls[-5:]==['execute','result','result','update','update']
        assert r['event_counters']['total_updates_by_seat']==[t,t]
        assert all(o['history']==r['observations_by_seat'][0]['history'] for o in r['observations_by_seat'])
        assert r['observations_by_seat'][0]['history']==e.history[:-1]
        if game=='UG':
            assert 'current_offer' not in r['observations_by_seat'][0]
            assert r['observations_by_seat'][1]['current_offer']==r['actions_by_seat'][0]['offer']
    saved=(e.states,e.records,e.history,e.update_counters,e.execution_counter)
    with pytest.raises(UpdateError):e.step()
    assert saved==(e.states,e.records,e.history,e.update_counters,e.execution_counter)


@pytest.mark.parametrize('game',['PD','BoS','UG'])
@pytest.mark.parametrize('variant',REGISTRY['enums']['variant'])
def test_AT_STATE_SWITCH_golden_three_rounds_independent_RN_substitution(game,variant):
    baseline={'PD':'PD_AllD','BoS':'BoS_Convention','UG':'UG_Offer2'}[game]
    cfg=fixture(game,variant=variant,horizon=3,baseline=baseline)
    records=engine(cfg,'AT-STATE').run()
    a=cfg['agents'][1]; pre=copy.deepcopy(a['initial_primary_state'])
    pre.update(personality=a['personality'],intensity=a['intensity'])
    if variant=='no_mood':pre['m']=0.
    if variant=='no_fatigue':pre['f']=0.
    pre.update(expected_derived([pre['v'][k] for k in K],[pre['p'][k] for k in K],pre['m'],pre['f']))
    for t,r in enumerate(records,1):
        assert r['pre_states_by_seat'][1]==pre
        iota=expected_impulse(pre,a['kind']);theta_reference=expected_threshold(pre)
        theta=clip(.15,1.25,REGISTRY['personality_map'][a['personality']]) if variant=='fixed_threshold' else theta_reference
        if game=='PD':
            aE={'name':'C' if iota>=C['pd_emotional_cut'] else 'D'}
            aR={'name':'D' if a['kind']=='rational_only' else 'C' if pre['S']>=C['pd_rational_state_cut'] else 'D'}
            opponent={'name':'D'}
        elif game=='BoS':
            aE=aR={'name':'O' if t%2 else 'F'};opponent=aE
        else:
            answer=oracle.vote(2,'N',[Q.from_float(float(pre['v'][k])) for k in K],[Q(pre['p'][k]) for k in K])[4]
            aE={'name':answer};aR={'name':'accept'};opponent={'name':'offer','offer':2}
        branch='E' if a['kind']=='emotional_only' else 'R' if a['kind']=='rational_only' else 'E' if abs(iota)>theta else 'R'
        actions=[opponent,aE if branch=='E' else aR]
        assert r['actions_by_seat']==actions
        decision=r['decisions_by_seat'][1]
        assert (decision['iota'],decision['theta_reference'],decision['aE'],decision['aR'],decision['selected_branch'])==(iota,theta_reference,aE,aR,branch)
        q=expected_raw(game,actions,2,cfg['selected_adapter_convention'])
        post,update=expected_update(pre,q,a['kind'],variant,aE,actions[1])
        assert r['updates_by_seat'][1]['raw_q']==mapping(q)
        for field,value in update.items(): assert r['updates_by_seat'][1][field]==value,field
        assert r['post_states_by_seat'][1]==post
        assert r['pre_states_by_seat'][0] is None and r['post_states_by_seat'][0] is None
        assert r['updates_by_seat'][1]['update_count']==1
        pre=post
    assert len(records)==3


@pytest.mark.parametrize('kind',REGISTRY['enums']['model_kind'])
@pytest.mark.parametrize('variant',REGISTRY['enums']['variant'])
@pytest.mark.parametrize('v,m,f',[(0.,-.5,0.),(.5,0.,0.),(1.,.5,1.),(.013,.2,.5)])
def test_AT_BOS_all_states_switches_kinds_equal_proposals(kind,variant,v,m,f):
    cfg=fixture('BoS',variant,kind,v,m,f,horizon=2)
    e=engine(cfg,'AT-BOS');a=e.agents[1];s=a.initial_state
    for t in (1,2):
        history=[] if t==1 else [{'round':1,'actions_by_seat':[{'name':'O'},{'name':'O'}],'payoffs_by_seat':[3,2]}]
        obs=observation(cfg,a.descriptor,history)
        d=a.decide({'public_observation':obs,'own_pre_state':s.to_dict()})
        assert d['aE']==d['aR']==d['action']=={'name':'O' if t==1 else 'F'}


def test_AT_BOS_even_odd_short_control_totals():
    for horizon,expected in [(2,(5,5)),(3,(8,7))]:
        cfg=fixture('BoS',horizon=horizon);r=engine(cfg,'AT-BOS').run()
        assert tuple(sum(row['payoffs_by_seat'][j] for row in r) for j in (0,1))==expected
    cfg=prepare_config(source_config('BoS',purpose='confirmatory_frame'));cfg['horizon']=201
    with pytest.raises(ConfigError):validate_config(cfg)


@pytest.mark.parametrize('offer',[2,8])
@pytest.mark.parametrize('profile',['material_high','fairness_high','relationship_high'])
def test_AT_UG_POLICY_neutral_R_null_declared_injected_high_E(offer,profile):
    for injected in (False,True):
        cfg=fixture(profile=profile,m=-.5 if injected else 0.,intensity='high' if injected else 'neutral',baseline='UG_Offer'+str(offer))
        r=engine(cfg,'AT-UG-POLICY').step();d=r['decisions_by_seat'][1]
        reject=profile=='fairness_high'
        assert d['aE']=={'name':'reject' if reject else 'accept'} and d['aR']=={'name':'accept'}
        assert d['choice']['N_VS']==(0 if reject else 2)
        assert d['choice']['D_VS']==(0 if reject else 2/3)
        assert d['selected_branch']==('E' if injected else 'R')
        assert d['action']==(d['aE'] if injected else d['aR'])
        assert d['iota']==expected_impulse(d['decision_pre_state'],'hybrid')
        assert d['iota']==pytest.approx(-.75 if injected else 0.,abs=1e-12)
        if injected:assert d['theta']==.63  # legal injected state, no neutral-reachability assertion


@pytest.mark.parametrize('variant',REGISTRY['enums']['variant'])
def test_AT_SWITCH_single_entry_points_and_fixed_opponent(variant):
    full=fixture('PD',v=.5,m=.5,f=.9,personality='pessimistic',intensity='high')
    changed=copy.deepcopy(full);changed['agents'][1]['variant']=variant
    assert changed['agents'][0]==full['agents'][0]
    baseline=engine(full,'AT-SWITCH').step();r=engine(changed,'AT-SWITCH').step();d=r['decisions_by_seat'][1]
    if variant=='fixed_threshold':assert (d['selected_branch'],d['aE'],d['aR'],d['action'])==('R',{'name':'C'},{'name':'D'},{'name':'D'})
    if variant=='no_mood':assert engine(changed).agents[1].initial_source_state.m==.5 and d['decision_pre_state']['m']==0 and r['post_states_by_seat'][1]['m']==0
    if variant=='no_fatigue':assert engine(changed).agents[1].initial_source_state.f==.9 and d['decision_pre_state']['f']==0 and r['post_states_by_seat'][1]['f']==0 and r['post_states_by_seat'][1]['r']==1
    if variant=='no_suppression':assert d==baseline['decisions_by_seat'][1] and r['updates_by_seat'][1]['Csup_applied']==0
    if variant=='full':assert r==baseline


def test_AT_SUPPRESSION_same_round_cost_clip_null_inherited_unequal_states():
    def pair(m,f,kind='hybrid'):
        records=[]
        for variant in ('full','no_suppression'):
            records.append(engine(fixture('PD',variant,kind,m=m,f=f),'AT-SUPPRESSION').step())
        d=[r['decisions_by_seat'][1] for r in records];u=[r['updates_by_seat'][1] for r in records]
        assert d[0]==d[1]
        assert u[0]['raw_q']==u[1]['raw_q']
        assert u[0]['fatigue_preclip']-u[1]['fatigue_preclip']==pytest.approx(.03*u[0]['Csup_raw'],abs=1e-12)
        assert records[0]['post_states_by_seat'][1]['f']-records[1]['post_states_by_seat'][1]['f']==clip(0,1,u[0]['fatigue_preclip'])-clip(0,1,u[1]['fatigue_preclip'])
        return records,u
    r,u=pair(.2,.5)
    assert r[0]['decisions_by_seat'][1]['iota']==pytest.approx(.025,abs=1e-12)
    assert (r[0]['decisions_by_seat'][1]['aE'],r[0]['decisions_by_seat'][1]['aR'],r[0]['actions_by_seat'][1])==({'name':'C'},{'name':'D'},{'name':'D'})
    assert u[0]['sigma']==1 and u[0]['fatigue_preclip']-u[1]['fatigue_preclip']==pytest.approx(.00075,abs=1e-12)
    r,u=pair(.2,.5,'emotional_only');assert u[0]['sigma']==0 and r[0]['post_states_by_seat'][1]==r[1]['post_states_by_seat'][1]
    pair(.5,1.)  # saturated output checked against difference of clips
    a=engine(fixture('PD',kind='emotional_only',m=.2,f=.2),'AT-SUPPRESSION').step()
    b=engine(fixture('PD',variant='no_suppression',kind='emotional_only',m=.2,f=.7),'AT-SUPPRESSION').step()
    assert a['updates_by_seat'][1]['sigma']==b['updates_by_seat'][1]['sigma']==0 and a['post_states_by_seat'][1]!=b['post_states_by_seat'][1]


@pytest.mark.parametrize('v',[0.,-0.,.013,1.])
def test_AT_MATERIAL_common_helper_signed_bits_candidates_purity_single_update(v):
    records=[]
    for variant in ('full','material_only'):
        records.append(engine(fixture(variant=variant,v=v,kind='emotional_only',profile='fairness_high',baseline='UG_Offer8'),'AT-MATERIAL').step())
    full,mat=records;uf=full['updates_by_seat'][1];um=mat['updates_by_seat'][1]
    assert full['decisions_by_seat'][1]['choice']==mat['decisions_by_seat'][1]['choice']
    assert uf['raw_q']==um['raw_q'] and uf['delta']['material']==um['delta']['material']
    assert len(um['numeric_evidence'])==4
    for k in K[1:]:
        assert bits(um['q_star'][k])==bits(v) and bits(mat['post_states_by_seat'][1]['v'][k])==bits(v)
        assert all(bits(um[field][k])=='0000000000000000' for field in ('delta','u_signed','u'))
    assert mat['event_counters']['updates_this_round_by_seat']==[1,1]


@pytest.mark.parametrize('row',ROWS,ids=lambda r:r['row_id'])
def test_AT_UG_ADAPTER_candidate_and_realized_legal_outcome_helpers(row):
    # Legal-outcome mapping fixture, not a claim every outcome is policy reachable.
    selection=row['adapter_key'];adapter=Adapter(selection,'sensitivity');seat=1 if row['role']=='proposer' else 2
    actions=[{'name':'offer','offer':int(row['offer'])},{'name':row['action']}]
    expected=expected_raw('UG',actions,seat,selection)
    for state in (state_at(),state_at(.013,m=.5,f=1.,p=(1.5,.5,.5,.5)),state_at(1.)):
        q=adapter.raw('UG',seat,row['role'],actions)
        assert tuple(q)==tuple(expected)
        observed=projection(state,q)
        for k,v,target in zip(K,state.v,q):assert observed['vhat'][k]==oracle.graph(v,target)['ieee_nodes']['current']['float']
        if seat==2:
            candidate=candidate_choice(state,int(row['offer']),adapter)['candidates'][row['action']]
            assert candidate['q']==mapping(expected) and candidate['vhat']==observed['vhat']


def test_AT_UG_ADAPTER_monotonicity_symmetry_distinct_ids_raw_purity():
    adapters=[Adapter(s,'sensitivity') for s in REGISTRY['enums']['selected_adapter_convention']]
    assert len(set(a.adapter_id for a in adapters))==3
    values=[adapters[0].raw('UG',2,'responder',[{'name':'offer','offer':o},{'name':'reject'}])[1] for o in range(2,9)]
    assert values==list(reversed(values)) and values[3]==0.
    assert values[:4]==sorted(values[:4],reverse=True) and values[3:]==sorted(values[3:])


def test_AT_INIT_STATE_direct_aggregate_and_endpoint_helpers():
    for values,p,m,f in [((0.,)*4,(.01,3.,1.,.9),-.5,1.),((1.,)*4,(1.,)*4,.5,0.),((.13,.83,.21,.73),(.5,1.5,.5,.5),.2,.7)]:
        state=State(values,(1.,)*4,p,m,f,'neutral','neutral');expected=expected_derived(values,p,m,f)
        for key,value in expected.items():assert state.to_dict()[key]==value
        assert State.from_dict(state.to_dict())==state
    assert clip(-.5,.5,2.)==.5 and clip(0,1,-1.)==0  # helper-only arbitrary clipping


def test_AT_THRESHOLD_PD_neighbors_defined_rounded_operands():
    for cutoff in (-.25,.25):
        for direction in (-math.inf,math.inf):
            s=state_at(m=math.nextafter(cutoff,direction));assert threshold(s)==expected_threshold(s.to_dict())
    for f in (.6,math.nextafter(.6,-math.inf),math.nextafter(.6,math.inf)):
        s=state_at(f=f);assert threshold(s)==expected_threshold(s.to_dict())
    for value,branch in [(math.nextafter(.75,-math.inf),'R'),(.75,'R'),(math.nextafter(.75,math.inf),'E')]:assert select_branch('hybrid',value,.75)==branch
    for cut,field in [(-.25,'iota'),(-.2,'S')]:
        args=(math.nextafter(cut,-math.inf),0.) if field=='iota' else (0.,math.nextafter(cut,-math.inf))
        p=pd_proposals(*args,'hybrid');assert p[0 if field=='iota' else 1]=={'name':'D'}


def test_AT_SWITCH_identical_unprojected_source_state_one_step_entry_projection():
    for variant,field in [('no_mood','m'),('no_fatigue','f')]:
        cfg=fixture('PD',variant,m=.5,f=.9)
        agent=engine(cfg,'AT-SWITCH').agents[1]
        source=agent.initial_source_state
        decision=agent.decide({'public_observation':observation(cfg,agent.descriptor,[]),'own_pre_state':source.to_dict()})
        assert decision['source_pre_state'][field]==getattr(source,field)
        assert decision['decision_pre_state'][field]==0.


GOLDEN_ROWS=parse_json((Path(__file__).parent/'GOLDEN_CORES_C6_v1.0.json').read_text())
@pytest.mark.parametrize('row',GOLDEN_ROWS,ids=lambda r:r['fixture_id'])
def test_AT_STATE_golden_static_independent_fixtures(row):
    from expected_oracles import episode
    assert episode(row['effective_config'])==row['expected']
    actual=engine(row['effective_config'],'AT-STATE').run()
    for record,expected in zip(actual,row['expected']):
        assert record['round']==expected['round']
        assert record['pre_states_by_seat'][1]==expected['pre']
        assert record['actions_by_seat']==expected['actions']
        for key,value in expected['decision'].items():assert record['decisions_by_seat'][1][key]==value
        assert record['updates_by_seat'][1]['raw_q']==expected['raw_q']
        for key,value in expected['update'].items():assert record['updates_by_seat'][1][key]==value
        assert record['post_states_by_seat'][1]==expected['post']


def test_AT_UG_OFFER_POLICY_F19_all_kinds_roles_and_production_envelope():
    from expected_oracles import add
    for kind in REGISTRY['enums']['model_kind']:
        cfg=fixture();cfg['agents'][0]['kind']=kind
        proposer=Agent.construct(cfg,1,Adapter(cfg['selected_adapter_convention'],cfg['run_purpose']))
        obs=observation(cfg,proposer.descriptor,[])
        for intensity,v,m,f in itertools.product(REGISTRY['intensity_map'],(0.,.5,1.),(-.5,.5),(0.,1.)):
            cfg2=copy.deepcopy(cfg);cfg2['agents'][0]['intensity']=intensity
            agent=Agent.construct(cfg2,1,proposer.adapter)
            state=state_at(v,m,f,intensity=intensity)
            d=agent.decide({'public_observation':obs,'own_pre_state':state.to_dict()})
            expected_i=expected_impulse(state.to_dict(),kind)
            z=add(C['ug_offer_center'],clip(C['ug_proposer_impulse_min'],C['ug_proposer_impulse_max'],expected_i))
            expected=min(range(2,9),key=lambda offer:(abs(offer-z),offer))
            assert d['iota']==expected_i and d['aE']=={'name':'offer','offer':expected}
            assert expected in (4,5,6)  # production envelope, offer3 helper-only
            assert d['aR']=={'name':'offer','offer':4 if kind=='rational_only' else 5}
        cfg['agents'][1]['kind']=kind
        responder=Agent.construct(cfg,2,proposer.adapter)
        for offer in range(2,9):
            d=responder.decide({'public_observation':observation(cfg,responder.descriptor,[],offer),'own_pre_state':responder.initial_state.to_dict()})
            assert d['aR']=={'name':'accept'}


def test_AT_UG_ADAPTER_pure_sensitivity_candidate_realized_update_integration():
    """No Engine/sensitivity trajectory: pure update from labelled injected pre-state."""
    for selection in REGISTRY['enums']['selected_adapter_convention']:
        for kind in ('emotional_only','rational_only'):
            source=source_config(purpose='sensitivity',adapter=selection)
            source['agents'][0]={'agent_id':1,'seat':1,'role':'proposer','controller_type':'baseline','baseline_id':'UG_Cycle'}
            source['agents'][1].update(kind=kind,intensity='high',priority_profile='fairness_high')
            cfg=prepare_config(source);adapter=Adapter(selection,'sensitivity');agent=Agent.construct(cfg,2,adapter)
            state=state_at(.013,m=-.5,p=(.5,1.5,.5,.5),intensity='high')
            for offer in range(2,9):
                history=[{'round':t,'actions_by_seat':[{'name':'offer','offer':t+1},{'name':'accept'}],'payoffs_by_seat':[9-t,t+1]} for t in range(1,offer-1)]
                obs=observation(cfg,agent.descriptor,history,offer)
                payload={'public_observation':obs,'own_pre_state':state.to_dict()}
                decision=agent.decide(payload)
                actions=[{'name':'offer','offer':offer},decision['action']]
                result=Result.build('UG',offer-1,agent.descriptor,actions)
                before=canonical({'payload':payload,'decision':decision,'state':state.to_dict(),'result':result.to_dict()})
                post,trace=agent.prepare_update(state,obs,decision,result,offer-1)
                assert before==canonical({'payload':payload,'decision':decision,'state':state.to_dict(),'result':result.to_dict()})
                q=expected_raw('UG',actions,2,selection)
                expected_post,expected_trace=expected_update(state.to_dict(),q,kind,'full',decision['aE'],decision['action'])
                assert trace['raw_q']==mapping(q)==decision['choice']['candidates'][decision['action']['name']]['q']
                assert trace['adapter_id']==decision['adapter_id']==adapter.adapter_id and trace['update_count']==1
                assert post.to_dict()==expected_post
                for field,value in expected_trace.items():assert trace[field]==value
