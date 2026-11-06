"""Bounded integrated controls, no Engine.step/run or production permission."""
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile
import pytest
from journal_reference_v1 import analysis_admission as a, batch_accounting as b
from journal_reference_v1.identity import digest
from journal_reference_v1.schema import canonical, TraceError
from journal_reference_v1.inventory import validate_inventory

R=Path(os.environ['EMBORA_READINESS_ROOT']).resolve()
PYTHON=R/'reference_env/bin/python'

@pytest.fixture
def admitted(tmp_path):
    configs={};sources={};members={};keys=[]
    for variant in ['full',*a.metrics.SWITCHES]:
        p=tmp_path/variant;shutil.copytree(R/'fixtures'/variant,p);m=a.read(p/'manifest.json');k='registered-'+variant;keys.append(k)
        configs[k]=m['original_config_text'];sources[variant]=dict(route='conformance_test_only',path=str(p),runtime_sha256=m['runtime_lock_sha256'],inventory_sha256=digest(a.files_digest(p)),plan_sha256=None,permission_sha256=None)
        members[k]=dict(group_attempt_id='original',source_id=variant,native_relative_path='.',attempt_id='synthetic-'+variant,run_id=k,replay_of=None)
    source=a.snapshot(R/'validator')
    spec=dict(schema_id=a.ADMISSION,kind='SYNTHETIC_TEST_ONLY',decision_id='bounded-readiness-synthetic-control',protocol_id=a.PAP,protocol_sha256=a.PAP_SHA,
        analysis_source=a.snapshot(Path(a.__file__).resolve().parents[2]),validator_source=source,runtime_sha256=a.runtime_hash(),config_texts=configs,sources=sources,
        contrasts=[dict(contrast_id='contrast-'+v,full_run_id=keys[0],comparison_run_id='registered-'+v,contrast_family='single_switch',block='synthetic_sensitivity') for v in a.metrics.SWITCHES],
        groups=[dict(condition_id='AT-config',group_kind='sensitivity',members=keys,selected='original',candidates=[dict(group_attempt_id='original',replaces=None,repair_authority=None,members=members)])])
    return spec


def run(spec):
    raw=(canonical(spec)+'\n').encode()
    return a.admitted_analysis(raw,a.sha(raw),(R/'previous/inputs/PAP.md').read_bytes(),R/'validator',PYTHON)


def rehash(spec,variant):
    p=Path(spec['sources'][variant]['path']);hashes={name:a.sha((p/name).read_bytes()) for name in ['manifest.json','rounds.json','failures.json']}
    (p/'artifact_hashes.json').write_text(canonical(hashes)+'\n');spec['sources'][variant]['inventory_sha256']=digest(a.files_digest(p))


def test_integrated_native_whole_group_metrics_C6_export(admitted,tmp_path):
    out=run(admitted);validate_inventory('ANALYSIS_C6_v1.0.json',out)
    assert out['status']=='COMPLETE' and out['metrics']['extracted_runs']==6 and len(out['metrics']['pair_metrics'])==5
    assert all(c['summary']['N_expected']==c['summary']['N_valid']==1 for c in out['cells'])
    assert all(v['result']['status']=='PASS' and v['invocation']['exit_code']==0 for v in out['native_validation'].values())
    assert out['alternatives']==dict(normalized_delta_Q=None,rank_Q=None,strict_discordance=None,persistence=None,reason='PAP_OWNER_DISPOSITION_REQUIRED')
    # Literal saved neutral first-round controls; switches can change private S.
    p=next(x for x in out['metrics']['pair_metrics'] if x['comparison_run_id']=='registered-no_suppression')['metrics']
    assert p['delta_P']==0 and p['I_A']==p['D_A']==0 and p['tau_A']==2
    assert next(x for x in out['metrics']['pair_metrics'] if x['comparison_run_id']=='registered-no_fatigue')['metrics']['delta_S']==-.0116
    assert all(c['summary']['strict_only_discordance'] is None for c in out['cells'])
    assert out['experimental_rounds_executed']==0 and out['kind']=='SYNTHETIC_TEST_ONLY'
    path=tmp_path/'export.json';a.write_export(path,out,admitted)
    with pytest.raises(FileExistsError):a.write_export(path,out,admitted)
    (R/'receipts/integrated_positive_export.json').write_text(canonical(out)+'\n')


