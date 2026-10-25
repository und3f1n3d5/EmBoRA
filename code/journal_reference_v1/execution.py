"""P3 v1.2 administrative execution. No production permission ships with code.

The caller obtains an external permission and its trusted digest independently.
An artifact can prove consistency, never confer execution permission on itself.
Scientific payloads and the P2 conformance authority are unchanged.
"""
import argparse
import csv
import io
import os
import re
import resource
import signal
import sys
import time
from dataclasses import dataclass, field
from .schema import (Path, canonical, parse_json, prepare_config, keys, ScopeError,
                     TraceError, IdentityError, ContractError, hashlib)
from .evidence import runtime_hash
from .identity import ROOT, capture_source_identity, git, digest
from .inventory import validate_inventory

VERSION = 'EMBORA-P3-EXECUTION-v1.2'
AUTHORITY_VERSION = 'EMBORA-P3-EXECUTION-v1.0'
PLAN = 'EMBORA-P3-PLAN-v1.2'
PERMISSION = 'EMBORA-P3-PERMISSION-v1.1'
ATTEMPT = 'EMBORA-P3-ATTEMPT-v1.1'
QUEUE = 'EMBORA-P3-QUEUE-v1.1'
SCOPES = ('test_only', 'pilot', 'full')
CAPS = ('attempts', 'rounds', 'wall_seconds', 'episode_seconds', 'rss_bytes', 'output_bytes')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    return parse_json(Path(path).read_text(encoding='utf-8'))


def write(path, data):
    """Exclusive, durable files; no overwrite, including on failure."""
    with Path(path).open('x', encoding='utf-8') as f:
        f.write(canonical(data)+'\n'); f.flush(); os.fsync(f.fileno())


def identifier(value):
    if type(value) is not str or re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,119}', value) is None:
        raise ScopeError('Invalid administrative ID')
    return value


def exact_source():
    identity = capture_source_identity()
    if git(ROOT, 'status', '--porcelain=v1').strip() or not identity['tracked_content_matches_commit']:
        raise IdentityError('Execution requires an exact clean source checkout')
    return {'commit': git(ROOT, 'rev-parse', 'HEAD').decode().strip(),
            'tree': identity['code_tree'], 'inventory_sha256': identity['tracked_inventory_sha256'],
            'runtime_sha256': runtime_hash()}


