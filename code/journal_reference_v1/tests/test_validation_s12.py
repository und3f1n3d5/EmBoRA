"""Typed negatives, full allowlist/leakage, baseline policies, artifact/CLI scope."""
import copy
import hashlib
import itertools
import json
import math
import subprocess
import sys
import os
import zipfile
from pathlib import Path
import pytest
from journal_reference_v1.schema import *
from journal_reference_v1.games import *
from journal_reference_v1.model import *
from journal_reference_v1.engine import *
from journal_reference_v1.cli import *
from test_integration_s12 import fixture, engine
from test_partial_conformance import source_config

DENIED = 'opponent_v opponent_d opponent_p opponent_m opponent_f opponent_r opponent_W opponent_Wtilde opponent_S opponent_personality opponent_intensity opponent_aE opponent_aR opponent_iota opponent_theta selected_branch current_response acceptance payoffs raw_q q_star appraisal post_state future_history rng_state trace logger'.split()


def run_cli(command):
    import conftest
    environment=os.environ.copy()
    environment['PYTHONPATH']=str(Path(__file__).resolve().parents[2])
    environment['PYTHONDONTWRITEBYTECODE']='1'
    result=subprocess.run(command,text=True,capture_output=True,env=environment)
    conftest.record_cli(command,result)
    return result


@pytest.mark.parametrize('game',['PD','BoS','UG'])
@pytest.mark.parametrize('field',DENIED)
@pytest.mark.parametrize('location',['payload','observation','descriptor','history','own_state'])
def test_AT_LEAK_deny_every_field_at_top_and_nested_levels(game,field,location):
    cfg=fixture(game,horizon=2);a=engine(cfg).agents[1];state=a.initial_state
    first=[{'name':'C'}]*2 if game=='PD' else [{'name':'O'}]*2 if game=='BoS' else [{'name':'offer','offer':2},{'name':'accept'}]
    history=[{'round':1,'actions_by_seat':first,'payoffs_by_seat':list(payoffs_for(game,first))}]
    obs=observation(cfg,a.descriptor,history,2 if game=='UG' else None)
    payload={'public_observation':obs,'own_pre_state':state.to_dict()}
    if location=='payload':payload[field]={}
    elif location=='observation':obs[field]={}
    elif location=='descriptor':obs['game_parameters'][field]={}
    elif location=='history':obs['history'][0][field]={}
    else:payload['own_pre_state'][field]={}
    before=canonical(payload)
    with pytest.raises(ContractError):a.decide(payload)
    assert canonical(payload)==before


@pytest.mark.parametrize('game',['PD','BoS','UG'])
def test_AT_LEAK_private_opponent_changes_public_fixed_own_trace_identical(game):
    cfg=fixture(game);other=copy.deepcopy(cfg)
    other['agents'][0].update(personality='optimistic',intensity='high')
    other['agents'][0]['initial_primary_state'].update(m=.5,f=.9,v=mapping((.013,)*4))
    for target in (0,1):
        config=cfg if target==0 else other;a=engine(config).agents[1]
        obs=observation(config,a.descriptor,[],2 if game=='UG' else None)
        payload={'public_observation':obs,'own_pre_state':a.initial_state.to_dict()};before=canonical(payload)
        actual=a.decide(payload);assert before==canonical(payload)
        if target==0:expected=actual
        else:assert actual==expected


@pytest.mark.parametrize('mutation',[
 lambda o:o.update(round=True), lambda o:o.update(round=2),lambda o:o.update(horizon=3),lambda o:o.update(agent_id=1),
 lambda o:o.update(current_offer=2.),lambda o:o.update(current_offer=9),lambda o:o['game_parameters'].update(endowment=11),
 lambda o:o['game_parameters'].update(offer_grid=[2,3,4,5,6,7,8,8]),lambda o:o['game_parameters'].update(offer_grid=[]),
 lambda o:o['game_parameters'].update(offer_grid=[8,7,6,5,4,3,2]),lambda o:o.update(legal_actions=[]),
 lambda o:o.update(history=[{'round':1,'actions_by_seat':[],'payoffs_by_seat':[]}])])
