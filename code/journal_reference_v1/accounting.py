"""P3 v1.2 semantic verifier shared by complete validation and recovery.

Transport hashes alone never establish counts, error consistency or lineage.
Missing crash/finalization evidence is incomplete, not a repair authority.
"""
from . import execution as x
from .schema import TraceError, canonical, prepare_config, parse_json, keys


def require(condition, message):
    if not condition: raise TraceError(message)


def monotone(after, before):
    return all(after[k]+1e-9 >= before[k] for k in before)


def over(metrics, grant, *, episode=False):
    caps = grant['caps']
    return (metrics['wall_seconds'] >= caps['episode_seconds'] if episode else metrics['wall_seconds'] >= caps['wall_seconds']) or metrics['peak_rss_bytes'] >= caps['rss_bytes'] or metrics['output_bytes'] >= caps['output_bytes']


def verify_accounting(output, trusted_sha256=None, *, expected_completion=None, identity_requirement='required', seen=()):
    """Verify complete/failed ledgers and committed prefixes; execute zero games."""
    from .cli import _validate_artifact
    output = x.Path(output).resolve()
    require(str(output) not in seen,'Cyclic parent lineage')
    seen = (*seen,str(output))
    q = x.read(output/'queue.json'); plan = x.read(output/'plan.json')
    require(q['schema_id'] == x.QUEUE,'Old administrative accounting requires its recorded validator; no successor completion binding')
    # No final record => incomplete/crash reservation, never automatic recovery.
    c = x.read(output/'completion.json')
    if expected_completion is not None:
        require(x.sha((output/'completion.json').read_bytes()) == expected_completion,'Parent completion digest mismatch')
    x.validate_inventory('EXECUTION_SCHEMA_P3_v1.1.json',c)
    x.verify_payloads(output,q)
    require(c['queue_sha256'] == x.sha((output/'queue.json').read_bytes()),'Terminal/queue binding mismatch')
    permission = (output/'permission.json').read_bytes(); permission_sha = x.sha(permission)
    if trusted_sha256 is not None: require(permission_sha == trusted_sha256,'Trusted permission digest mismatch')
    grant = x.read(output/'permission.json')
    x.check_plan(plan,(output/'protocol.bin').read_bytes(),(output/'allowlist.csv').read_bytes(),source_required=False,_seen=seen)
    x.check_permission(permission,permission_sha,plan,grant['output'],existing=True)
    zero_cpu = {k:0.0 for k in x.cpu_snapshot()}
    prior = dict(reserved_attempts=0,reserved_rounds=0,replay_attempts=0,replay_rounds=0,replayed_groups=[],wall_seconds=0.0,output_bytes=0,cpu_seconds=zero_cpu)
    if plan['parent_queue'] is not None:
        # check_plan already fully verified this exact ancestor, including its
        # own ancestors and source/content. Read its terminal observations.
        prior = x.outcome(x.Path(plan['parent_queue']['path']))
    runs = plan['runs']; items = q['attempts']; n = len(items)
    require(0 < n <= len(runs),'Invalid actual started prefix')
    require(q['plan_sha256'] == x.digest(plan) and q['permission_sha256'] == permission_sha,'Queue plan/permission mismatch')
    reservation = x.read(output/'reservation.json')
    require(reservation == dict(schema_id=x.QUEUE,reserved_attempts=len(runs)+prior['reserved_attempts'],
        reserved_rounds=sum(prepare_config(parse_json(r['config_text']))['horizon'] for r in runs)+prior['reserved_rounds']),
        'Planned reservation differs from exact dispatch plus verified charged ancestors')
    require(q['not_started'] == [r['attempt_id'] for r in runs[n:]],'Known-unstarted tail mismatch')
    require(len(q['attempt_boundaries']) == n,'Missing durable attempt boundary')
    expected_files = {'plan.json','permission.json','protocol.bin','allowlist.csv','reservation.json','queue.json','completion.json','seal.json'}
    receipts = []; native_replays = []; charged_rounds = 0
    for index,(run,item,boundary) in enumerate(zip(runs,items,q['attempt_boundaries'])):
        directory = output/run['attempt_id']; config = prepare_config(parse_json(run['config_text'])); horizon = config['horizon']
        require(x.read(directory/'attempt.json') == item,'Attempt/queue mismatch')
        initial = dict(schema_id=x.ATTEMPT,attempt_id=run['attempt_id'],run_id=run['run_id'],plan_sha256=x.digest(plan),
            permission_sha256=permission_sha,status='FAILED',committed_rounds=0,error_type=None,message=None)
        require(x.read(directory/'reservation.json') == initial,'Attempt reservation semantic mismatch')
        require(all(item[k] == initial[k] for k in ('schema_id','attempt_id','run_id','plan_sha256','permission_sha256')),'Attempt identity mismatch')
        require(0 <= item['committed_rounds'] <= horizon,'Committed count exceeds T')
        if item['status'] == 'COMPLETE':
            require(item['committed_rounds'] == horizon and item['error_type'] is None and item['message'] is None,'COMPLETE attempt has failure/incomplete count')
        else:
            require(index == n-1 and type(item['error_type']) is str and item['error_type'] and type(item['message']) is str,'Failure must stop the started prefix')
        require(boundary['attempt_id'] == run['attempt_id'] and boundary['wall_seconds'] >= item['wall_seconds'] and
            boundary['peak_rss_bytes'] >= item['peak_rss_bytes'] and monotone(boundary['cpu_seconds'],item['cpu_seconds']),'Attempt finalization measurement mismatch')
        if item['status'] == 'COMPLETE' and over(boundary,grant,episode=True):
            require(q['tail_failure'] is not None,'Late attempt bound has no failure evidence')
        native = directory/'native'
        journal = [parse_json(line) for line in (directory/'committed.jsonl').read_text().splitlines()] if (directory/'committed.jsonl').exists() else []
        require(len(journal) == item['committed_rounds'],'Journal/committed count mismatch')
        for p in directory.rglob('*'):
            if p.is_file(): expected_files.add(str(p.relative_to(output)))
        allowed = {'reservation.json','attempt.json','committed.jsonl','native/manifest.json','native/rounds.json','native/failures.json','native/artifact_hashes.json'}
        require({str(p.relative_to(directory)) for p in directory.rglob('*') if p.is_file()} <= allowed,'Unexpected attempt payload')
        if native.exists():
            m = x.read(native/'manifest.json')
            require(m['original_config_text'] == run['config_text'] and m['code_commit'] == plan['source']['commit'] and
                m['runtime_lock_sha256'] == plan['source']['runtime_sha256'],'Native plan source/config/runtime mismatch')
            require(m['source_identity']['code_tree'] == plan['source']['tree'] and m['source_identity']['tracked_inventory_sha256'] == plan['source']['inventory_sha256'],'Native tree/inventory mismatch')
            require(canonical(journal) == canonical(x.read(native/'rounds.json')),'Journal/native mismatch')
            native_replays.append((native,run,item))
        else:
            require(item['status']=='FAILED' and item['committed_rounds']==0,'Missing native content')
        charged_rounds += horizon
    tail = q['tail_failure']; last_group = runs[n-1]['group_id']
    if tail is not None:
        require(tail['error_type']=='ScopeError' and tail['failed_group']==last_group,'Unknown tail cause/group')
        b=q['attempt_boundaries'][-1]
        require(over(b,grant,episode=True) or b['total_wall_seconds']>=grant['caps']['wall_seconds'],'Tail failure has no observed bound')
    failed = items[-1]['status']=='FAILED' or tail is not None
    expected_cause = tail['error_type'] if tail is not None else items[-1]['error_type'] if failed else None
    require(q['status'] == ('FAILED' if failed else 'COMPLETE') and (failed or n==len(runs)),'Queue status/prefix contradiction')
    require(q['error_type']==expected_cause and q['failed_group']==(last_group if failed else None),'Queue cause/group contradiction')
    replay = [r for r in runs[:n] if r['replay_of'] is not None]
    expected = dict(reserved_attempts=n+prior['reserved_attempts'],reserved_rounds=charged_rounds+prior['reserved_rounds'],
        committed_rounds=sum(a['committed_rounds'] for a in items),replay_attempts=len(replay)+prior['replay_attempts'],
        replay_rounds=sum(prepare_config(parse_json(r['config_text']))['horizon'] for r in replay)+prior['replay_rounds'],
        replayed_groups=sorted(set(prior['replayed_groups'])|{r['group_id'] for r in replay}))
    require(all(q[k]==v for k,v in expected.items()),'Administrative aggregates differ from actual attempts/verified ancestors')
    rp=grant['replay_policy']; caps=grant['caps']
    require(expected['reserved_attempts']<=caps['attempts'] and expected['reserved_rounds']<=caps['rounds'],'Charged budgets exceeded')
    require(expected['replay_attempts']<=rp['additional_attempts'] and expected['replay_rounds']<=rp['additional_rounds'] and
        len(expected['replayed_groups'])<=rp['max_groups'] and (not replay or rp['max_per_group']==1),'Replay allowance exceeded')
    require(c['prior_output_bytes']==prior['output_bytes'],'Ancestor output accounting mismatch')
    payload_bytes=sum((output/name).stat().st_size for name in q['payload_hashes'])
    require(q['output_bytes']==payload_bytes+prior['output_bytes'],'Pre-queue payload byte accounting mismatch')
    require(c['output_bytes']==payload_bytes+(output/'queue.json').stat().st_size+prior['output_bytes'],'Terminal byte boundary mismatch')
    require(c['wall_seconds']>=q['wall_seconds']>=prior['wall_seconds'] and monotone(c['cpu_seconds'],q['cpu_seconds']) and monotone(q['cpu_seconds'],prior['cpu_seconds']),'Nonmonotone wall/CPU accounting')
    require(c['episode_seconds']>=q['attempt_boundaries'][-1]['wall_seconds'] and c['peak_rss_bytes']>=q['attempt_boundaries'][-1]['peak_rss_bytes'],'Terminal attempt boundary mismatch')
    terminal_bound=over(c,grant) or c['episode_seconds']>=caps['episode_seconds']
    require(c['status']==('FAILED' if failed or terminal_bound else 'COMPLETE'),'Terminal status/bound contradiction')
    require(c['error_type']==('ScopeError' if terminal_bound else expected_cause) and c['failed_group']==(last_group if failed or terminal_bound else None),'Terminal cause mismatch')
    late_path=output/'failure.json'
    if late_path.exists():
        expected_files.add('failure.json');late=x.read(late_path);x.validate_inventory('EXECUTION_SCHEMA_P3_v1.1.json',late)
        require(late['wall_seconds']>=c['wall_seconds'] and monotone(late['cpu_seconds'],c['cpu_seconds']),'Late boundary regression')
        require(late['output_bytes']==c['output_bytes']+(output/'completion.json').stat().st_size,'Late byte boundary mismatch')
        require(over(late,grant) or late['episode_seconds']>=caps['episode_seconds'],'Late marker has no observed overrun')
        require(late['error_type']=='ScopeError' and late['failed_group']==last_group,'Late cause/group mismatch')
    seal=x.read(output/'seal.json');x.validate_inventory('EXECUTION_SCHEMA_P3_v1.2.json',seal)
    observed=x.read(late_path) if late_path.exists() else c
    require(seal['completion_sha256']==x.sha((output/'completion.json').read_bytes()) and
        seal['failure_sha256']==(x.sha(late_path.read_bytes()) if late_path.exists() else None),'Final seal binding mismatch')
    require(seal['output_bytes']==observed['output_bytes']+(late_path.stat().st_size if late_path.exists() else (output/'completion.json').stat().st_size),'Final seal byte boundary mismatch')
    require(seal['wall_seconds']>=observed['wall_seconds'] and seal['episode_seconds']>=observed['episode_seconds'] and
        seal['peak_rss_bytes']>=observed['peak_rss_bytes'],'Final seal measurement regression')
    seal_bound=over(seal,grant) or seal['episode_seconds']>=caps['episode_seconds'] or seal['output_bytes']+(output/'seal.json').stat().st_size>=caps['output_bytes']
    require(seal['status']==('FAILED' if observed['status']=='FAILED' or seal_bound else 'COMPLETE'),'Final seal status contradiction')
    require(seal['error_type']==('ScopeError' if seal_bound else observed['error_type']) and
        seal['failed_group']==(last_group if seal_bound else observed['failed_group']),'Final seal cause contradiction')
    require({str(p.relative_to(output)) for p in output.rglob('*') if p.is_file()}==expected_files,'Administrative file set mismatch')
    transient=('OSError','InterruptedError');native_recoverable=False;stages=[]
    for native,run,item in native_replays:
        receipts.append(_validate_artifact(native,identity_requirement,x.authority(plan,grant,permission_sha,run),allow_partial=item['status']!='COMPLETE'))
        native_failures=x.read(native/'failures.json')
        causes=[f['error_type'] for f in native_failures]
        require(not (item['error_type'] in transient and any(cause not in transient for cause in causes)),
                'Native nontransient failure '+str(causes)+' cannot be relabelled as transient administrative I/O')
        stage=('native_execution_failure' if causes else 'complete_native_admin_finalization' if item['committed_rounds']==prepare_config(parse_json(run['config_text']))['horizon'] else 'outside_native_step')
        stages.append(dict(attempt_id=run['attempt_id'],stage=stage,native_causes=causes))
        if run['attempt_id']==runs[n-1]['attempt_id']:
            native_recoverable=all(cause in transient for cause in causes)
    result=x.outcome(output)
    result.update(identity_verified=bool(receipts) and all(r['identity']['strict_identity_satisfied'] for r in receipts),native_receipts=receipts,
                  recoverable_transient=result['status']=='FAILED' and result['error_type'] in transient and native_recoverable,
                  verified_native_stages=stages)
    return result
