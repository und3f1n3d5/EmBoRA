"""Finalization, semantic failed-parent and CPU checks; only short test_only."""
import json
import os
import subprocess
import sys
import time
from pathlib import Path
import pytest
from journal_reference_v1 import execution as x, engine as em
from journal_reference_v1.schema import ContractError, canonical
from test_execution_p3 import inputs, regrant, reseal, recovery_inputs


@pytest.mark.parametrize('stage',['native_episode','queue_fsync','terminal_commit','queue_schema','native_rss'])
def test_P3_late_boundaries_stop_and_never_pass(tmp_path,monkeypatch,stage):
    args=inputs(tmp_path,n=2 if stage=='native_episode' else 1,horizon=1)
    if stage=='native_episode':args=regrant(args,lambda g:g['caps'].update(episode_seconds=2))
    elif stage!='native_rss':args=regrant(args,lambda g:g['caps'].update(wall_seconds=2))
    injected=False;calls=0;step=em.Engine.step
    def traced(self):
        nonlocal calls
        calls+=1;return step(self)
    monkeypatch.setattr(em.Engine,'step',traced)
    if stage in ('native_episode','native_rss'):
        save=em.Engine.save
        def delayed_save(self,*a,**kw):
            nonlocal injected
            result=save(self,*a,**kw);injected=True
            if stage=='native_rss':monkeypatch.setattr(x,'peak_rss',lambda:9*1024**3)
            else:time.sleep(2.2)
            return result
        monkeypatch.setattr(em.Engine,'save',delayed_save)
    elif stage=='queue_fsync':
        sync=x.sync_directory
        def delayed_sync(path):
            nonlocal injected
            sync(path)
            if not injected and Path(path)==args[-1] and (Path(path)/'queue.json').exists():
                injected=True;time.sleep(2.2)
        monkeypatch.setattr(x,'sync_directory',delayed_sync)
    elif stage=='terminal_commit':
        write=x.write
        def delayed_write(path,data):
            nonlocal injected
            write(path,data)
            if Path(path).name=='completion.json':injected=True;time.sleep(2.2)
        monkeypatch.setattr(x,'write',delayed_write)
    else:
        validate=x.validate_inventory
        def delayed_validate(name,data,*a):
            nonlocal injected
            validate(name,data,*a)
            if not injected and data.get('schema_id')==x.QUEUE:
                injected=True;time.sleep(2.2)
        monkeypatch.setattr(x,'validate_inventory',delayed_validate)
    result=x.run_queue(*args)
    assert injected and calls==1 and result['status']=='FAILED'
    assert (args[-1]/'completion.json').exists()
    if stage=='native_episode':assert len(result['not_started'])==1
    if stage=='terminal_commit':assert (args[-1]/'failure.json').exists()
    with pytest.raises(ContractError):x.validate_queue(args[-1],args[-2])


@pytest.mark.parametrize('case,reason',[('replay','aggregates'),('reservation','Planned reservation'),('cause','cause/group')])
def test_P3_original_semantic_oracles_python_and_report(tmp_path,case,reason):
    args=inputs(tmp_path,horizon=1);x.run_queue(*args);path=args[-1];q=x.read(path/'queue.json')
    if case=='replay':q.update(replay_attempts=999,replay_rounds=999999,replayed_groups=['invented'])
    elif case=='reservation':(path/'reservation.json').write_text(canonical(dict(schema_id=x.QUEUE,reserved_attempts=999,reserved_rounds=999999))+'\n')
    else:q.update(error_type='OSError',failed_group=args[0]['runs'][0]['group_id'])
    (path/'queue.json').write_text(canonical(q)+'\n');reseal(path)
    for mode in ('required','report'):
        with pytest.raises(ContractError,match=reason):x.validate_queue(path,args[-2],mode)
        cmd=[sys.executable,'-m','journal_reference_v1.execution','validate',str(path),'--permission-sha256',args[-2],'--identity-requirement',mode]
        result=subprocess.run(cmd,text=True,capture_output=True,env=dict(os.environ,PYTHONPATH=str(Path(__file__).resolve().parents[2]),PYTHONDONTWRITEBYTECODE='1'))
        assert result.returncode==2 and reason in result.stderr


@pytest.mark.parametrize('case',['reservation','charged','unstarted','cause','crash'])
def test_P3_failed_or_crash_parent_checked_before_recovery(tmp_path,monkeypatch,case):
    args=inputs(tmp_path,n=2,horizon=3)
    def fail(self):raise OSError('named structural transient failure')
    with monkeypatch.context() as patch:
        patch.setattr(em.Engine,'step',fail);result=x.run_queue(*args)
    assert result['status']=='FAILED' and result['reserved_rounds']==3
    path=args[-1];q=x.read(path/'queue.json')
    if case=='reservation':(path/'reservation.json').write_text(canonical(dict(schema_id=x.QUEUE,reserved_attempts=999,reserved_rounds=999999))+'\n')
    elif case=='charged':q['reserved_rounds']=0
    elif case=='unstarted':q['not_started']=[]
    elif case=='cause':q['error_type']='InterruptedError'
    (path/'queue.json').write_text(canonical(q)+'\n');reseal(path)
    recovery=recovery_inputs(args,tmp_path/'repair')
    if case=='crash':(path/'completion.json').unlink()
    def forbidden(*a,**k):raise AssertionError('Unverified parent reached Engine')
    monkeypatch.setattr(em.Engine,'__init__',forbidden)
    with pytest.raises((ContractError,OSError)):x.run_queue(*recovery)
    assert not recovery[-1].exists()


def test_P3_CPU_is_measured_process_child_not_wall(tmp_path):
    args=inputs(tmp_path,horizon=1);before=x.cpu_snapshot();result=x.run_queue(*args);after=x.cpu_snapshot()
    assert result['status']=='COMPLETE'
    cpu=result['cpu_seconds'];assert set(cpu)==set(before)
    assert all(0<=cpu[k]<=after[k]-before[k]+1e-8 for k in cpu)
    assert sum(cpu.values())>0
    completion=x.read(args[-1]/'completion.json')
    assert completion['cpu_seconds']==cpu
    assert completion['wall_seconds']<=x.read(args[-1]/'seal.json')['wall_seconds']==result['wall_seconds']
    assert x.validate_queue(args[-1],args[-2])['status']=='PASS'


def test_P3_failed_engine_prefix_is_replayed_without_games(tmp_path,monkeypatch):
    from journal_reference_v1.accounting import verify_accounting
    args=inputs(tmp_path,horizon=3);execute=em.execute;calls=0
    def interrupted(*a,**k):
        nonlocal calls
        calls+=1
        if calls==2:raise OSError('named interruption before second game result')
        return execute(*a,**k)
    with monkeypatch.context() as patch:
        patch.setattr(em,'execute',interrupted);result=x.run_queue(*args)
    assert result['status']=='FAILED' and result['committed_rounds']==1 and result['reserved_rounds']==3
    def forbidden(*a,**k):raise AssertionError('Partial parent replay executed a game')
    monkeypatch.setattr(em,'execute',forbidden);monkeypatch.setattr(em.Engine,'step',forbidden)
    checked=verify_accounting(args[-1],args[-2])
    assert checked['status']=='FAILED' and checked['native_receipts'][0]['status']=='PARTIAL_CONTENT_VERIFIED'