def test_AT_INVALID_observation_stages(mutation):
    cfg=fixture();a=engine(cfg).agents[1];obs=observation(cfg,a.descriptor,[],2);mutation(obs)
    with pytest.raises(ContractError):a.decide({'public_observation':obs,'own_pre_state':a.initial_state.to_dict()})


@pytest.mark.parametrize('field',['adapter_id','selected_adapter_convention','q','vhat','Deltahat','uhat_signed','uhat_absolute','numeric_evidence'])
def test_AT_INVALID_candidate_nested_trace_mismatch(field):
    cfg=fixture();e=engine(cfg);a=e.agents[1];state=a.initial_state;choice=candidate_choice(state,2,e.adapter)
    bad=copy.deepcopy(choice);bad['candidates']['accept'][field]=None
    with pytest.raises(TraceError):validate_choice(bad,state,2,e.adapter)


@pytest.mark.parametrize('field',['N_VS','P_VS','D_VS','category','action','z','p_clip','extra'])
def test_AT_INVALID_candidate_top_trace_mismatch(field):
    e=engine(fixture());s=e.states[1];bad=candidate_choice(s,8,e.adapter);bad[field]=None
    with pytest.raises(TraceError):validate_choice(bad,s,8,e.adapter)


def test_AT_INVALID_result_duplicate_stale_trace_state_before_mutation():
    cfg=fixture(horizon=2);e=engine(cfg);r=e.step();a=e.agents[1];state=State.from_dict(r['pre_states_by_seat'][1]);obs=r['observations_by_seat'][1];d=r['decisions_by_seat'][1];result=Result(canonical(r['results_by_seat'][1]))
    before=(e.states,e.history,e.records,e.update_counters)
    for data in (None,{},'result'):
        with pytest.raises(PayloadError):a.prepare_update(state,obs,d,data,1)
    with pytest.raises(UpdateError):a.prepare_update(state,obs,d,result,2)
    bad=copy.deepcopy(d);bad['action']={'name':'reject'}
    with pytest.raises(TraceError):a.prepare_update(state,obs,bad,result,1)
    malformed=result.to_dict();malformed['payoffs_by_seat'][1]=999
    with pytest.raises(PayloadError):a.prepare_update(state,obs,d,Result(canonical(malformed)),1)
    malformed=result.to_dict();malformed['extra']=1
    with pytest.raises(PayloadError):a.prepare_update(state,obs,d,Result(canonical(malformed)),1)
    e.update_counters=(1,0)
    with pytest.raises(UpdateError):e.step()
    assert e.states==before[0] and e.history==before[1] and e.records==before[2] and e.execution_counter==1
    assert e.failures[-1]['committed'] is False
    with pytest.raises(UpdateError):e.step()


def test_AT_INVALID_dynamic_failure_atomic_round_and_adapter_switch(monkeypatch):
    e=engine(fixture());before=(e.states,e.history,e.records,e.update_counters,e.execution_counter)
    original=Agent.decide
    def invalid(self,payload):
        result=original(self,payload)
        if self.agent_id==2:result['action']={'name':'reject'} if result['action']['name']=='accept' else {'name':'accept'}
        return result
    monkeypatch.setattr(Agent,'decide',invalid)
    # Independent typed recomputation rejects a malformed public decision.
    def illegal(self,payload):
        result=original(self,payload);result['action']={'name':'ILLEGAL'};return result
    monkeypatch.setattr(Agent,'decide',illegal)
    with pytest.raises(TraceError):e.step()
    assert before==(e.states,e.history,e.records,e.update_counters,e.execution_counter)
    assert len(e.failures)==1
    monkeypatch.setattr(Agent,'decide',original)
    e=engine(fixture());e.adapter=Adapter('sensitivity_zero_exchange_v1','sensitivity')
    with pytest.raises(TraceError):e.step()
    assert e.execution_counter==0 and e.update_counters==(0,0)


