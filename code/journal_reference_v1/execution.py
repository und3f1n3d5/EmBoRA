"""P3 v1.0 administrative execution. No production permission ships with code.

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

VERSION = 'EMBORA-P3-EXECUTION-v1.0'
PLAN = 'EMBORA-P3-PLAN-v1.0'
PERMISSION = 'EMBORA-P3-PERMISSION-v1.0'
ATTEMPT = 'EMBORA-P3-ATTEMPT-v1.0'
QUEUE = 'EMBORA-P3-QUEUE-v1.0'
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


def check_plan(plan, protocol, allowlist, *, source_required=True):
    validate_inventory('EXECUTION_SCHEMA_P3_v1.0.json',plan,ScopeError)
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
        parent = plan['parent_queue']; keys(parent, ('path','queue_sha256'), ScopeError)
        path = Path(parent['path'])
        if sha((path/'queue.json').read_bytes()) != parent['queue_sha256']: raise ScopeError('Replay parent digest mismatch')
        previous = read(path/'plan.json'); result = read(path/'queue.json')
        verify_payloads(path,result)
        if result['plan_sha256'] != digest(previous): raise ScopeError('Parent plan binding mismatch')
        for key in ('scope','protocol_id','protocol_sha256','allowlist_sha256','source'):
            if previous[key] != plan[key]: raise ScopeError('Replay changed snapshot/protocol')
        if result['status'] != 'FAILED' or result['error_type'] not in ('OSError','InterruptedError'):
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
    validate_inventory('EXECUTION_SCHEMA_P3_v1.0.json',grant,ScopeError)
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
        prior = read(Path(plan['parent_queue']['path'])/'queue.json')
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
    return ExecutionAuthority({'schema_id':VERSION,'scope':plan['scope'],
        'protocol_id':plan['protocol_id'],'protocol_sha256':plan['protocol_sha256'],
        'permission_id':grant['permission_id'],'permission_sha256':permission_sha,
        'plan_sha256':digest(plan),'run_id':run['run_id'],'base_run_id':run['base_run_id'],
        'attempt_id':run['attempt_id'],'group_id':run['group_id'],'replay_of':run['replay_of']},
        digest(prepare_config(parse_json(run['config_text']))), guard)


def output_size(path):
    return sum(p.stat().st_size for p in Path(path).rglob('*') if p.is_file())


def verify_payloads(path, queue):
    validate_inventory('EXECUTION_SCHEMA_P3_v1.0.json',queue)
    actual = {str(p.relative_to(path)):sha(p.read_bytes()) for p in Path(path).rglob('*') if p.is_file() and p != Path(path)/'queue.json'}
    if queue['payload_hashes'] != actual: raise TraceError('Queue payload inventory mismatch')


def run_queue(plan, protocol, allowlist, permission, trusted_sha256, output):
    """One exclusive queue, synchronous dispatch, stop on the first exception.

    A reservation survives abrupt termination. Committed rounds are fsynced to
    an append-only journal. Incomplete reservations never validate as complete.
    A bound is checked before every game and after each atomic committed round.
    Failure receipts preserve mandatory logs even when that reveals an overrun.
    """
    from .engine import Engine
    grant, counts, prior = preflight(plan, protocol, allowlist, permission, trusted_sha256, output)
    output = Path(output).resolve(); output.mkdir(parents=True, exist_ok=False)
    for name, data in [('plan.json',plan),
                       ('reservation.json',{'schema_id':QUEUE,'reserved_attempts':counts['attempts']+prior['reserved_attempts'],
                                           'reserved_rounds':counts['rounds']+prior['reserved_rounds']})]: write(output/name,data)
    with (output/'protocol.bin').open('xb') as f: f.write(protocol)
    with (output/'allowlist.csv').open('xb') as f: f.write(allowlist)
    with (output/'permission.json').open('xb') as f: f.write(permission)
    start = time.monotonic(); episode_start = start; active = True; attempts = []; failure = None; failed_group = None
    source = exact_source()
    def guard():
        if not active: raise ScopeError('Execution lease is closed')
        status = git(ROOT,'status','--porcelain=v2','--branch').decode().splitlines()
        if '# branch.oid '+source['commit'] not in status or any(not line.startswith('# ') for line in status):
            raise IdentityError('Source/HEAD drift during execution')
        elapsed = time.monotonic()-start
        if elapsed+prior['wall_seconds'] >= grant['caps']['wall_seconds'] or time.monotonic()-episode_start >= grant['caps']['episode_seconds']:
            raise ScopeError('Wall/episode budget exhausted')
        if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024 >= grant['caps']['rss_bytes']:
            raise ScopeError('RSS budget exhausted')
        if output_size(output)+prior['output_bytes'] >= grant['caps']['output_bytes']:
            raise ScopeError('Output budget exhausted')
    def timeout(signum, frame): raise ScopeError('Wall/episode deadline reached')
    def interrupted(signum, frame): raise InterruptedError('Process interrupted; queue stopped')
    old_as = resource.getrlimit(resource.RLIMIT_AS)
    old_handler = signal.getsignal(signal.SIGALRM)
    old_interrupts = {s:signal.getsignal(s) for s in (signal.SIGINT,signal.SIGTERM)}
    old_timer = signal.getitimer(signal.ITIMER_REAL)
    if old_timer != (0.0,0.0): raise ScopeError('Runner needs exclusive process timer')
    try:
        # Address-space ceiling is deliberately stricter than resident memory;
        # it prevents unbounded allocation between synchronous RSS checks.
        limit = grant['caps']['rss_bytes']
        if old_as[0] != resource.RLIM_INFINITY: limit = min(limit,old_as[0])
        resource.setrlimit(resource.RLIMIT_AS,(limit,old_as[1]))
        signal.signal(signal.SIGALRM, timeout)
        for s in old_interrupts: signal.signal(s,interrupted)
        for run in plan['runs']:
            episode_start = time.monotonic(); directory = output/run['attempt_id']; directory.mkdir(exist_ok=False)
            item = {'schema_id':ATTEMPT,'attempt_id':run['attempt_id'],'run_id':run['run_id'],
                    'plan_sha256':digest(plan),'permission_sha256':trusted_sha256,
                    'status':'FAILED','committed_rounds':0,'error_type':None,'message':None}
            write(directory/'reservation.json',item)
            engine = None
            try:
                guard()
                if exact_source() != source: raise IdentityError('Code/runtime drift before episode')
                remaining = min(grant['caps']['episode_seconds'], grant['caps']['wall_seconds']-prior['wall_seconds']-(time.monotonic()-start))
                signal.setitimer(signal.ITIMER_REAL, remaining)
                engine = Engine(prepare_config(parse_json(run['config_text'])),authority(plan,grant,trusted_sha256,run,_Lease(guard)))
                with (directory/'committed.jsonl').open('x',encoding='utf-8') as journal:
                    while len(engine.history) < engine.config['horizon']:
                        record = engine.step()
                        journal.write(canonical(record)+'\n'); journal.flush(); os.fsync(journal.fileno())
                        guard()
                item['status'] = 'COMPLETE'
            except BaseException as error:
                failure = error; failed_group = run['group_id']
                item.update(error_type=type(error).__name__,message=str(error))
            finally:
                signal.setitimer(signal.ITIMER_REAL,0)
                if engine is not None:
                    item['committed_rounds'] = len(engine.records)
                    engine.save(directory/'native',parse_json(run['config_text']),run['config_text'])
                item['wall_seconds'] = time.monotonic()-episode_start
                item['peak_rss_bytes'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
                validate_inventory('EXECUTION_SCHEMA_P3_v1.0.json',item)
                write(directory/'attempt.json',item); attempts.append(item)
            if failure is not None: break
    finally:
        active = False; signal.setitimer(signal.ITIMER_REAL,*old_timer); signal.signal(signal.SIGALRM,old_handler)
        for s,handler in old_interrupts.items(): signal.signal(s,handler)
        resource.setrlimit(resource.RLIMIT_AS,old_as)
        result = {'schema_id':QUEUE,'status':'FAILED' if failure is not None or len(attempts)!=len(plan['runs']) else 'COMPLETE',
                  'plan_sha256':digest(plan),'permission_sha256':trusted_sha256,'attempts':attempts,
                  'not_started':[r['attempt_id'] for r in plan['runs'][len(attempts):]],
                  'reserved_attempts':len(attempts)+prior['reserved_attempts'],
                  'reserved_rounds':sum(prepare_config(parse_json(r['config_text']))['horizon'] for r in plan['runs'][:len(attempts)])+prior['reserved_rounds'],
                  'committed_rounds':sum(a['committed_rounds'] for a in attempts),
                  'wall_seconds':time.monotonic()-start+prior['wall_seconds'],
                  'output_bytes':output_size(output)+prior['output_bytes'],
                  'failed_group':failed_group,'error_type':None if failure is None else type(failure).__name__}
        replays = [r for r in plan['runs'][:len(attempts)] if r['replay_of'] is not None]
        result.update(replayed_groups=sorted(set(prior['replayed_groups'])|{r['group_id'] for r in replays}),
                      replay_attempts=prior['replay_attempts']+len(replays),
                      replay_rounds=prior['replay_rounds']+sum(prepare_config(parse_json(r['config_text']))['horizon'] for r in replays))
        # Final native serialization also counts against the bound, not just the journal.
        if result['output_bytes'] >= grant['caps']['output_bytes'] or result['wall_seconds'] >= grant['caps']['wall_seconds']:
            result.update(status='FAILED',error_type='ScopeError')
        result['payload_hashes'] = {str(p.relative_to(output)):sha(p.read_bytes()) for p in sorted(output.rglob('*')) if p.is_file()}
        payload_bytes = result['output_bytes']
        for _ in range(8):
            total = payload_bytes+len((canonical(result)+'\n').encode())
            if total == result['output_bytes']: break
            result['output_bytes'] = total
        if result['output_bytes'] >= grant['caps']['output_bytes']: result.update(status='FAILED',error_type='ScopeError')
        validate_inventory('EXECUTION_SCHEMA_P3_v1.0.json',result)
        write(output/'queue.json',result)
    return result


def validate_queue(output, trusted_sha256, identity_requirement='required'):
    """No Engine.step/execute: only native deterministic content replay."""
    from .cli import _validate_artifact
    if identity_requirement not in ('required','report'): raise IdentityError('Unknown identity requirement')
    output = Path(output); plan = read(output/'plan.json'); grant = read(output/'permission.json')
    permission_bytes = (output/'permission.json').read_bytes()
    # The recorded output is a historical identity, not the verifier's path.
    grant,counts,prior = preflight(plan,(output/'protocol.bin').read_bytes(),(output/'allowlist.csv').read_bytes(),
                                  permission_bytes,trusted_sha256,grant['output'],source_required=False,existing=True)
    queue = read(output/'queue.json')
    verify_payloads(output,queue)
    expected_files = {'plan.json','permission.json','protocol.bin','allowlist.csv','reservation.json','queue.json'}
    for run in plan['runs']:
        prefix = run['attempt_id']+'/'
        expected_files.update(prefix+n for n in ('reservation.json','attempt.json','committed.jsonl','native/manifest.json','native/rounds.json','native/failures.json','native/artifact_hashes.json'))
    if {str(p.relative_to(output)) for p in output.rglob('*') if p.is_file()} != expected_files:
        raise TraceError('Administrative artifact file set mismatch')
    if queue['schema_id'] != QUEUE or queue['status'] != 'COMPLETE' or queue['not_started']:
        raise TraceError('Failed/incomplete queue is preserved but cannot receive complete PASS')
    if queue['plan_sha256'] != digest(plan) or queue['permission_sha256'] != trusted_sha256 or len(queue['attempts']) != len(plan['runs']):
        raise TraceError('Queue/attempt binding mismatch')
    if queue['output_bytes'] != output_size(output)+prior['output_bytes']: raise TraceError('Output byte accounting mismatch')
    for key in ('attempts','rounds'):
        if queue['reserved_'+key] != counts[key]+prior['reserved_'+key] or queue['reserved_'+key] > grant['caps'][key]:
            raise TraceError('Reserved attempt/round budget mismatch')
    if queue['wall_seconds'] >= grant['caps']['wall_seconds'] or queue['output_bytes'] >= grant['caps']['output_bytes']:
        raise TraceError('Over-budget queue cannot pass')
    receipts = []
    for run, item in zip(plan['runs'],queue['attempts']):
        directory = output/run['attempt_id']; actual = read(directory/'attempt.json')
        reservation = read(directory/'reservation.json')
        for key in ('schema_id','attempt_id','run_id','plan_sha256','permission_sha256'):
            if reservation[key] != actual[key]: raise TraceError('Attempt reservation mismatch')
        if actual != item or item['status'] != 'COMPLETE' or item['attempt_id'] != run['attempt_id'] or item['run_id'] != run['run_id']:
            raise TraceError('Attempt identity/status mismatch')
        if item['wall_seconds'] >= grant['caps']['episode_seconds'] or item['peak_rss_bytes'] >= grant['caps']['rss_bytes']:
            raise TraceError('Over-budget attempt cannot pass')
        config = prepare_config(parse_json(run['config_text']))
        if item['committed_rounds'] != config['horizon'] or item['plan_sha256'] != digest(plan) or item['permission_sha256'] != trusted_sha256:
            raise TraceError('Incomplete attempt accounting')
        native = directory/'native'; manifest = read(native/'manifest.json')
        if manifest['original_config_text'] != run['config_text'] or manifest['code_commit'] != plan['source']['commit'] or manifest['runtime_lock_sha256'] != plan['source']['runtime_sha256']:
            raise TraceError('Native source/config/runtime binding mismatch')
        if manifest['source_identity']['code_tree'] != plan['source']['tree'] or manifest['source_identity']['tracked_inventory_sha256'] != plan['source']['inventory_sha256']:
            raise IdentityError('Plan/native tree/inventory mismatch')
        journal = [parse_json(line) for line in (directory/'committed.jsonl').read_text().splitlines()]
        if canonical(journal) != canonical(read(native/'rounds.json')): raise TraceError('Committed journal/native content mismatch')
        receipts.append(_validate_artifact(native,identity_requirement,authority(plan,grant,trusted_sha256,run)))
    if queue['committed_rounds'] != sum(r['validated_rounds'] for r in receipts): raise TraceError('Queue counter mismatch')
    verified = all(r['status'] == 'PASS' for r in receipts)
    return {'interface_id':VERSION,'status':'PASS' if verified else 'CONTENT_VALID_IDENTITY_UNVERIFIED',
            'scope':plan['scope'],'attempts':len(receipts),'validated_rounds':queue['committed_rounds'],
            'identity_requirement':identity_requirement,'accepted_code_binding_authorized':False,
            'rounds_executed':0,'native_receipts':receipts}


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
