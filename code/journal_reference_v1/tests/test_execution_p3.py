"""Named short P3 administrative fixtures, never production/PAP episodes."""
import copy
import csv
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import pytest
from journal_reference_v1 import execution as x
from journal_reference_v1 import engine as em
from journal_reference_v1.schema import canonical, parse_json, ScopeError, ContractError
from test_integration_s12 import fixture


def inputs(tmp_path, game='PD', n=1, horizon=2):
    protocol = b'P3-NAMED-STRUCTURAL-FIXTURE-v1.0\n'
    cfg = fixture(game,horizon=horizon)
    text = canonical(cfg); group = cfg['condition_id']; runs = []; rows = []
    for j in range(n):
        run = f'p3-test-{game}-{j}'
        runs.append(dict(run_id=run,base_run_id=run,attempt_id=run+'.attempt01',group_id=group,config_text=text,replay_of=None))
        rows.append(dict(protocol_id='P3-NAMED-STRUCTURAL-FIXTURE-v1.0',run_id=run,condition_id=group,horizon=str(horizon),
                         native_source_sha256=x.sha(text.encode()),effective_config_sha256=x.digest(cfg)))
    stream = io.StringIO(); writer = csv.DictWriter(stream,fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    allowlist = stream.getvalue().encode()
    plan = dict(schema_id=x.PLAN,scope='test_only',protocol_id='P3-NAMED-STRUCTURAL-FIXTURE-v1.0',
                protocol_sha256=x.sha(protocol),allowlist_sha256=x.sha(allowlist),source=x.exact_source(),runs=runs,parent_queue=None)
    output = tmp_path/'queue'
    # Current engineering instructions authorize named <=8 structural tests.
    # This is explicitly NOT an author pilot permission or a PAP protocol.
    grant = dict(schema_id=x.PERMISSION,permission_id='P3-TEST-ONLY-01',decision_id='P3-ENGINEERING-HANDOFF-2026-10-24',
                 issuer='Engineer',status='AUTHORIZED',scope='test_only',plan_sha256=x.digest(plan),output=str(output),
                 caps=dict(attempts=n,rounds=n*horizon,wall_seconds=180,episode_seconds=60,rss_bytes=8*1024**3,output_bytes=64*1024**2),
                 replay_policy=dict(additional_attempts=0,additional_rounds=0,max_groups=0,max_per_group=0,reason=None),
                 stop_rule='first_error_or_bound')
    permission = (canonical(grant)+'\n').encode()
    return plan,protocol,allowlist,permission,x.sha(permission),output


def regrant(args, mutate):
    plan,protocol,allowlist,permission,_,output = args
    grant = parse_json(permission.decode()); mutate(grant); permission = (canonical(grant)+'\n').encode()
    return plan,protocol,allowlist,permission,x.sha(permission),output


def reseal(path):
    """Recompute transport hashes so negatives exercise semantic validation."""
    for native in path.glob('*/native'):
        hashes = {n:x.sha((native/n).read_bytes()) for n in ('manifest.json','rounds.json','failures.json')}
        (native/'artifact_hashes.json').write_text(canonical(hashes)+'\n')
    queue = x.read(path/'queue.json')
    queue['payload_hashes'] = {str(p.relative_to(path)):x.sha(p.read_bytes()) for p in path.rglob('*') if p.is_file() and p not in {path/n for n in ('queue.json','completion.json','failure.json')}}
    payload = sum(p.stat().st_size for p in path.rglob('*') if p.is_file() and p not in {path/n for n in ('queue.json','completion.json','failure.json')})
    queue['output_bytes'] = payload
    (path/'queue.json').write_text(canonical(queue)+'\n')
    completion=x.read(path/'completion.json');completion.update(queue_sha256=x.sha((path/'queue.json').read_bytes()),output_bytes=payload+(path/'queue.json').stat().st_size)
    (path/'completion.json').write_text(canonical(completion)+'\n')


@pytest.mark.parametrize('game',['PD','BoS','UG'])
def test_P3_named_fixture_and_pure_replay(tmp_path,monkeypatch,game):
    args = inputs(tmp_path,game); result = x.run_queue(*args)
    assert result['status']=='COMPLETE' and result['committed_rounds']==2
    def forbidden(*a,**k): raise AssertionError('Artifact replay executed a game/step')
    monkeypatch.setattr(em,'execute',forbidden); monkeypatch.setattr(em.Engine,'step',forbidden)
    receipt = x.validate_queue(args[-1],args[-2]); assert receipt['status']=='PASS' and receipt['rounds_executed']==0
    assert x.output_size(args[-1])==result['output_bytes']
    with pytest.raises(ScopeError):x.run_queue(*args)


def test_P3_permission_absence_before_engine(tmp_path,monkeypatch):
    args = list(inputs(tmp_path)); args[3:5] = [None,None]
    def forbidden(*a,**k): raise AssertionError('Engine constructed without permission')
    monkeypatch.setattr(em.Engine,'__init__',forbidden)
    with pytest.raises(ScopeError,match='External explicit permission'): x.run_queue(*args)
    assert not args[-1].exists()


@pytest.mark.parametrize('field',['commit','tree','inventory_sha256','runtime_sha256'])
def test_P3_exact_source_runtime_preflight(tmp_path,field):
    args = inputs(tmp_path); args[0]['source'][field] = '0'*40
    with pytest.raises(ContractError):x.preflight(*args)
    assert not args[-1].exists()


@pytest.mark.parametrize('case',['unknown_run','source','effective','protocol','allowlist','duplicate_attempt','incomplete_allowlist','replay_without_parent'])
def test_P3_allowlist_lineage_negatives(tmp_path,case):
    args = list(inputs(tmp_path,n=2)); plan = args[0]
    if case=='unknown_run':plan['runs'][0]['base_run_id']='unknown'
    elif case=='source':plan['runs'][0]['config_text']+='\n'
    elif case=='effective':plan['runs'][0]['config_text']=plan['runs'][0]['config_text'].replace('"horizon":2','"horizon":3')
    elif case=='protocol':args[1]+=b'wrong'
    elif case=='allowlist':args[2]+=b'wrong'
    elif case=='duplicate_attempt':plan['runs'][1]['attempt_id']=plan['runs'][0]['attempt_id']
    elif case=='incomplete_allowlist':plan['runs'].pop()
    else:plan['runs'][0]['replay_of']='invented'
    with pytest.raises(ContractError):x.preflight(*args)


@pytest.mark.parametrize('case',['attempts','rounds','boolean_cap','stop','output','permission_hash','scope'])
def test_P3_authority_budget_negatives(tmp_path,case):
    args = inputs(tmp_path,n=2)
    def mutate(g):
        if case in ('attempts','rounds'):g['caps'][case]=1
        elif case=='boolean_cap':g['caps']['wall_seconds']=True
        elif case=='stop':g['stop_rule']='continue'
        elif case=='output':g['output']+='-wrong'
        elif case=='scope':g['scope']='pilot'
    args = list(regrant(args,mutate))
    if case=='permission_hash':args[4]='0'*64
    with pytest.raises(ContractError):x.preflight(*args)
    assert not args[-1].exists()


def test_P3_test_scope_cannot_promote_purpose_or_horizon(tmp_path):
    args = inputs(tmp_path,horizon=8)
    for horizon,purpose in [(9,'structural_fixture'),(200,'confirmatory_frame')]:
        plan=copy.deepcopy(args[0]);config=parse_json(plan['runs'][0]['config_text']);config.update(horizon=horizon,run_purpose=purpose)
        plan['runs'][0]['config_text']=canonical(config)
        with pytest.raises(ContractError):x.check_plan(plan,args[1],args[2])
    with pytest.raises(ContractError):em.Engine(fixture('PD',horizon=9),em.P2ConformanceAuthority(em.U1_ID,'AT-INVALID','old-guard'))


@pytest.mark.parametrize('case',['journal','attempt','round_counter','manifest_commit','native_config','truncation','payload_extra','claimed_complete_over_budget'])
def test_P3_artifact_semantic_negatives(tmp_path,case):
    args=inputs(tmp_path);x.run_queue(*args);path=args[-1];directory=path/args[0]['runs'][0]['attempt_id']
    if case=='journal':(directory/'committed.jsonl').write_text('')
    elif case=='attempt':
        data=x.read(directory/'attempt.json');data['run_id']='wrong';(directory/'attempt.json').write_text(canonical(data)+'\n')
    elif case in ('manifest_commit','native_config'):
        p=directory/'native/manifest.json';data=x.read(p)
        if case=='manifest_commit':data['code_commit']='this-is-not-a-git-commit'
        else:data['original_config_text']+='\n'
        p.write_text(canonical(data)+'\n')
    elif case in ('round_counter','truncation'):
        p=directory/'native/rounds.json';data=x.read(p)
        if case=='round_counter':data[0]['event_counters']['total_game_executions']=7
        else:data.pop()
        p.write_text(canonical(data)+'\n')
        (directory/'committed.jsonl').write_text(''.join(canonical(r)+'\n' for r in data))
    elif case=='payload_extra':(directory/'extra.json').write_text('{}')
    else:
        p=path/'queue.json';data=x.read(p);data['wall_seconds']=10**9;p.write_text(canonical(data)+'\n')
    reseal(path)
    with pytest.raises(ContractError):x.validate_queue(path,args[-2])


def test_P3_partial_failure_write_once_no_continue(tmp_path,monkeypatch):
    args=inputs(tmp_path,n=2,horizon=3);step=em.Engine.step;calls=0
    def fail(self):
        nonlocal calls
        calls+=1
        if calls==2:raise OSError('named injected transient I/O fixture')
        return step(self)
    monkeypatch.setattr(em.Engine,'step',fail)
    result=x.run_queue(*args)
    assert result['status']=='FAILED' and result['committed_rounds']==1
    assert result['reserved_attempts']==1 and result['reserved_rounds']==3 and len(result['not_started'])==1
    assert result['attempts'][0]['error_type']=='OSError'
    directory=args[-1]/args[0]['runs'][0]['attempt_id']
    assert len((directory/'committed.jsonl').read_text().splitlines())==1
    with pytest.raises(ContractError):x.validate_queue(args[-1],args[-2])
    with pytest.raises(ContractError):x.run_queue(*args)


def test_P3_output_bound_stops_before_engine(tmp_path,monkeypatch):
    args=regrant(inputs(tmp_path,n=2),lambda g:g['caps'].update(output_bytes=1))
    def forbidden(*a,**k):raise AssertionError('Engine constructed after exhausted budget')
    monkeypatch.setattr(em.Engine,'__init__',forbidden)
    result=x.run_queue(*args)
    assert result['status']=='FAILED' and result['committed_rounds']==0 and len(result['not_started'])==1
    with pytest.raises(ContractError):x.validate_queue(args[-1],args[-2])


def test_P3_replay_only_descriptor_cannot_execute(tmp_path):
    args=inputs(tmp_path);plan=args[0];grant=parse_json(args[3].decode())
    a=x.authority(plan,grant,args[4],plan['runs'][0])
    engine=em.Engine(parse_json(plan['runs'][0]['config_text']),a)
    with pytest.raises(ScopeError,match='live preflighted'):engine.step()
    assert engine.execution_counter==0


def recovery_inputs(args, output):
    plan,protocol,allowlist,permission,_,parent=args
    plan=copy.deepcopy(plan)
    plan['parent_queue']=dict(path=str(parent),queue_sha256=x.sha((parent/'queue.json').read_bytes()),completion_sha256=x.sha((parent/'completion.json').read_bytes()),failure_sha256=x.sha((parent/'failure.json').read_bytes()) if (parent/'failure.json').exists() else None)
    for run in plan['runs']:
        run['replay_of']=run['attempt_id'];run['attempt_id']+='.repair01';run['run_id']+='.repair01'
    grant=parse_json(permission.decode());grant.update(output=str(output),permission_id='P3-TEST-ONLY-REPAIR',plan_sha256=x.digest(plan))
    grant['caps'].update(attempts=3,rounds=9)
    grant['replay_policy']=dict(additional_attempts=2,additional_rounds=6,max_groups=1,max_per_group=1,reason='confirmed_transient_io_process_same_snapshot')
    permission=(canonical(grant)+'\n').encode()
    return plan,protocol,allowlist,permission,x.sha(permission),output


def test_P3_whole_group_replay_new_authority_no_auto_retry(tmp_path,monkeypatch):
    args=inputs(tmp_path,n=2,horizon=3);step=em.Engine.step;calls=0
    def fail(self):
        nonlocal calls
        calls+=1
        if calls==2:raise OSError('named transient I/O failure')
        return step(self)
    with monkeypatch.context() as patch:
        patch.setattr(em.Engine,'step',fail);result=x.run_queue(*args)
    assert calls==2 and result['status']=='FAILED'
    recovery=recovery_inputs(args,tmp_path/'repair')
    assert x.preflight(*recovery)[1]==dict(attempts=2,rounds=6)
    result=x.run_queue(*recovery)
    assert result['status']=='COMPLETE' and result['reserved_attempts']==3 and result['reserved_rounds']==9
    assert result['replay_attempts']==2 and result['replay_rounds']==6
    assert x.validate_queue(recovery[-1],recovery[-2])['status']=='PASS'
    assert x.read(args[-1]/'queue.json')['status']=='FAILED'


@pytest.mark.parametrize('case',['single_variant','missing_allowance','wrong_parent','wrong_cause','stale_snapshot'])
def test_P3_repair_scope_negatives(tmp_path,monkeypatch,case):
    args=inputs(tmp_path,n=2,horizon=3)
    def fail(self):raise OSError('named transient I/O failure')
    with monkeypatch.context() as patch:
        patch.setattr(em.Engine,'step',fail);x.run_queue(*args)
    recovery=list(recovery_inputs(args,tmp_path/'repair'));plan=recovery[0]
    if case=='single_variant':plan['runs'].pop()
    elif case=='wrong_parent':plan['parent_queue']['queue_sha256']='0'*64
    elif case=='stale_snapshot':plan['source']['runtime_sha256']='0'*64
    elif case=='missing_allowance':recovery=list(regrant(recovery,lambda g:g['replay_policy'].update(additional_attempts=0)))
    else:recovery=list(regrant(recovery,lambda g:g['replay_policy'].update(reason='null_outcome')))
    with pytest.raises(ContractError):x.preflight(*recovery)


def test_P3_identity_unavailable_explicit_report_exit3(tmp_path):
    args=inputs(tmp_path);x.run_queue(*args);path=args[-1]
    plan=x.read(path/'plan.json');plan['source']['commit']='0'*40
    (path/'plan.json').write_text(canonical(plan)+'\n');ph=x.digest(plan)
    grant=x.read(path/'permission.json');grant['plan_sha256']=ph;permission=(canonical(grant)+'\n').encode();ps=x.sha(permission)
    (path/'permission.json').write_bytes(permission)
    queue=x.read(path/'queue.json');queue.update(plan_sha256=ph,permission_sha256=ps)
    run=plan['runs'][0];directory=path/run['attempt_id']
    for name in ('attempt.json','reservation.json'):
        data=x.read(directory/name);data.update(plan_sha256=ph,permission_sha256=ps)
        (directory/name).write_text(canonical(data)+'\n')
        if name=='attempt.json':queue['attempts']=[data]
    descriptor=x.authority(plan,grant,ps,run).to_dict()
    native=directory/'native';manifest=x.read(native/'manifest.json');manifest.update(code_commit='0'*40,administrative_authority=descriptor)
    (native/'manifest.json').write_text(canonical(manifest)+'\n')
    rounds=x.read(native/'rounds.json')
    for record in rounds:record['administrative_authority']=descriptor
    (native/'rounds.json').write_text(canonical(rounds)+'\n')
    (directory/'committed.jsonl').write_text(''.join(canonical(r)+'\n' for r in rounds))
    (path/'queue.json').write_text(canonical(queue)+'\n');reseal(path)
    with pytest.raises(ContractError):x.validate_queue(path,ps)
    receipt=x.validate_queue(path,ps,'report')
    assert receipt['status']=='CONTENT_VALID_IDENTITY_UNVERIFIED' and not receipt['accepted_code_binding_authorized']
    env=dict(os.environ,PYTHONPATH=str(Path(__file__).resolve().parents[2]),PYTHONDONTWRITEBYTECODE='1')
    command=[sys.executable,'-m','journal_reference_v1.execution','validate',str(path),'--permission-sha256',ps,'--identity-requirement','report']
    result=subprocess.run(command,text=True,capture_output=True,env=env)
    assert result.returncode==3 and json.loads(result.stdout)['rounds_executed']==0


def test_P3_external_permission_required_by_cli(tmp_path):
    args=inputs(tmp_path);plan,protocol,allowlist,permission,sha,output=args
    for name,data in [('plan.json',canonical(plan).encode()),('protocol.bin',protocol),('allowlist.csv',allowlist),('permission.json',permission)]:
        (tmp_path/name).write_bytes(data)
    env=dict(os.environ,PYTHONPATH=str(Path(__file__).resolve().parents[2]),PYTHONDONTWRITEBYTECODE='1')
    command=[sys.executable,'-m','journal_reference_v1.execution','preflight','--plan',str(tmp_path/'plan.json'),
             '--protocol',str(tmp_path/'protocol.bin'),'--allowlist',str(tmp_path/'allowlist.csv'),'--output',str(output)]
    result=subprocess.run(command,text=True,capture_output=True,env=env)
    assert result.returncode==2 and json.loads(result.stdout)['status']=='NOT_AUTHORIZED' and not output.exists()
    command+=['--permission',str(tmp_path/'permission.json'),'--permission-sha256',sha]
    result=subprocess.run(command,text=True,capture_output=True,env=env)
    assert result.returncode==0 and json.loads(result.stdout)['rounds_executed']==0 and not output.exists()
    command[3]='run'
    result=subprocess.run(command,text=True,capture_output=True,env=env)
    assert result.returncode==0 and json.loads(result.stdout)['queue']['committed_rounds']==2
    result=subprocess.run([sys.executable,'-m','journal_reference_v1.execution','validate',str(output),'--permission-sha256',sha],text=True,capture_output=True,env=env)
    assert result.returncode==0 and json.loads(result.stdout)['rounds_executed']==0