def test_AT_BASELINE_every_B01_initial_later_policies_and_null_states():
    cfg=fixture('PD',baseline='PD_AllC');a=cfg['agents'][0];obs=observation(cfg,a,[])
    for bid,initial in [('PD_AllC','C'),('PD_AllD','D'),('PD_TFT','C'),('PD_WSLS','C')]:assert baseline_policy(bid,obs)=={'name':initial}
    for own,opp in itertools.product('CD',repeat=2):
        actions=[{'name':own},{'name':opp}];payoff=TABLES['PD'][(own,opp)][0]
        later=copy.deepcopy(obs);later['round']=2;later['history']=[{'round':1,'actions_by_seat':actions,'payoffs_by_seat':list(TABLES['PD'][(own,opp)])}]
        assert baseline_policy('PD_TFT',later)=={'name':opp}
        assert baseline_policy('PD_WSLS',later)=={'name':own if payoff in (3,5) else 'D' if own=='C' else 'C'}
        assert baseline_policy('PD_AllC',later)=={'name':'C'} and baseline_policy('PD_AllD',later)=={'name':'D'}
    for bid in ('BoS_Opera','BoS_Fight','BoS_Convention'):
        for t in (1,2,3):
            assert baseline_policy(bid,{'game':'BoS','seat':1,'history':[],'round':t})=={'name':'O' if bid=='BoS_Opera' or bid=='BoS_Convention' and t%2 else 'F'}
    for bid in ('UG_Offer2','UG_Offer4','UG_Offer5','UG_Offer8','UG_Cycle'):
        for t in (1,2,7,8):
            expected=(2,3,4,5,6,7,8)[(t-1)%7] if bid=='UG_Cycle' else int(bid[-1])
            assert baseline_policy(bid,{'game':'UG','seat':1,'history':[],'round':t,'game_parameters':{'offer_grid':list(range(2,9))}})=={'name':'offer','offer':expected}
    for bid in ('UG_AcceptAll','UG_RejectAll','UG_Threshold4','UG_Threshold5'):
        for o in range(2,9):
            expected='accept' if bid=='UG_AcceptAll' or bid.startswith('UG_Threshold') and o>=int(bid[-1]) else 'reject'
            assert baseline_policy(bid,{'game':'UG','seat':2,'history':[],'current_offer':o})=={'name':expected}
    # B02 finite frame counts are arithmetic, never an inventory execution.
    assert (5*3*5*6,5*3*3*6,5*3*3*5,5*3*3*6)==(450,270,225,270)
    assert 450+270+225+270==1215
    r=engine(cfg,'AT-BASELINE').step();assert r['pre_states_by_seat'][0] is None and r['updates_by_seat'][0]['V'] is None


def test_AT_RNG_hash_labels_do_not_create_independence():
    cfg=fixture('PD');a=engine(cfg,'AT-RNG').run();other=copy.deepcopy(cfg);other.update(condition_id='different-label',pair_id='different-seed-label')
    b=engine(other,'AT-RNG').run();assert trajectory_hash(a)==trajectory_hash(b)
    assert sampling_unit_ids([{'draw_id':'same_action_a','independent_cluster_id':'A'},{'draw_id':'same_action_b','independent_cluster_id':'B'}],'stochastic')==['A','B']
    changed=copy.deepcopy(a);changed[0]['actions_by_seat'][0]={'name':'D'};assert trajectory_hash(changed)!=trajectory_hash(a)
    assert sampling_unit_ids([{'draw_id':'U','independent_cluster_id':'shared'},{'draw_id':'1-U','independent_cluster_id':'shared'}],'stochastic')==['shared']
    assert sampling_unit_ids([{'draw_id':'seed1','independent_cluster_id':'label1'},{'draw_id':'seed2','independent_cluster_id':'label2'}],'deterministic')==[]