@pytest.mark.parametrize('field',['analysis_source','validator_source','runtime','PAP','raw_trust','native_hash','config','production_conformance','mixed_leaf','missing_full','missing_leaf','missing_contrast','unknown_group'])
def test_integrated_binding_selection_negatives(admitted,field):
    if field in ('analysis_source','validator_source'):admitted[field]['commit']='f'*40
    elif field=='runtime':admitted['runtime_sha256']='f'*64
    elif field=='PAP':admitted['protocol_sha256']='f'*64
    elif field=='raw_trust':
        with pytest.raises(TraceError):a.admitted_analysis(canonical(admitted).encode(),'f'*64,b'',R/'validator',PYTHON)
        return
    elif field=='native_hash':admitted['sources']['full']['inventory_sha256']='f'*64
    elif field=='config':admitted['config_texts']['registered-full']=admitted['config_texts']['registered-no_mood']
    elif field=='production_conformance':admitted['kind']='PRODUCTION'
    elif field=='mixed_leaf':admitted['groups'][0]['candidates'][0]['members']['registered-no_mood']['group_attempt_id']='other'
    elif field.startswith('missing_') and field!='missing_contrast':
        variant='full' if field=='missing_full' else 'no_mood';(Path(admitted['sources'][variant]['path'])/'rounds.json').unlink()
    elif field=='missing_contrast':admitted['contrasts'].pop()
    else:admitted['groups'][0]['condition_id']='wrong-condition'
    with pytest.raises((ValueError,OSError)):run(admitted)


@pytest.mark.parametrize('mutation',['schema','identity','unverified','authority','semantic'])
def test_rehashed_native_schema_identity_authority_semantic_still_reject(admitted,mutation):
    p=Path(admitted['sources']['full']['path']);m=a.read(p/'manifest.json');r=a.read(p/'rounds.json')
    if mutation=='schema':r[0]['post_states_by_seat'][1]['S']='not-a-real'
    elif mutation=='identity':m['code_commit']='not-a-git-commit'
    elif mutation=='unverified':m['code_commit']='f'*40
    elif mutation=='authority':m['administrative_authority']['full_runs_authorized']=True
    else:r[0]['post_states_by_seat'][1]['S']+=.1
    (p/'manifest.json').write_text(canonical(m)+'\n');(p/'rounds.json').write_text(canonical(r)+'\n');rehash(admitted,'full')
    with pytest.raises(TraceError,match='Native strict validation rejected'):run(admitted)


def repair(spec,authorized):
    g=spec['groups'][0];old=g['candidates'][0];new=copy.deepcopy(old);new.update(group_attempt_id='repair',replaces='original',repair_authority=None)
    if authorized:new['repair_authority']=dict(decision_id='separate-synthetic-repair-decision',kind='SYNTHETIC_TEST_ONLY',status='WHOLE_GROUP_REPAIR_AUTHORIZED',replaces='original',group_attempt_id='repair')
    for k,leaf in new['members'].items():
        v=leaf['source_id'];p=Path(spec['sources'][v]['path']);q=p.parent/('repair-'+v);shutil.copytree(p,q)
        m=a.read(q/'manifest.json');rr=a.read(q/'rounds.json');ep='synthetic-repair-'+v
        m['administrative_authority']['episode_id']=ep
        for r in rr:r['episode_id']=ep;r['administrative_authority']['episode_id']=ep
        (q/'manifest.json').write_text(canonical(m)+'\n');(q/'rounds.json').write_text(canonical(rr)+'\n')
        spec['sources']['repair-'+v]=dict(spec['sources'][v],path=str(q));rehash(spec,'repair-'+v)
        leaf.update(group_attempt_id='repair',source_id='repair-'+v,attempt_id=ep,run_id=k+'-repair',replay_of=old['members'][k]['attempt_id'])
    g['candidates'].append(new);g['selected']='repair'


