"""CE01: actual no-new-trajectory native/archive checkpoint controls.

Input is an explicitly SYNTHETIC_TEST_ONLY administrative wrapper of a SAVED
T1 control, built with a non-executing authority in the pinned native checkout.
No native PASS is mocked and no synthetic ledger receipt replaces validation.
"""
import copy
import csv
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import zipfile
import pytest
from journal_reference_v1 import batch_accounting as b, analysis_admission as a, execution as x
from journal_reference_v1.identity import digest
from journal_reference_v1.schema import canonical,parse_json,prepare_config,TraceError

R=Path(os.environ['EMBORA_CE01_ROOT']).resolve()
PYTHON=R/'reference_env/bin/python'


def make_proposal(q):
    plan=a.read(q/'plan.json');grant=a.read(q/'permission.json');r=plan['runs'][0];caps=grant['caps']
    first=dict(batch_id='CE01-initial',kind='INITIAL',block='SYNTHETIC_TEST_ONLY',plan_sha256=digest(plan),allowlist_sha256=plan['allowlist_sha256'],
        run_ids=[r['run_id']],attempt_ids=[r['attempt_id']],group_ids=[r['group_id']],members={r['group_id']:[r['run_id']]},output_id=grant['output'],parent_queue=None,
        caps=caps,reservation_intervals={k:[0,caps[k]] for k in b.DOMAINS},stop_rule='first_error_or_bound',replay_policy=copy.deepcopy(b.ZERO_REPLAY),repair_authority=None)
    # The next reservation is config-only, has no permission and is not run.
    c=parse_json(r['config_text']);c.update(condition_id='CE01-next-control',pair_id='CE01-next-pair');text=canonical(prepare_config(c));run=dict(r,run_id='CE01-next-run',base_run_id='CE01-next-run',attempt_id='CE01-next-attempt',group_id=c['condition_id'],config_text=text)
    f=io.StringIO();w=csv.DictWriter(f,fieldnames=['run_id','native_source_sha256','effective_config_sha256','condition_id','horizon','protocol_id']);w.writeheader();w.writerow(dict(run_id=run['run_id'],native_source_sha256=a.sha(text.encode()),effective_config_sha256=digest(prepare_config(c)),condition_id=c['condition_id'],horizon=str(c['horizon']),protocol_id=plan['protocol_id']));allow=f.getvalue().encode()
    nextplan=dict(plan,runs=[run],allowlist_sha256=a.sha(allow));assert x.check_plan(nextplan,(q/'protocol.bin').read_bytes(),allow,source_required=False)==dict(attempts=1,rounds=1)
    second=copy.deepcopy(first);second.update(batch_id='CE01-next',plan_sha256=digest(nextplan),allowlist_sha256=a.sha(allow),run_ids=[run['run_id']],attempt_ids=[run['attempt_id']],group_ids=[run['group_id']],members={run['group_id']:[run['run_id']]},output_id=str(q.parent/'SYNTHETIC_NEXT_NOT_CREATED'),reservation_intervals={k:[caps[k],2*caps[k]] for k in b.DOMAINS})
    proposal=dict(schema_id=b.VERSION,status='PROPOSED_NOT_AUTHORIZED',receipt_kind='NATIVE_VERIFIED',allocations=[first,second],aggregate_reservations={k:2*caps[k] for k in b.DOMAINS},nonadditive_caps={k:caps[k] for k in ('rss_bytes','episode_seconds')})
    return proposal,nextplan,allow


def source_spec(q):
    plan=a.read(q/'plan.json')
    return dict(route='queue',path=str(q),runtime_sha256=plan['source']['runtime_sha256'],inventory_sha256=digest(a.files_digest(q)),plan_sha256=digest(plan),permission_sha256=a.sha((q/'permission.json').read_bytes()))


def archive(q,path,change=None):
    with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_STORED) as z:
        for p in sorted(q.rglob('*')):
            if p.is_file():
                name=str(p.relative_to(q))
                if change=='missing' and name=='protocol.bin':continue
                z.writestr(name,p.read_bytes()+(b'x' if change=='tampered' and name=='protocol.bin' else b''))
        if change=='extra':z.writestr('unexpected.txt',b'extra')
    if change=='CRC':
        with zipfile.ZipFile(path) as z:info=z.getinfo('protocol.bin')
        raw=bytearray(path.read_bytes());start=info.header_offset+30+len(info.filename.encode())+len(info.extra);raw[start]^=1;path.write_bytes(raw)


@pytest.fixture
def queue(tmp_path):
    q=tmp_path/'SYNTHETIC_TEST_ONLY';shutil.copytree(R/'SYNTHETIC_TEST_ONLY_NATIVE_QUEUE',q)
    p,nextplan,allow=make_proposal(q);z=tmp_path/'saved_native.zip';archive(q,z)
    return q,p,source_spec(q),z,nextplan,allow


def reconcile(data):
    q,p,s,z,*_=data
    return b.reconcile_native(p,'CE01-initial',s,R/'validator',PYTHON,a.snapshot(R/'validator'),z)