def test_AT_CLAIMS_exact_bindings_and_distinct_structural_layers_no_claim_promotion():
    cfg=fixture(profile='fairness_high',baseline='UG_Offer2');e=engine(cfg,'AT-CLAIMS');r=e.step();manifest=e.manifest(cfg)
    assert manifest['specification_id']==SPEC_ID and manifest['spec_sha256']==SPEC_SHA256
    d=r['decisions_by_seat'][1];assert d['aE']=={'name':'reject'} and d['action']=={'name':'accept'} and d['choice']['category']=='tie_reject'
    assert d['choice']['candidates']['reject']['q']==r['updates_by_seat'][1]['raw_q'] or d['choice']['candidates']['accept']['q']==r['updates_by_seat'][1]['raw_q']
    for selection in REGISTRY['enums']['selected_adapter_convention']:
        assert selection in condition_identity(prepare_config({**cfg,'selected_adapter_convention':selection,'run_purpose':'sensitivity','horizon':200}),'fixture')
    # Fixed conceptual readout: ties stay in denominator and stateless baselines
    # have no state readout. This is no frequency or journal-effect analysis.
    concordant,tied,discordant=1,1,1
    assert concordant/(concordant+tied+discordant)==1/3
    assert r['post_states_by_seat'][0] is None


def test_AT_PACKAGE_exact_C6_entries_CRC_hashes_internal_external_manifest():
    manifest=parse_json((C6_CONTRACT/'MANIFEST_C6_v1.1.json').read_text())
    zip_path=C6_CONTRACT/'EMBORA_R0PKG_2026-10-04_C6_v1.1.zip'
    assert hashlib.sha256(zip_path.read_bytes()).hexdigest()=='7915c1c0aa69548091a1eb64dee99cd64c460f239e2f8a86d2b2e10f9ee4bba0'
    assert hashlib.sha256((C6_CONTRACT/'MANIFEST_C6_v1.1.json').read_bytes()).hexdigest()=='5430b96fc23283e2d75c1f26ce6de7928972e2784c765b2dff4fa58b18a31f46'
    with zipfile.ZipFile(zip_path) as z:
        assert len(z.namelist())==len(set(z.namelist()))==63 and z.testzip() is None
        assert set(z.namelist())=={r['path'] for r in manifest['review_files']}|{'MANIFEST_C6_v1.1.json'}
        assert z.read('MANIFEST_C6_v1.1.json')==(C6_CONTRACT/'MANIFEST_C6_v1.1.json').read_bytes()
        for row in manifest['review_files']:
            assert len(z.read(row['path']))==row['bytes'] and hashlib.sha256(z.read(row['path'])).hexdigest()==row['sha256']
            assert f"{z.getinfo(row['path']).CRC:08x}"==row['crc32']


@pytest.mark.parametrize('game',['PD','BoS','UG'])
def test_AT_INVALID_serialization_artifact_and_CLI_interfaces(game,tmp_path):
    cfg=fixture(game,horizon=2);e=engine(cfg);e.run();destination=tmp_path/'artifact';e.save(destination,cfg)
    assert validate_artifact(destination)['validated_rounds']==2
    path=tmp_path/'config.json';path.write_text(canonical(cfg))
    command=[sys.executable,'-m','journal_reference_v1','validate-config',str(path)]
    result=run_cli(command);assert result.returncode==0,result.stderr
    receipt=parse_json(result.stdout);assert receipt['rounds_executed']==0 and receipt['administrative_execution_authorized'] is False
    command=[sys.executable,'-m','journal_reference_v1','run-conformance',str(path),'--authority',U1_ID,'--acceptance-id','AT-EVENT','--episode-id','cli-bounded','--output',str(tmp_path/'cli-artifact')]
    result=run_cli(command);assert result.returncode==0,result.stderr
    result=run_cli([sys.executable,'-m','journal_reference_v1','validate-artifact',str(tmp_path/'cli-artifact')]);assert result.returncode==0,result.stderr
    data=parse_json((destination/'rounds.json').read_text());data[0]['decisions_by_seat'][1]['theta']=None
    (destination/'rounds.json').write_text(canonical(data)+'\n')
    hashes=parse_json((destination/'artifact_hashes.json').read_text());hashes['rounds.json']=hashlib.sha256((destination/'rounds.json').read_bytes()).hexdigest();(destination/'artifact_hashes.json').write_text(canonical(hashes)+'\n')
    with pytest.raises(TraceError):validate_artifact(destination)