@pytest.mark.parametrize('authorized',[False,True])
def test_whole_group_repair_requires_separate_synthetic_authority(admitted,authorized):
    repair(admitted,authorized)
    if not authorized:
        with pytest.raises(TraceError,match='Unauthorized repair'):run(admitted)
    else:
        out=run(admitted);assert out['status']=='COMPLETE' and out['whole_group_lineage'][0]['selected']=='repair'
        assert len({v['trajectory_sha256'] for v in out['generation_identities'].values()})>=1
        (R/'receipts/integrated_synthetic_repair.json').write_text(canonical(out)+'\n')


def allocation(n=2):
    totals={k:0 for k in b.DOMAINS};bs=[]
    for i in range(n):
        caps=dict(attempts=6,rounds=6,wall_seconds=100,output_bytes=1000,episode_seconds=10,rss_bytes=1000)
        x=dict(batch_id=f'b{i}',kind='INITIAL',block='synthetic',plan_sha256=str(i)*64,allowlist_sha256='0'*64,
           run_ids=[f'r{i}-{j}' for j in range(6)],attempt_ids=[f'a{i}-{j}' for j in range(6)],group_ids=[f'g{i}'],output_id=f'out{i}',parent_queue=None,
           caps=caps,stop_rule='first_error_or_bound',replay_policy=copy.deepcopy(b.ZERO_REPLAY),repair_authority=None)
        x['members']={f'g{i}':x['run_ids']};x['reservation_intervals']={k:[totals[k],totals[k]+caps[k]] for k in b.DOMAINS}
        for k in totals:totals[k]+=caps[k]
        bs.append(x)
    return dict(schema_id=b.VERSION,status='PROPOSED_NOT_AUTHORIZED',receipt_kind='SYNTHETIC_TEST_ONLY',allocations=bs,aggregate_reservations=totals,nonadditive_caps=dict(rss_bytes=1000,episode_seconds=10))


def receipt(x,status='COMPLETE'):
    return dict(kind='SYNTHETIC_TEST_ONLY',allocation_sha256=digest(x),plan_sha256=x['plan_sha256'],output_id=x['output_id'],status=status,
      consumption=dict(attempts=6,rounds=6,wall_seconds=2,output_bytes=50),committed_rounds=6,known_unstarted_attempts=0,
      peak_rss_bytes=100,episode_seconds=1,native_validation_sha256='1'*64,archive_sha256='2'*64,readback_sha256='2'*64,
      failed_group=x['group_ids'][0] if status=='FAILED' else None,recoverable_transient=status=='FAILED',group_attempt_ids={x['group_ids'][0]:x['attempt_ids']})


def append(events,kind,x,r=None):events.append(b.event(events,kind,x['batch_id'],r))
def audit(p,ev):return b.audit(p,ev,b.chain(ev))


def test_sequential_success_and_exact_reservations():
    p=allocation();e=[]
    for x in p['allocations']:append(e,'RESERVE',x);append(e,'RECONCILE',x,receipt(x))
    out=audit(p,e);assert out['status']=='CHECKPOINTED' and out['reserved_ever']==p['aggregate_reservations'] and out['charged_consumption']['rounds']==12
    (R/'receipts/synthetic_accounting_positive.json').write_text(canonical(dict(proposal=p,events=e,result=out))+'\n')