def check_plan(plan, protocol, allowlist, *, source_required=True, _seen=()):
    validate_inventory('EXECUTION_SCHEMA_P3_v1.2.json',plan,ScopeError)
    keys(plan, ('schema_id','scope','protocol_id','protocol_sha256','allowlist_sha256',
                'source','runs','parent_queue'), ScopeError)
    if plan['schema_id'] != PLAN or plan['scope'] not in SCOPES:
        raise ScopeError('Unknown execution plan/scope')
    identifier(plan['protocol_id'])
    if sha(protocol) != plan['protocol_sha256'] or sha(allowlist) != plan['allowlist_sha256']:
        raise ScopeError('Protocol/allowlist bytes mismatch')
    if source_required and plan['source'] != exact_source(): raise IdentityError('Exact code/runtime mismatch')
    rows = list(csv.DictReader(io.StringIO(allowlist.decode('utf-8'))))
    allowed = {row['run_id']: row for row in rows}
    if len(allowed) != len(rows) or not rows: raise ScopeError('Duplicate/empty allowlist')
    runs = plan['runs']
    if type(runs) is not list or not runs: raise ScopeError('Explicit nonempty run plan required')
    seen = set(); bases = set(); groups = []
    for run in runs:
        keys(run, ('run_id','base_run_id','attempt_id','group_id','config_text','replay_of'), ScopeError)
        for key in ('run_id','base_run_id','attempt_id','group_id'): identifier(run[key])
        for key in ('run_id','attempt_id'):
            token = (key,run[key])
            if token in seen: raise ScopeError('Duplicate run/attempt ID')
            seen.add(token)
        base = run['base_run_id']
        if base not in allowed or base in bases: raise ScopeError('Unknown/duplicate allowlisted run')
        bases.add(base); row = allowed[base]
        text = run['config_text']
        if type(text) is not str: raise ScopeError('Original native config text required')
        config = prepare_config(parse_json(text))
        if (sha(text.encode()) != row['native_source_sha256'] or digest(config) != row['effective_config_sha256']
                or config['condition_id'] != run['group_id'] or config['condition_id'] != row['condition_id']
                or str(config['horizon']) != row['horizon'] or row['protocol_id'] != plan['protocol_id']):
            raise ScopeError('Native config/run allowlist mismatch')
        if plan['scope'] == 'test_only' and (config['run_purpose'] != 'structural_fixture' or config['horizon'] > 8):
            raise ScopeError('Test-only authority cannot execute PAP episodes')
        if plan['scope'] != 'test_only' and config['run_purpose'] == 'structural_fixture':
            raise ScopeError('Structural fixtures require separate test-only scope')
        if not groups or groups[-1] != run['group_id']:
            if run['group_id'] in groups: raise ScopeError('A paired group must be contiguous')
            groups.append(run['group_id'])
        if plan['parent_queue'] is None:
            if run['run_id'] != base or run['replay_of'] is not None: raise ScopeError('Unexpected replay lineage')
        elif run['replay_of'] is not None and (run['run_id'] == base or type(run['replay_of']) is not str):
            raise ScopeError('Replay requires new run ID and explicit parent attempt')
    if plan['parent_queue'] is None:
        if [r['base_run_id'] for r in runs] != [r['run_id'] for r in rows]:
            raise ScopeError('Original dispatch must match the complete ordered allowlist')
    else:
        parent = plan['parent_queue']; keys(parent, ('path','queue_sha256','completion_sha256','failure_sha256','seal_sha256'), ScopeError)
        path = Path(parent['path'])
        if sha((path/'queue.json').read_bytes()) != parent['queue_sha256']: raise ScopeError('Replay parent digest mismatch')
        marker = path/'failure.json'
        if (sha(marker.read_bytes()) if marker.exists() else None) != parent['failure_sha256']:
            raise ScopeError('Replay parent late-failure binding mismatch')
        if sha((path/'seal.json').read_bytes()) != parent['seal_sha256']:
            raise ScopeError('Replay parent final seal binding mismatch')
        previous = read(path/'plan.json')
        from .accounting import verify_accounting
        result = verify_accounting(path, expected_completion=parent['completion_sha256'],seen=_seen)
        if result['plan_sha256'] != digest(previous): raise ScopeError('Parent plan binding mismatch')
        for key in ('scope','protocol_id','protocol_sha256','allowlist_sha256','source'):
            if previous[key] != plan[key]: raise ScopeError('Replay changed snapshot/protocol')
        if result['status'] != 'FAILED' or not result['recoverable_transient']:
            raise ScopeError('Only confirmed same-snapshot transient I/O/process failures permit replay')
        failed_group = result['failed_group']
        if failed_group in result['replayed_groups']: raise ScopeError('Second replay of a group is forbidden')
        selected = [r for r in previous['runs'] if r['group_id'] == failed_group]
        pending = [r for r in previous['runs'] if r['group_id'] != failed_group and r['attempt_id'] in result['not_started']]
        if len(selected) > 16 or len(runs) != len(selected)+len(pending): raise ScopeError('Whole failed group and pending tail required')
        for run, old in zip(runs, selected+pending):
            if (run['base_run_id'],run['config_text']) != (old['base_run_id'],old['config_text']):
                raise ScopeError('Incomplete or altered paired recovery')
            if old in selected:
                if run['replay_of'] != old['attempt_id'] or run['attempt_id'] == old['attempt_id'] or run['run_id'] == old['run_id']:
                    raise ScopeError('Replay requires new IDs and exact original lineage')
            elif run != old: raise ScopeError('Unstarted tail must retain its original identity/config')
    return {'attempts':len(runs), 'rounds':sum(prepare_config(parse_json(r['config_text']))['horizon'] for r in runs)}