def reseal(q):
    """Transport reseal of copied negative fixture; never repair old originals."""
    files={str(p.relative_to(q)):a.sha(p.read_bytes()) for p in sorted(q.rglob('*')) if p.is_file() and p.name not in ('queue.json','completion.json','seal.json')}
    queue=a.read(q/'queue.json');queue['payload_hashes']=files;queue['output_bytes']=sum((q/k).stat().st_size for k in files);(q/'queue.json').write_text(canonical(queue)+'\n')
    c=a.read(q/'completion.json');c['queue_sha256']=a.sha((q/'queue.json').read_bytes());c['output_bytes']=queue['output_bytes']+(q/'queue.json').stat().st_size;(q/'completion.json').write_text(canonical(c)+'\n')
    seal=a.read(q/'seal.json');seal['completion_sha256']=a.sha((q/'completion.json').read_bytes());seal['output_bytes']=c['output_bytes']+(q/'completion.json').stat().st_size;(q/'seal.json').write_text(canonical(seal)+'\n')


def mutate_native(q,kind):
    native=next(q.glob('*/native'));m=a.read(native/'manifest.json');rounds=a.read(native/'rounds.json')
    if kind=='UNVERIFIED':m['code_commit']='f'*40
    else:
        rounds[0]['post_states_by_seat'][1]['S']+=.1
        from journal_reference_v1.engine import trajectory_hash
        m['trajectory_hash']=trajectory_hash(rounds)
        aid=native.parent;(aid/'committed.jsonl').write_text(''.join(canonical(r)+'\n' for r in rounds))
    (native/'manifest.json').write_text(canonical(m)+'\n');(native/'rounds.json').write_text(canonical(rounds)+'\n')
    hashes={k:a.sha((native/k).read_bytes()) for k in ['manifest.json','rounds.json','failures.json']};(native/'artifact_hashes.json').write_text(canonical(hashes)+'\n');reseal(q)


def test_actual_native_checkpoint_to_next_reservation(queue,monkeypatch):
    q,p,s,z,nextplan,allow=queue
    assert b.verify_allocations(p)==p['aggregate_reservations']
    # Unchanged native permission still has all FIVE fields, including reason.
    grant=a.read(q/'permission.json');raw=(q/'permission.json').read_bytes();plan=a.read(q/'plan.json')
    assert x.check_permission(raw,s['permission_sha256'],plan,grant['output'],existing=True)==grant
    assert set(grant['replay_policy'])==set(b.ZERO_REPLAY)|{'reason'} and grant['replay_policy']['reason'] is None
    # Transparent evidence capture: delegate the one actual pinned subprocess;
    # never manufacture a receipt or substitute a synthetic PASS.
    real=b.validate_source;observed=[]
    def capture(*args,**kwargs):
        result=real(*args,**kwargs);observed.append(result);return result
    monkeypatch.setattr(b,'validate_source',capture)
    checkpoint=reconcile(queue)
    assert len(observed)==1 and checkpoint['native_validation_sha256']==digest(observed[0])
    assert observed[0]['result']['identity_verified'] is True and observed[0]['invocation']['exit_code']==0
    assert checkpoint['kind']=='NATIVE_VERIFIED' and checkpoint['status']=='COMPLETE'
    assert checkpoint['committed_rounds']==checkpoint['consumption']['rounds']==checkpoint['consumption']['attempts']==1
    assert checkpoint['archive_sha256']==checkpoint['readback_sha256']==a.sha(z.read_bytes())
    assert checkpoint['native_validation_sha256'] and checkpoint['consumption']['output_bytes']==sum(p.stat().st_size for p in q.rglob('*') if p.is_file())
    events=[b.event([],'RESERVE','CE01-initial')];events.append(b.event(events,'RECONCILE','CE01-initial',checkpoint))
    done=b.audit(p,events,b.chain(events));assert done['states']['CE01-initial']=='COMPLETE' and done['status']=='CHECKPOINTED'
    events.append(b.event(events,'RESERVE','CE01-next'));out=b.audit(p,events,b.chain(events));assert out['active']=='CE01-next' and out['states']['CE01-next']=='RESERVED' and not out['execution_authorized']
    assert not Path(p['allocations'][1]['output_id']).exists()
    (R/'receipts/actual_checkpoint_positive.json').write_text(canonical(dict(kind='SYNTHETIC_TEST_ONLY_REAL_NATIVE_VALIDATION',proposal=p,source_spec=s,archive=str(z),native_validation=observed[0],checkpoint=checkpoint,events=events,state=out,next_plan=nextplan,next_allowlist_hex=allow.hex(),Engine_step_run_calls=0))+'\n')