def test_AT_INVALID_validator_scope_token_lineage_and_cli_exit(tmp_path):
    cfg=fixture();text=canonical(cfg).replace('0.5','0.50000000000000000')
    receipt=validate_config_text(text);assert '0.50000000000000000' in receipt['original_numeric_tokens'].values()
    for purpose in ('confirmatory_frame','sensitivity'):
        config=prepare_config(source_config(purpose=purpose))
        with pytest.raises(ScopeError):engine(config)
    for wrong in ('AT-UNKNOWN','AT-independent',''):
        with pytest.raises(ScopeError):Engine(cfg,P2ConformanceAuthority(U1_ID,wrong,'fixture'))
    long=copy.deepcopy(cfg);long['horizon']=9
    with pytest.raises(ScopeError):engine(long)
    path=tmp_path/'invalid.json';path.write_text('{"game":"UG","game":"PD"}')
    result=run_cli([sys.executable,'-m','journal_reference_v1','validate-config',str(path)])
    assert result.returncode==2 and parse_json(result.stderr)['error_type']=='ContractError'


def test_AT_LEGACY_all_tracked_nonreference_bytes_unchanged():
    root=Path(__file__).resolve().parents[3]
    result=subprocess.run(['git','-C',str(root),'diff','--name-only','142f9a4feb6e3e8879d45cfd9e7636f1c1db99a0','--','.',':(exclude)code/journal_reference_v1'],text=True,capture_output=True)
    assert result.returncode==0 and result.stdout==''


@pytest.mark.parametrize('field,value',[('iota',float('nan')),('theta',True),('selected_branch','E'),('action',{'name':'reject'}),('extra',1)])
def test_AT_INVALID_decision_closed_typed_fields(field,value):
    cfg=fixture();e=engine(cfg);a=e.agents[1];payload={'public_observation':observation(cfg,a.descriptor,[],2),'own_pre_state':a.initial_state.to_dict()}
    d=a.decide(payload);d[field]=value
    with pytest.raises(TraceError):a.validate_decision(d,payload)


def test_AT_GAMES_all_22_outcomes_two_seats_and_role_swaps():
    tables={'PD':{('C','C'):(3,3),('C','D'):(0,5),('D','C'):(5,0),('D','D'):(1,1)},
            'BoS':{('O','O'):(3,2),('O','F'):(0,0),('F','O'):(0,0),('F','F'):(2,3)}}
    for game,table in tables.items():
        cfg=fixture(game)
        for actions,expected in table.items():
            objects=[{'name':x} for x in actions]
            assert payoffs_for(game,objects)==expected
            for descriptor in cfg['agents']:
                result=Result.build(game,1,descriptor,objects)
                assert result.validate(cfg,descriptor)['payoffs_by_seat']==list(expected)
    cfg=fixture()
    for offer in range(2,9):
        for response in ('accept','reject'):
            actions=[{'name':'offer','offer':offer},{'name':response}]
            expected=(10-offer,offer) if response=='accept' else (0,0)
            assert payoffs_for('UG',actions)==expected
            for descriptor in cfg['agents']:assert Result.build('UG',1,descriptor,actions).validate(cfg,descriptor)['payoffs_by_seat']==list(expected)
    swapped=fixture('PD');swapped['agents'][0]['seat']=2;swapped['agents'][1]['seat']=1
    validate_config(swapped);record=engine(swapped,'AT-GAMES').step()
    assert [a['agent_id'] for a in record['agent_descriptors_by_seat']]==[2,1]


def test_AT_PACKAGE_35_traceability_rows_resolve_real_test_functions():
    import csv, ast
    folder=Path(__file__).parent
    functions={n.name for p in folder.glob('test_*.py') for n in ast.walk(ast.parse(p.read_text())) if isinstance(n,ast.FunctionDef)}
    rows=list(csv.DictReader((folder.parent/'FORMULA_CODE_TEST_TRACEABILITY_C6_v1.0.csv').open()))
    assert len(rows)==35 and {r['formula_id'] for r in rows}=={f'F-{i:02d}' for i in range(1,36)}
    for row in rows:
        assert all(name.strip() in functions for name in row['test_functions'].split(';'))
