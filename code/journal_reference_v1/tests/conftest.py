import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import json
import subprocess
import collections


def pytest_addoption(parser):
    parser.addoption('--conformance-receipt',default=None,help='Write actual bounded owner execution receipt')


def pytest_sessionstart(session):
    import journal_reference_v1.engine as module
    session.embora_counts={'constructors':0,'successful_rounds':0,'external_game_calls':0,'failed_step_calls':0,'started_episodes':0,'rounds_by_acceptance_id':collections.Counter()}
    counts=session.embora_counts
    construct=module.Engine.__init__;step=module.Engine.step;execute=module.execute
    def init(self,*args,**kwargs):
        construct(self,*args,**kwargs);counts['constructors']+=1
    def traced_step(self):
        if not self.history and not self.failures:counts['started_episodes']+=1
        try:result=step(self)
        except Exception:counts['failed_step_calls']+=1;raise
        counts['successful_rounds']+=1;counts['rounds_by_acceptance_id'][self.authority.acceptance_test_id]+=1
        return result
    def traced_execute(*args):counts['external_game_calls']+=1;return execute(*args)
    module.Engine.__init__=init;module.Engine.step=traced_step;module.execute=traced_execute


def pytest_sessionfinish(session,exitstatus):
    destination=session.config.getoption('--conformance-receipt')
    if not destination:return
    from journal_reference_v1.evidence import runtime_record,runtime_hash
    root=Path(__file__).resolve().parents[3]
    def git(*args):return subprocess.check_output(['git','-C',str(root),*args],text=True).strip()
    data={'stage':'P2 owner code/conformance','status':'PASS' if exitstatus==0 else 'FAIL','exit_code':int(exitstatus),
          'argv':sys.argv,'cwd':str(Path.cwd()),'commit':git('rev-parse','HEAD'),'tree':git('rev-parse','HEAD^{tree}'),
          'branch':git('branch','--show-current'),'dirty_state':git('status','--porcelain=v1'),
          'tests_collected':session.testscollected,'runtime_lock':runtime_record(),'runtime_lock_sha256':runtime_hash(),
          'in_process_actual_counts':session.embora_counts,
          'subprocess_conformance_scope':'Three CLI run-conformance tests execute 2 rounds each in child processes; counted separately from in-process wrappers.',
          'subprocess_conformance_episodes':3,'subprocess_conformance_rounds':6,
          'pilot_full_sensitivity_trajectories':0,'independent_audit':'PENDING','code_freeze':False}
    Path(destination).write_text(json.dumps(data,indent=2)+'\n')