@pytest.mark.parametrize('case',['reason','missing_reason','nonzero','extra','bool','float'])
def test_closed_typed_initial_replay_bridge(case):
    policy=dict(b.ZERO_REPLAY,reason=None)
    if case=='reason':policy['reason']='confirmed_transient_io_process_same_snapshot'
    elif case=='missing_reason':policy.pop('reason')
    elif case=='nonzero':policy['additional_attempts']=1
    elif case=='extra':policy['extra']=0
    elif case=='bool':policy['additional_rounds']=False
    else:policy['max_groups']=0.0
    with pytest.raises(TraceError):b.verify_initial_replay_policy(b.ZERO_REPLAY,policy)


@pytest.mark.parametrize('case',['reason','nonzero','caps','output','plan','inventory_hash','permission_hash'])
def test_initial_bindings_reject(queue,case):
    q,p,s,z,*_=queue;grant=a.read(q/'permission.json')
    if case in ('reason','nonzero','caps','output'):
        if case=='reason':grant['replay_policy']['reason']='wrong-reason'
        elif case=='nonzero':grant['replay_policy']['max_groups']=1
        elif case=='caps':grant['caps']['wall_seconds']+=1
        else:grant['output']=str(q/'wrong-output')
        (q/'permission.json').write_text(canonical(grant)+'\n');s.update(source_spec(q))
    elif case=='plan':s['plan_sha256']='0'*64
    elif case=='inventory_hash':s['inventory_sha256']='0'*64
    else:s['permission_sha256']='0'*64
    with pytest.raises(TraceError):reconcile(queue)


@pytest.mark.parametrize('case',['missing','extra','tampered','CRC','absent'])
def test_actual_archive_checkpoint_negatives(queue,case):
    q,p,s,z,*_=queue
    if case=='absent':z.unlink()
    else:archive(q,z,case)
    # Actual native validation precedes this readback; no mock or PASS injection.
    with pytest.raises((TraceError,OSError,zipfile.BadZipFile)):reconcile(queue)


@pytest.mark.parametrize('case',['invalid','UNVERIFIED'])
def test_rehashed_native_invalid_or_unverified_cannot_checkpoint(queue,case):
    q,p,s,z,*_=queue;mutate_native(q,case);s.update(source_spec(q));archive(q,z)
    if case=='UNVERIFIED':
        script="""import sys,json
from pathlib import Path
from journal_reference_v1 import execution as x
from journal_reference_v1.cli import _validate_artifact
p=Path(sys.argv[1]);plan=x.read(p/'plan.json');g=x.read(p/'permission.json');r=plan['runs'][0]
out=_validate_artifact(p/r['attempt_id']/'native','report',x.authority(plan,g,x.sha((p/'permission.json').read_bytes()),r))
print(json.dumps(out));sys.exit(3 if out['status']=='CONTENT_VALID_IDENTITY_UNVERIFIED' else 2)
"""
        env=os.environ.copy();env['PYTHONPATH']=str(R/'validator/code');argv=[str(PYTHON),'-c',script,str(q)]
        report=subprocess.run(argv,cwd=R/'validator',env=env,text=True,capture_output=True)
        assert report.returncode==3 and json.loads(report.stdout)['identity']['strict_identity_satisfied'] is False
        (R/'receipts/native_unverified_report.json').write_text(canonical(dict(argv=argv,cwd=str(R/'validator'),exit=report.returncode,stdout=report.stdout,stderr=report.stderr))+'\n')
    with pytest.raises(TraceError,match='Native strict validation rejected'):reconcile(queue)


def test_original_CE01_after_bridge_reaches_real_native_validator(queue):
    q,p,s,z,*_=queue;(q/'completion.json').unlink();s.update(source_spec(q))
    with pytest.raises(TraceError,match='Native strict validation rejected') as caught:reconcile(queue)
    assert 'completion.json' in str(caught.value)


@pytest.mark.parametrize('case',['contradictory_COMPLETE','valid_FAILED'])
def test_late_overshoot_is_never_complete(queue,case):
    q,p,s,z,*_=queue;seal=a.read(q/'seal.json');seal['wall_seconds']=p['allocations'][0]['caps']['wall_seconds']+.1
    if case=='valid_FAILED':seal.update(status='FAILED',error_type='ScopeError',failed_group=p['allocations'][0]['group_ids'][0])
    (q/'seal.json').write_text(canonical(seal)+'\n');s.update(source_spec(q));archive(q,z)
    if case=='contradictory_COMPLETE':
        with pytest.raises(TraceError,match='Native strict validation rejected'):reconcile(queue)
    else:
        checkpoint=reconcile(queue);assert checkpoint['status']=='FAILED'
        events=[b.event([],'RESERVE','CE01-initial')];events.append(b.event(events,'RECONCILE','CE01-initial',checkpoint));out=b.audit(p,events,b.chain(events))
        assert out['status']=='HALTED' and out['charged_consumption']['wall_seconds']==100.1
        assert out['reserved_ever']['wall_seconds']==100
        events.append(b.event(events,'RESERVE','CE01-next'))
        with pytest.raises(TraceError):b.audit(p,events,b.chain(events))
        (R/'receipts/actual_native_overshoot_failed.json').write_text(canonical(dict(kind='SYNTHETIC_TEST_ONLY',checkpoint=checkpoint,state=out))+'\n')
