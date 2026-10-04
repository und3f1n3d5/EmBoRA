"""Direct frozen oracles; incomplete P2 coverage. No pilot/frame/trajectory execution."""
import csv
import copy
import hashlib
import inspect
import itertools
import math
from fractions import Fraction
from pathlib import Path
import pytest
from journal_reference_v1.schema import *
from journal_reference_v1.games import *
from journal_reference_v1.formulas import *
from journal_reference_v1.engine import sampling_unit_ids


def source_config(game='UG', purpose='structural_fixture', adapter='normative_resisted_inequity_v1'):
    return {'schema_id': SCHEMA_ID, 'specification_id': SPEC_ID, 'condition_id': 'AT-config', 'pair_id': 'AT-pair',
            'game': game, 'focal_agent_id': 2, 'selected_adapter_convention': adapter, 'run_purpose': purpose,
            'horizon': 2 if purpose == 'structural_fixture' else 200,
            'agents': [{'agent_id': j, 'seat': j, 'role': ('proposer' if j == 1 else 'responder') if game == 'UG' else 'player',
                        'controller_type': 'model'} for j in (1, 2)]}


def state_at(v=.5, m=0., f=0., p=(1.,)*4, personality='neutral', intensity='neutral'):
    return State((float(v),)*4, (1.,)*4, tuple(p), float(m), float(f), personality, intensity)


ROWS = list(csv.DictReader((CONTRACT/'UG_OUTCOME_TABLE_R1C5.csv').open()))


@pytest.mark.parametrize('row', ROWS, ids=lambda r: r.get('row_id', str(list(r.values())[0])))
def test_AT_UG_ADAPTER_84_frozen_vectors(row):
    # Field names grounded in frozen CSV, exact rational data is the independent expected oracle.
    selection = row['adapter_key']
    adapter = Adapter(selection, 'sensitivity')
    offer = int(row['offer']); action = row['action']; role = row['role']; seat = 1 if role == 'proposer' else 2
    actions = [{'name':'offer','offer':offer},{'name':action}]
    q = adapter.raw('UG', seat, role, actions)
    expected = tuple(float(Fraction(row['q_'+k+'_exact'])) for k in K)
    assert q == pytest.approx(expected, abs=1e-12, rel=1e-12)
    assert all(0 <= x <= 1 for x in q)
    assert execute('UG', actions) == ((int(row['payoff_self']),int(row['payoff_other'])) if seat == 1 else (int(row['payoff_other']),int(row['payoff_self'])))
    assert adapter.adapter_id == row['adapter_id']
    assert '|'.join(REGISTRY['adapter_contract']['context_matrix'][selection]) == row['allowed_run_purpose']
    for context in row['allowed_run_purpose'].split('|'):
        assert Adapter(selection, context).raw('UG', seat, role, actions) == q


@pytest.mark.parametrize('adapter', REGISTRY['enums']['selected_adapter_convention'][1:])
@pytest.mark.parametrize('context', ['confirmatory_frame','structural_fixture'])
def test_AT_INVALID_prohibited_adapters(adapter, context):
    with pytest.raises(ConfigError): Adapter(adapter,context)


@pytest.mark.parametrize('game,actions,expected', [
 ('PD',[{'name':'C'},{'name':'C'}],[(.6,1,1,0),(.6,1,1,0)]),
 ('PD',[{'name':'C'},{'name':'D'}],[(0,0,0,.5),(1,0,1,1)]),
 ('PD',[{'name':'D'},{'name':'C'}],[(1,0,1,1),(0,0,0,.5)]),
 ('PD',[{'name':'D'},{'name':'D'}],[(.2,1,0,1),(.2,1,0,1)]),
 ('BoS',[{'name':'O'},{'name':'O'}],[(1,Fraction(2,3),1,1),(Fraction(2,3),Fraction(2,3),1,1)]),
 ('BoS',[{'name':'O'},{'name':'F'}],[(0,1,0,Fraction(1,3)),(0,1,0,Fraction(1,3))]),
 ('BoS',[{'name':'F'},{'name':'O'}],[(0,1,0,0),(0,1,0,0)]),
 ('BoS',[{'name':'F'},{'name':'F'}],[(Fraction(2,3),Fraction(2,3),1,1),(1,Fraction(2,3),1,1)])])
def test_AT_ADAPTER_PDBOS_direct_table(game, actions, expected):
    adapter = Adapter('normative_resisted_inequity_v1','structural_fixture')
    for seat in (1,2):
        assert adapter.raw(game,seat,'player',actions) == pytest.approx(tuple(float(x) for x in expected[seat-1]),abs=1e-12,rel=1e-12)