def check_permission(permission, trusted_sha256, plan, output, *, existing=False):
    if permission is None or trusted_sha256 is None: raise ScopeError('External explicit permission and independently trusted SHA256 required')
    if sha(permission) != trusted_sha256: raise ScopeError('Permission digest mismatch')
    grant = parse_json(permission.decode('utf-8'))
    validate_inventory('EXECUTION_SCHEMA_P3_v1.2.json',grant,ScopeError)
    keys(grant, ('schema_id','permission_id','decision_id','issuer','status','scope','plan_sha256',
                 'output','caps','replay_policy','stop_rule'), ScopeError)
    if (grant['schema_id'] != PERMISSION or grant['status'] != 'AUTHORIZED' or
            grant['scope'] != plan['scope'] or grant['plan_sha256'] != digest(plan)):
        raise ScopeError('Permission/scope/plan mismatch')
    for key in ('permission_id','decision_id','issuer'): identifier(grant[key])
    if Path(grant['output']).resolve() != Path(output).resolve(): raise ScopeError('Output identity mismatch')
    if not existing and Path(output).exists(): raise ScopeError('Write-once output already exists')
    if grant['stop_rule'] != 'first_error_or_bound': raise ScopeError('Required stop rule missing')
    keys(grant['caps'], CAPS, ScopeError)
    for value in grant['caps'].values():
        if type(value) is not int or value <= 0: raise ScopeError('All caps must be explicit positive integers')
    keys(grant['replay_policy'], ('additional_attempts','additional_rounds','max_groups','max_per_group','reason'), ScopeError)
    rp = grant['replay_policy']
    for key,maximum in [('additional_attempts',16),('additional_rounds',3200),('max_groups',2),('max_per_group',1)]:
        if type(rp[key]) is not int or not 0 <= rp[key] <= maximum: raise ScopeError('Invalid explicit replay allowance')
    if plan['parent_queue'] is None:
        if rp['reason'] is not None: raise ScopeError('Original queue cannot claim a repair reason')
    elif rp['reason'] != 'confirmed_transient_io_process_same_snapshot':
        raise ScopeError('External confirmation of transient repair cause required')
    return grant


def preflight(plan, protocol, allowlist, permission=None, trusted_sha256=None, output=None, *, source_required=True, existing=False):
    counts = check_plan(plan, protocol, allowlist,source_required=source_required)
    grant = check_permission(permission, trusted_sha256, plan, output,existing=existing)
    prior = {'reserved_attempts':0,'reserved_rounds':0,'wall_seconds':0,'output_bytes':0,'replayed_groups':[],'replay_attempts':0,'replay_rounds':0}
    if plan['parent_queue'] is not None:
        prior = outcome(Path(plan['parent_queue']['path']))
        rp = grant['replay_policy']
        replays = [r for r in plan['runs'] if r['replay_of'] is not None]
        replay_rounds = sum(prepare_config(parse_json(r['config_text']))['horizon'] for r in replays)
        if (len(replays)+prior['replay_attempts'] > rp['additional_attempts'] or replay_rounds+prior['replay_rounds'] > rp['additional_rounds']
                or len(set(prior['replayed_groups'])|{r['group_id'] for r in replays}) > rp['max_groups'] or rp['max_per_group'] < 1):
            raise ScopeError('Replay exceeds explicitly granted allowance')
    for needed, cap in [('attempts','attempts'),('rounds','rounds')]:
        used = prior['reserved_'+needed]
        if counts[needed] + used > grant['caps'][cap]: raise ScopeError('Reserved '+needed+' budget exceeded')
    for key in ('wall_seconds','output_bytes'):
        if prior[key] >= grant['caps'][key]: raise ScopeError('Prior queue exhausted '+key)
    return grant, counts, prior


class _Lease:
    def __init__(self, guard): self.guard = guard


@dataclass(frozen=True)
class ExecutionAuthority:
    """A live runner lease or a replay-only descriptor; replay cannot execute games."""
    descriptor: dict
    config_sha256: str
    _guard: object = field(default=None, repr=False, compare=False)

    @property
    def episode_id(self): return self.descriptor['attempt_id']
    @property
    def acceptance_test_id(self): return 'P3-TEST-ONLY' if self.descriptor['scope'] == 'test_only' else 'P3-EXECUTION'

    def validate(self, config):
        if digest(config) != self.config_sha256: raise ScopeError('Authority/config binding mismatch')
        if self.descriptor['scope'] == 'test_only' and (config['run_purpose'] != 'structural_fixture' or config['horizon'] > 8):
            raise ScopeError('Test-only scope exceeded')

    def before_game(self):
        if type(self._guard) is not _Lease: raise ScopeError('Only a live preflighted runner lease can execute a game')
        self._guard.guard()

    def to_dict(self): return parse_json(canonical(self.descriptor))


def authority(plan, grant, permission_sha, run, guard=None):
    return ExecutionAuthority({'schema_id':AUTHORITY_VERSION,'scope':plan['scope'],
        'protocol_id':plan['protocol_id'],'protocol_sha256':plan['protocol_sha256'],
        'permission_id':grant['permission_id'],'permission_sha256':permission_sha,
        'plan_sha256':digest(plan),'run_id':run['run_id'],'base_run_id':run['base_run_id'],
        'attempt_id':run['attempt_id'],'group_id':run['group_id'],'replay_of':run['replay_of']},
        digest(prepare_config(parse_json(run['config_text']))), guard)