@pytest.mark.parametrize('case',['duplicate','unknown','order','unresolved','failed','late','archive','cap','global','overlap','successful_parent','tip','synthetic_laundering'])
def test_accounting_fail_closed(case):
    p=allocation();x,y=p['allocations'];e=[]
    if case=='global':p['aggregate_reservations']['wall_seconds']-=1
    elif case=='overlap':y['run_ids'][0]=x['run_ids'][0]
    elif case=='successful_parent':y['parent_queue']={'path':'successful'}
    elif case=='order':append(e,'RESERVE',y)
    elif case=='unknown':e.append(dict(sequence=0,previous=None,event='RESERVE',batch_id='unknown',receipt=None))
    else:
        append(e,'RESERVE',x)
        if case=='duplicate':append(e,'RESERVE',x)
        elif case=='unresolved':append(e,'RESERVE',y)
        else:
            r=receipt(x,'FAILED' if case=='failed' else 'COMPLETE')
            if case=='archive':r['readback_sha256']=None
            if case=='cap':r['consumption']['wall_seconds']=100.01
            if case=='synthetic_laundering':p['receipt_kind']='NATIVE_VERIFIED'
            append(e,'RECONCILE',x,r)
            if case=='late':append(e,'LATE_FAILURE',x)
            if case in ('failed','late'):append(e,'RESERVE',y)
    with pytest.raises((ValueError,KeyError)):
        b.audit(p,e,'f'*64 if case=='tip' else b.chain(e))


def test_unknown_failure_retains_full_reservation():
    p=allocation();x=p['allocations'][0];e=[];append(e,'RESERVE',x);append(e,'RECONCILE',x,receipt(x,'UNKNOWN'))
    out=audit(p,e);assert out['status']=='HALTED' and out['reserved_ever']=={k:x['caps'][k] for k in b.DOMAINS}


def test_external_append_only_checkpoint(tmp_path):
    p=allocation();x=p['allocations'][0];e=b.event([],'RESERVE',x['batch_id']);f=tmp_path/'0000.json'
    b.save_event(f,[],None,e)
    with pytest.raises(FileExistsError):b.save_event(f,[],None,e)
    with pytest.raises(TraceError):b.save_event(tmp_path/'bad',[],'f'*64,e)


def test_export_schema_rejects_C5_and_alternative_adoption(admitted):
    out=run(admitted);out['protocol_id']='EMBORA-P3-PAP-2026-10-03-C5-v1.0'
    with pytest.raises(TraceError):validate_inventory('ANALYSIS_C6_v1.0.json',out)
    out['protocol_id']=a.PAP;out['alternatives']['normalized_delta_Q']=0
    with pytest.raises(TraceError):validate_inventory('ANALYSIS_C6_v1.0.json',out)


def test_separately_allocated_whole_group_repair_and_healthy_parent_rejection():
    p=allocation();x,y=p['allocations'];e=[];append(e,'RESERVE',x);append(e,'RECONCILE',x,receipt(x,'FAILED'))
    repair=copy.deepcopy(y);repair.update(kind='REPAIR',repair_authority=dict(decision_id='separate-synthetic-allocation',status='EXPLICIT_SEPARATE_REPAIR_ALLOCATION',
      parent_batch_id=x['batch_id'],group_id=x['group_ids'][0],new_run_ids=y['run_ids'],replay_of=dict(zip(y['attempt_ids'],x['attempt_ids']))),group_ids=x['group_ids'])
    repair['members']={x['group_ids'][0]:y['run_ids']}
    # Replacing the single failed group deliberately overlaps condition identity,
    # while all run/attempt/output identities and cap intervals remain new.
    p['allocations'][1]=repair
    append(e,'RESOLVE_REPAIR',repair);append(e,'RECONCILE',repair,receipt(repair))
    out=audit(p,e);assert out['states'][repair['batch_id']]=='COMPLETE' and not out['halt']
    e[1]['receipt']['status']='COMPLETE';e[1]['receipt']['failed_group']=None;e[1]['receipt']['recoverable_transient']=False
    # Rechain to test semantic oracle, not stale hashes.
    e2=[]
    for old in e:e2.append(b.event(e2,old['event'],old['batch_id'],old['receipt']))
    with pytest.raises(TraceError):audit(p,e2)


def test_production_mixed_native_queues_reject_same_whole_group_oracle(admitted):
    g=admitted['groups'][0];candidate=g['candidates'][0]
    # Independent synthetic source roots pass literal group labels; this tests
    # the production selection invariant, without fabricated native PASS.
    with pytest.raises(TraceError,match='Whole native group must come from one queue'):
        a.native_whole_group(candidate,g,admitted['sources'])