def test_AT_INIT_direct_and_serialization():
    cfg = prepare_config(source_config())
    s=State.from_primary(cfg['agents'][0]['initial_primary_state'],'neutral','neutral')
    assert s.pbar == (.25,)*4 and s.r == 1 and s.W == .5 and s.Wtilde == s.S == 0
    assert State.from_dict(parse_json(canonical(s.to_dict()))) == s
    bad=s.to_dict();bad['S']=.5
    with pytest.raises(StateError):State.from_dict(bad)
    for k in K:
        bad=s.to_dict();del bad['v'][k]
        with pytest.raises(StateError):State.from_dict(bad)
    for profile, p in REGISTRY['priority_profiles'].items():
        source=source_config();source['agents'][0]['priority_profile']=profile
        config=prepare_config(source)
        assert tuple(config['agents'][0]['initial_primary_state']['p'][k] for k in K)==tuple(p)
    assert set(cfg)==set(REGISTRY['effective_config_contract']['required_no_default'])|set(REGISTRY['effective_config_contract']['common_default_resolution'])


@pytest.mark.parametrize('missing',REGISTRY['effective_config_contract']['required_no_default'])
def test_AT_INVALID_required_no_defaults(missing):
    source=source_config();del source[missing]
    with pytest.raises(ConfigError):prepare_config(source)


@pytest.mark.parametrize('mutation',[lambda c:c.update(adapter_convention='normative_resisted_inequity_v1'),
 lambda c:c.update(selected_adapter_convention=None),lambda c:c.update(run_purpose='conformance'),
 lambda c:c.update(model_mode='integrated_model'),lambda c:c.update(training=True),
 lambda c:c.update(training=0),lambda c:c.update(dqn_config={}),lambda c:c.update(refocus_config={}),
 lambda c:c.update(horizon=True),lambda c:c.update(horizon=0),lambda c:c.update(horizon=2.0),
 lambda c:c['agents'][0].update(role='responder'),lambda c:c['agents'][0].update(variant=['full','no_mood']),
 lambda c:c['agents'][0].update(agent_id=2),lambda c:c['agents'][0].update(personality='Neutral'),
 lambda c:c['agents'][0]['initial_primary_state']['p'].update(material=1.5),
 lambda c:c['agents'][0]['initial_primary_state'].update(m=math.nan),
 lambda c:c['agents'][0]['initial_primary_state'].update(S=0),
 lambda c:c['agents'][0].update(candidate_adapter_id='other')])
def test_AT_INVALID_closed_config(mutation):
    cfg=prepare_config(source_config());mutation(cfg)
    with pytest.raises(ContractError):validate_config(cfg)


def test_AT_INVALID_json_duplicate_nonfinite_and_action_types():
    for text in ('{"a":1,"a":2}','{"x":NaN}','{"x":Infinity}'):
        with pytest.raises(ContractError):parse_json(text)
    for offer in (True,2.,'2',0,9,math.nan,math.inf):
        with pytest.raises(ActionError):validate_action('UG','proposer',{'name':'offer','offer':offer})
    for action in ({'name':'accept','q':[]},{},{'name':'ACCEPT'}):
        with pytest.raises(ActionError):validate_action('UG','responder',action)


def test_AT_CHOICE_numerator_tie_neighbors_helpers():
    votes=(1,-1,1,1); p=(.5,1.5,.5,.5)
    t=directional_vote(p,votes)
    assert (t['N_VS'],t['P_VS'],t['D_VS'],t['category'],t['action'])==(0.,3.,0.,'tie_reject',{'name':'reject'})
    first=(.5,math.nextafter(1.5,-math.inf),.5,.5)
    second=(math.nextafter(.5,math.inf),1.5,.5,.5)
    for pp, expected in [(first,2**-52),(second,2**-53)]:
        trace=directional_vote(pp,votes)
        assert trace['N_VS']==expected and trace['action']=={'name':'accept'}
    for p in ((1.5,.5,.5,.5),(.5,.5,1.5,.5)):
        t=directional_vote(p,votes)
        assert t['N_VS']==2 and t['D_VS']==2/3 and t['category']=='positive_accept'
    assert classify_numerator(-2**-52)==('negative_reject',{'name':'reject'})  # HELPER-ONLY, not legal N/B priorities
    for perm in itertools.permutations(K):
        pp={k:dict(zip(K,(.5,1.5,.5,.5)))[k] for k in perm}
        zz={k:dict(zip(K,votes))[k] for k in perm}
        assert directional_vote(tuple(pp[k] for k in K),tuple(zz[k] for k in K))['category']=='tie_reject'


def test_AT_FOCUS_explicit_ties_null():
    assert focus((.25,)*4,(.1,.1,0.,0.))=='material'
    assert focus((.25,)*4,(0.,.1,.1,0.))=='fairness'
    assert focus((.25,)*4,(0.,)*4) is None


@pytest.mark.parametrize('gain',[True,False],ids=['gain_near_desired','loss_near_zero'])
def test_AT_URGENCY_near_epsilon_frozen_scientific_oracle(gain):
    # C5 S06-D and S12 AT-URGENCY: ±alpha/2, with table tolerance 1e-12.
    v=1-C['epsilon']/2 if gain else C['epsilon']/2
    # Material q=1 from legal offer-8 acceptance; q=0 from offer-5 rejection.
    adapter=Adapter('normative_resisted_inequity_v1','structural_fixture')
    q=adapter.raw('UG',2,'responder',[{'name':'offer','offer':8 if gain else 5},{'name':'accept' if gain else 'reject'}])
    projected=projection(state_at(v), q)
    expected=7/40 if gain else -7/40  # exact rational independent oracle
    observed=projected['uhat_signed']['material']
    assert math.isclose(observed,expected,abs_tol=1e-12,rel_tol=1e-12), (observed,expected,abs(observed-expected))