def output_size(path):
    return sum(p.stat().st_size for p in Path(path).rglob('*') if p.is_file())


def verify_payloads(path, queue):
    validate_inventory('EXECUTION_SCHEMA_P3_v1.2.json',queue)
    actual = {str(p.relative_to(path)):sha(p.read_bytes()) for p in Path(path).rglob('*') if p.is_file() and p not in {Path(path)/n for n in ('queue.json','completion.json','failure.json','seal.json')}}
    if queue['payload_hashes'] != actual: raise TraceError('Queue payload inventory mismatch')


def cpu_snapshot():
    own = resource.getrusage(resource.RUSAGE_SELF); child = resource.getrusage(resource.RUSAGE_CHILDREN)
    return dict(process_user_seconds=own.ru_utime,process_system_seconds=own.ru_stime,
                child_user_seconds=child.ru_utime,child_system_seconds=child.ru_stime)


def cpu_delta(now, before): return {k:now[k]-before[k] for k in now}
def cpu_add(a, b): return {k:a[k]+b[k] for k in a}
def peak_rss(): return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024


def sync_directory(path):
    fd = os.open(path,os.O_RDONLY|os.O_DIRECTORY)
    try: os.fsync(fd)
    finally: os.close(fd)


def sync_tree(path):
    for p in Path(path).rglob('*'):
        if p.is_file():
            with p.open('rb') as f: os.fsync(f.fileno())
    for p in sorted(Path(path).rglob('*'),reverse=True):
        if p.is_dir(): sync_directory(p)
    sync_directory(path)


def outcome(path):
    """Read finalized observations, never promote a queue payload by itself."""
    path = Path(path); q = read(path/'queue.json'); c = read(path/'completion.json')
    late = read(path/'failure.json') if (path/'failure.json').exists() else c
    seal = read(path/'seal.json')  # Absence of a veto is never positive success.
    q.update(status=seal['status'],wall_seconds=seal['wall_seconds'],cpu_seconds=late['cpu_seconds'],
             output_bytes=output_size(path)+c['prior_output_bytes'])
    if seal['status'] == 'FAILED': q.update(error_type=seal['error_type'],failed_group=seal['failed_group'])
    return q


