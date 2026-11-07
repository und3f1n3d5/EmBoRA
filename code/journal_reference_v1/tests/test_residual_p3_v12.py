"""Only changed recoverability branches; named short structural fixtures."""
import pytest
from journal_reference_v1 import execution as x,engine as em
from journal_reference_v1.accounting import verify_accounting
from test_execution_p3 import inputs,recovery_inputs


@pytest.mark.parametrize('stage',['native_execution_failure','complete_native_admin_finalization'])
def test_P3_genuine_transient_native_or_finalization_IO_recovery(tmp_path,monkeypatch,stage):
    args=inputs(tmp_path,n=2,horizon=1)
    with monkeypatch.context() as patch:
        if stage=='native_execution_failure':
            def failed_game(*a,**k):raise OSError('named transient native I/O interruption')
            patch.setattr(em,'execute',failed_game)
        else:
            save=em.Engine.save
            def late_io(self,*a,**k):
                save(self,*a,**k)
                raise OSError('named late I/O after complete durable native content')
            patch.setattr(em.Engine,'save',late_io)
        result=x.run_queue(*args)
    assert result['status']=='FAILED' and len(result['not_started'])==1
    assert result['committed_rounds']==(0 if stage=='native_execution_failure' else 1)
    checked=verify_accounting(args[-1],args[-2])
    assert checked['recoverable_transient'] and checked['verified_native_stages'][-1]['stage']==stage
    repair=recovery_inputs(args,tmp_path/'repair')
    def forbidden(*a,**k):raise AssertionError('Recovery preflight executed a game')
    monkeypatch.setattr(em.Engine,'step',forbidden);monkeypatch.setattr(em,'execute',forbidden)
    assert x.preflight(*repair)[1]==dict(attempts=2,rounds=2)
    assert not repair[-1].exists()