def test_AT_URGENCY_helper_only_and_invalid_domain():
    assert urgency(.5,.6,.5)==1  # helper-only saturation; not production d/recurrence
    assert urgency(.5,.4,1)==pytest.approx(-.2)
    assert urgency(.5,.5,1)==0
    with pytest.raises(ContractError):urgency(0,-.1,1)
    with pytest.raises(ContractError):urgency(.5,.6,1,0)
    assert normalize(2,2,2)==1 and inverse_regret(0,0)==1  # helper-only zero ranges
    with pytest.raises(ContractError):inverse_regret(1,0)


@pytest.mark.parametrize('iota,offer',[(-1.5,3),(-1.499,4),(-.5,4),(-.499,5),(.5,5),(.501,6),(1.5,6)])
def test_AT_UG_OFFER_direct_boundaries(iota,offer):
    assert ug_offer(iota)=={'name':'offer','offer':offer}
    assert ug_offer(iota,reversed(OFFERS))=={'name':'offer','offer':offer}


def test_AT_THRESHOLD_equalities_and_declared_witness():
    for m in (-.25,.25):
        s=state_at(m=m);assert threshold(s)==.75
    s=state_at(f=.6);assert s.r==.4 and threshold(s)==.75*(1-.45*.6)
    assert threshold(state_at(m=-.2501))==.63
    assert threshold(state_at(m=.2501))==.8
    assert select_branch('hybrid',.75,.75)=='R'
    fixture=state_at(m=.5,f=.9,personality='pessimistic',intensity='high')
    assert impulse(fixture,'hybrid')==pytest.approx(.2775,abs=1e-12)
    assert threshold(fixture)==pytest.approx(.27725,abs=1e-12)
    assert select_branch('hybrid',impulse(fixture,'hybrid'),threshold(fixture))=='E'
    assert select_branch('hybrid',impulse(fixture,'hybrid'),fixture.chi1)=='R'
    assert impulse(fixture,'rational_only')==0


def test_AT_PD_equalities_and_kind_matrix():
    assert pd_proposals(-.25,-.2,'hybrid')==({'name':'C'},{'name':'C'})
    assert pd_proposals(0,1.5,'rational_only')==({'name':'C'},{'name':'D'})
    assert pd_proposals(0,1.5,'emotional_only')==({'name':'C'},{'name':'C'})
    assert convention(1)=={'name':'O'} and convention(2)=={'name':'F'}


def test_AT_IDENTITY_adapter_and_purpose_distinct():
    keys_seen=[]
    for selection, contexts in REGISTRY['adapter_contract']['context_matrix'].items():
        for context in contexts:
            cfg=prepare_config(source_config(purpose=context,adapter=selection));cfg['horizon']=200
            keys_seen.append(condition_identity(cfg,'fixture-identity'))
    assert len(keys_seen)==len(set(keys_seen))==5
    cfg=prepare_config(source_config());other=copy.deepcopy(cfg);other['agents'][1]['variant']='no_suppression'
    assert condition_identity(cfg,'f')==condition_identity(other,'f')


def test_AT_RNG_fixed_input_units_no_population():
    same=[{'draw_id':'same_action_1','independent_cluster_id':'U1'}, {'draw_id':'same_action_2','independent_cluster_id':'U2'}]
    different=[{'draw_id':'U_action','independent_cluster_id':'U'}, {'draw_id':'one_minus_U_action','independent_cluster_id':'U'}]
    assert sampling_unit_ids(same,'stochastic')==['U1','U2']
    assert sampling_unit_ids(different,'stochastic')==['U']
    assert sampling_unit_ids(same,'deterministic')==[]


def test_AT_LEGACY_import_isolation():
    import ast
    folder=Path(__file__).parents[1]
    forbidden=('agent_core','agent_fixed','emotional_agent','rational_new','torch','numpy','random')
    for path in folder.glob('*.py'):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node,ast.Import): names=[n.name for n in node.names]
            elif isinstance(node,ast.ImportFrom):names=[node.module or '']
            else:continue
            assert not any(name.split('.')[0] in forbidden for name in names)


def test_AT_PACKAGE_artifact_hashes():
    manifest=parse_json((CONTRACT/'R0_RECHECK_PACKAGE_MANIFEST_C5.json').read_text())
    assert len(manifest['review_files'])==13
    for entry in manifest['review_files']:
        data=(CONTRACT/entry['path']).read_bytes()
        assert len(data)==entry['bytes'] and hashlib.sha256(data).hexdigest()==entry['sha256']
    assert len(ROWS)==84