def run_queue(plan, protocol, allowlist, permission, trusted_sha256, output):
    """Durable payload -> completion -> finite checks -> positive final seal.

    The terminal receipt excludes its own commit from its sampled clock/CPU.
    Completion alone is provisional. A final seal confirms finished checks;
    interruption before it is incomplete. Only the final seal commit and
    return/control-restoration tail are excluded, with no post-seal check.
    No self-hash/time recursion and no truncation of mandatory logs.
    """
    from .engine import Engine
    grant, counts, prior = preflight(plan,protocol,allowlist,permission,trusted_sha256,output)
    start = time.monotonic(); cpu_start = cpu_snapshot(); episode_start = start
    prior_cpu = prior.get('cpu_seconds',{k:0.0 for k in cpu_start})
    output = Path(output).resolve(); output.mkdir(parents=True,exist_ok=False)
    write(output/'plan.json',plan)
    write(output/'reservation.json',{'schema_id':QUEUE,'reserved_attempts':counts['attempts']+prior['reserved_attempts'],
                                   'reserved_rounds':counts['rounds']+prior['reserved_rounds']})
    for name,data in [('protocol.bin',protocol),('allowlist.csv',allowlist),('permission.json',permission)]:
        with (output/name).open('xb') as f: f.write(data); f.flush(); os.fsync(f.fileno())
    source = exact_source(); active = True; attempts = []; boundaries = []; failure = None; failed_group = None; tail_failure = None
    def measurements():
        return dict(wall_seconds=time.monotonic()-start+prior['wall_seconds'],
                    episode_seconds=time.monotonic()-episode_start,
                    peak_rss_bytes=peak_rss(),cpu_seconds=cpu_add(cpu_delta(cpu_snapshot(),cpu_start),prior_cpu))
    def bound_error(m, size):
        if m['wall_seconds'] >= grant['caps']['wall_seconds']: return 'total_wall'
        if m['episode_seconds'] >= grant['caps']['episode_seconds']: return 'episode_wall'
        if m['peak_rss_bytes'] >= grant['caps']['rss_bytes']: return 'rss'
        if size+prior['output_bytes'] >= grant['caps']['output_bytes']: return 'output'
        return None
    def guard():
        if not active: raise ScopeError('Execution lease is closed')
        status = git(ROOT,'status','--porcelain=v2','--branch').decode().splitlines()
        if '# branch.oid '+source['commit'] not in status or any(not line.startswith('# ') for line in status):
            raise IdentityError('Source/HEAD drift during execution')
        size = output_size(output); reason = bound_error(measurements(),size)
        if reason: raise ScopeError('Execution bound reached: '+reason)
    def timeout(signum,frame): raise ScopeError('Wall/episode deadline reached')
    def interrupted(signum,frame): raise InterruptedError('Process interrupted; queue stopped')
    old_as = resource.getrlimit(resource.RLIMIT_AS); old_handler = signal.getsignal(signal.SIGALRM)
    old_interrupts = {s:signal.getsignal(s) for s in (signal.SIGINT,signal.SIGTERM)}
    old_timer = signal.getitimer(signal.ITIMER_REAL)
    if old_timer != (0.0,0.0): raise ScopeError('Runner needs exclusive process timer')
    try:
        limit = grant['caps']['rss_bytes']
        if old_as[0] != resource.RLIM_INFINITY: limit = min(limit,old_as[0])
        resource.setrlimit(resource.RLIMIT_AS,(limit,old_as[1])); signal.signal(signal.SIGALRM,timeout)
        for s in old_interrupts: signal.signal(s,interrupted)
        for run in plan['runs']:
            episode_start = time.monotonic(); episode_cpu = cpu_snapshot()
            directory = output/run['attempt_id']; directory.mkdir(exist_ok=False)
            item = dict(schema_id=ATTEMPT,attempt_id=run['attempt_id'],run_id=run['run_id'],plan_sha256=digest(plan),
                        permission_sha256=trusted_sha256,status='FAILED',committed_rounds=0,error_type=None,message=None)
            write(directory/'reservation.json',item); engine = None
            try:
                guard()
                if exact_source() != source: raise IdentityError('Code/runtime drift before episode')
                remaining = min(grant['caps']['episode_seconds'],grant['caps']['wall_seconds']-prior['wall_seconds']-(time.monotonic()-start))
                signal.setitimer(signal.ITIMER_REAL,remaining)
                engine = Engine(prepare_config(parse_json(run['config_text'])),authority(plan,grant,trusted_sha256,run,_Lease(guard)))
                with (directory/'committed.jsonl').open('x',encoding='utf-8') as journal:
                    while len(engine.history) < engine.config['horizon']:
                        record = engine.step(); journal.write(canonical(record)+'\n'); journal.flush(); os.fsync(journal.fileno()); guard()
                item['status'] = 'COMPLETE'
            except BaseException as error:
                failure = error; failed_group = run['group_id']; item.update(error_type=type(error).__name__,message=str(error))
            finally:
                # Failure retention must finish even after a deadline. All of it
                # is measured and checked before any next game/complete receipt.
                signal.setitimer(signal.ITIMER_REAL,0)
                try:
                    if engine is not None:
                        item['committed_rounds'] = len(engine.records)
                        engine.save(directory/'native',parse_json(run['config_text']),run['config_text'])
                    sync_tree(directory)
                    size = output_size(output); reason = bound_error(measurements(),size)
                    if reason:
                        failure = ScopeError('Attempt finalization bound: '+reason); failed_group = run['group_id']
                        item.update(status='FAILED',error_type='ScopeError',message=str(failure))
                except BaseException as error:
                    failure = error; failed_group = run['group_id']; item.update(status='FAILED',error_type=type(error).__name__,message=str(error))
                item.update(wall_seconds=time.monotonic()-episode_start,peak_rss_bytes=peak_rss(),
                            cpu_seconds=cpu_delta(cpu_snapshot(),episode_cpu))
                validate_inventory('EXECUTION_SCHEMA_P3_v1.2.json',item); write(directory/'attempt.json',item); sync_directory(directory)
                attempts.append(item)
                size = output_size(output); m = measurements()
                boundaries.append(dict(attempt_id=run['attempt_id'],wall_seconds=m['episode_seconds'],total_wall_seconds=m['wall_seconds'],output_bytes=size+prior['output_bytes'],peak_rss_bytes=m['peak_rss_bytes'],
                                       cpu_seconds=cpu_delta(cpu_snapshot(),episode_cpu)))
                reason = bound_error(m,size)
                if reason:
                    failure = ScopeError('Post-attempt commit bound: '+reason); failed_group = run['group_id']
                    tail_failure = dict(error_type='ScopeError',message=str(failure),failed_group=failed_group)
            if failure is not None: break
        active = False
        result = dict(schema_id=QUEUE,status='FAILED' if failure is not None else 'COMPLETE',plan_sha256=digest(plan),permission_sha256=trusted_sha256,
                      attempts=attempts,attempt_boundaries=boundaries,tail_failure=tail_failure,
                      not_started=[r['attempt_id'] for r in plan['runs'][len(attempts):]],
                      reserved_attempts=len(attempts)+prior['reserved_attempts'],
                      reserved_rounds=sum(prepare_config(parse_json(r['config_text']))['horizon'] for r in plan['runs'][:len(attempts)])+prior['reserved_rounds'],
                      committed_rounds=sum(a['committed_rounds'] for a in attempts),wall_seconds=0.0,output_bytes=0,cpu_seconds=prior_cpu,
                      failed_group=failed_group,error_type=None if failure is None else type(failure).__name__)
        replays = [r for r in plan['runs'][:len(attempts)] if r['replay_of'] is not None]
        result.update(replayed_groups=sorted(set(prior['replayed_groups'])|{r['group_id'] for r in replays}),
                      replay_attempts=prior['replay_attempts']+len(replays),replay_rounds=prior['replay_rounds']+sum(prepare_config(parse_json(r['config_text']))['horizon'] for r in replays))
        sync_tree(output)
        result['payload_hashes'] = {str(p.relative_to(output)):sha(p.read_bytes()) for p in sorted(output.rglob('*')) if p.is_file()}
        result['output_bytes'] = output_size(output)+prior['output_bytes']
        result['wall_seconds'] = measurements()['wall_seconds']; result['cpu_seconds'] = measurements()['cpu_seconds']
        validate_inventory('EXECUTION_SCHEMA_P3_v1.2.json',result); write(output/'queue.json',result); sync_directory(output)
        completion = dict(schema_id='EMBORA-P3-COMPLETION-v1.1',status='COMPLETE',error_type=None,failed_group=None,
                          boundary='after_payload_queue_fsync_hash_size_schema_before_terminal_commit',queue_sha256=sha((output/'queue.json').read_bytes()),
                          prior_output_bytes=prior['output_bytes'],output_bytes=output_size(output)+prior['output_bytes'],
                          wall_seconds=0.0,episode_seconds=0.0,peak_rss_bytes=0,cpu_seconds=prior_cpu)
        validate_inventory('EXECUTION_SCHEMA_P3_v1.2.json',completion)
        completion.update(measurements())
        reason = bound_error(completion,completion['output_bytes']-prior['output_bytes'])
        if failure is not None or reason:
            completion.update(status='FAILED',error_type='ScopeError' if reason else type(failure).__name__,
                              failed_group=failed_group or (plan['runs'][len(attempts)-1]['group_id'] if attempts else None))
        write(output/'completion.json',completion); sync_directory(output)
        # This post-commit observation cannot time/hash itself. If it reveals
        # an overrun, a durable failure marker vetoes the completion receipt.
        size = output_size(output); final = measurements(); reason = bound_error(final,size)
        if reason:
            write(output/'failure.json',dict(schema_id='EMBORA-P3-LATE-FAILURE-v1.1',status='FAILED',error_type='ScopeError',
                  failed_group=completion['failed_group'] or (plan['runs'][len(attempts)-1]['group_id'] if attempts else None),
                  boundary='after_terminal_commit_before_failure_marker_commit',output_bytes=size+prior['output_bytes'],**final))
            sync_directory(output)
        # Positive evidence that the finite post-completion checks finished.
        # No required policy check follows this last, excluded seal commit.
        marker = output/'failure.json'
        observed = read(marker) if marker.exists() else completion
        seal = dict(schema_id='EMBORA-P3-TERMINAL-SEAL-v1.2',status=observed['status'],
                    error_type=observed['error_type'],failed_group=observed['failed_group'],
                    completion_sha256=sha((output/'completion.json').read_bytes()),
                    failure_sha256=sha(marker.read_bytes()) if marker.exists() else None,
                    boundary='after_finite_terminal_checks_before_final_seal_commit',
                    output_bytes=output_size(output)+prior['output_bytes'],
                    wall_seconds=final['wall_seconds'],episode_seconds=final['episode_seconds'],peak_rss_bytes=final['peak_rss_bytes'])
        validate_inventory('EXECUTION_SCHEMA_P3_v1.2.json',seal)
        measured = measurements()
        for key in ('wall_seconds','episode_seconds','peak_rss_bytes'): seal[key] = measured[key]
        reason = bound_error(seal,seal['output_bytes']-prior['output_bytes'])
        # Include the known seal byte length in the output check, without a
        # self-hash/self-size field. Failure retention may itself overshoot.
        if reason or seal['output_bytes']+len((canonical(seal)+'\n').encode()) >= grant['caps']['output_bytes']:
            seal.update(status='FAILED',error_type='ScopeError',failed_group=plan['runs'][len(attempts)-1]['group_id'])
        write(output/'seal.json',seal); sync_directory(output)
        return outcome(output)
    finally:
        active = False; signal.setitimer(signal.ITIMER_REAL,*old_timer); signal.signal(signal.SIGALRM,old_handler)
        for s,handler in old_interrupts.items(): signal.signal(s,handler)
        resource.setrlimit(resource.RLIMIT_AS,old_as)


def validate_queue(output, trusted_sha256, identity_requirement='required'):
    from .accounting import verify_accounting
    if identity_requirement not in ('required','report'): raise IdentityError('Unknown identity requirement')
    result = verify_accounting(output,trusted_sha256,identity_requirement=identity_requirement)
    if result['status'] != 'COMPLETE': raise TraceError('Failed/incomplete queue cannot receive complete PASS')
    return dict(interface_id=VERSION,status='PASS' if result['identity_verified'] else 'CONTENT_VALID_IDENTITY_UNVERIFIED',
                scope=read(Path(output)/'plan.json')['scope'],attempts=len(result['attempts']),validated_rounds=result['committed_rounds'],
                identity_requirement=identity_requirement,accepted_code_binding_authorized=False,rounds_executed=0,
                native_receipts=result['native_receipts'])

def main(argv=None):
    parser = argparse.ArgumentParser(prog='journal_reference_v1.execution')
    sub = parser.add_subparsers(dest='command',required=True)
    for name in ('preflight','run'):
        p = sub.add_parser(name); p.add_argument('--plan',required=True); p.add_argument('--protocol',required=True)
        p.add_argument('--allowlist',required=True); p.add_argument('--permission'); p.add_argument('--permission-sha256'); p.add_argument('--output',required=True)
    p = sub.add_parser('validate'); p.add_argument('output'); p.add_argument('--permission-sha256',required=True)
    p.add_argument('--identity-requirement',choices=('required','report'),default='required')
    args = parser.parse_args(argv)
    try:
        if args.command == 'validate': result = validate_queue(args.output,args.permission_sha256,args.identity_requirement)
        else:
            plan = read(args.plan); protocol = Path(args.protocol).read_bytes(); allowlist = Path(args.allowlist).read_bytes()
            permission = None if args.permission is None else Path(args.permission).read_bytes()
            if args.command == 'preflight':
                counts = check_plan(plan,protocol,allowlist)
                if permission is None:
                    result = {'status':'NOT_AUTHORIZED','plan_status':'PASS','interface_id':VERSION,**counts,'rounds_executed':0}
                else:
                    preflight(plan,protocol,allowlist,permission,args.permission_sha256,args.output)
                    result = {'status':'PASS','interface_id':VERSION,**counts,'rounds_executed':0}
            else:
                result = run_queue(plan,protocol,allowlist,permission,args.permission_sha256,args.output)
                result = {'status':'PASS' if result['status']=='COMPLETE' else 'FAIL','queue':result}
        print(canonical(result)); return 0 if result['status']=='PASS' else 3 if result['status']=='CONTENT_VALID_IDENTITY_UNVERIFIED' else 2
    except (ContractError,OSError,KeyError,TypeError) as error:
        print(canonical({'status':'FAIL','error_type':type(error).__name__,'message':str(error),'rounds_executed':0}),file=sys.stderr); return 2


if __name__ == '__main__':
    # Use the importable class identity also for -m; Engine's exact-type gate
    # must not see a second __main__.ExecutionAuthority class.
    from .execution import main as module_main
    sys.exit(module_main())
