"""Closed config validation, bounded conformance runner and artifact validation."""
import argparse
import sys
from .schema import *
from .engine import Engine, P2ConformanceAuthority, trajectory_hash
from .games import observation, Result, payoffs_for
from .evidence import runtime_record, runtime_hash
from .inventory import validate_inventory
from .identity import verify_source_identity


def token_lineage(text):
    """Retain original JSON numeric spellings independently of converted config."""
    class Token(str): pass
    parsed = json.loads(text, parse_float=Token, parse_int=Token)
    out = {}
    def visit(x, pointer):
        if type(x) is Token: out[pointer] = str(x)
        elif type(x) is list:
            for j, item in enumerate(x): visit(item, pointer + '/' + str(j))
        elif type(x) is dict:
            for k, item in x.items(): visit(item, pointer + '/' + k.replace('~','~0').replace('/','~1'))
    visit(parsed, '')
    return out


def validate_config_text(text):
    original = parse_json(text)
    effective = prepare_config(original)
    validate_inventory("EFFECTIVE_CONFIG_SCHEMA_C6_v1.0.json",effective,ConfigError)
    return {'status': 'PASS', 'interface_id': 'EMBORA-CONFIG-VALIDATOR-C6-v1.1',
            'specification_id': SPEC_ID, 'parameter_schema_id': SCHEMA_ID,
            'numeric_policy_id': NUMERIC_POLICY_ID, 'numeric_evidence_schema_id': EVIDENCE_ID,
            'original_config': original, 'original_text_sha256': hashlib.sha256(text.encode()).hexdigest(),
            'original_numeric_tokens': token_lineage(text), 'effective_config': effective,
            'effective_config_sha256': hashlib.sha256(canonical(effective).encode()).hexdigest(),
            'runtime_lock': runtime_record(), 'runtime_lock_sha256': runtime_hash(),
            'administrative_execution_authorized': False, 'rounds_executed': 0}


def expected_events(game):
    prefix = ['validate_config_and_pre_states', 'snapshot_both_pre_states_and_history']
    if game == 'UG':
        prefix += ['build_observation_seat_1', 'decide_seat_1', 'validate_decision_seat_1',
                   'build_observation_seat_2', 'decide_seat_2', 'validate_decision_seat_2']
    else:
        prefix += ['build_observation_seat_1', 'build_observation_seat_2',
                   'decide_seat_1', 'validate_decision_seat_1', 'decide_seat_2', 'validate_decision_seat_2']
    return prefix + ['execute_game_once', 'build_result_seat_1', 'build_result_seat_2',
                     'prepare_update_seat_1', 'prepare_update_seat_2', 'atomic_commit_both_states_history_and_log']


def validate_artifact(destination, identity_requirement='required'):
    return _validate_artifact(destination, identity_requirement)


def _validate_artifact(destination, identity_requirement='required', execution_authority=None, allow_partial=False):
    if identity_requirement not in ('required', 'report'):
        raise IdentityError('Unknown identity requirement')
    destination = Path(destination)
    names = {'manifest.json','rounds.json','failures.json','artifact_hashes.json'}
    if set(p.name for p in destination.iterdir()) != names: raise TraceError('Artifact file set mismatch')
    hashes = parse_json((destination/'artifact_hashes.json').read_text())
    keys(hashes, names-{'artifact_hashes.json'}, TraceError)
    for name, expected in hashes.items():
        if hashlib.sha256((destination/name).read_bytes()).hexdigest()!=expected: raise TraceError('Artifact byte hash mismatch')
    manifest = parse_json((destination/'manifest.json').read_text())
    rounds = parse_json((destination/'rounds.json').read_text())
    failures = parse_json((destination/'failures.json').read_text())
    if type(rounds) is not list or type(failures) is not list or (failures and not allow_partial): raise TraceError('Failed/incomplete episode cannot pass conformance artifact validation')
    try:
        original = manifest['original_config']; config = prepare_config(original)
        authority = manifest['administrative_authority']
        if execution_authority is None:
            keys(authority, ('decision_record_id','acceptance_test_id','episode_id','work_kind','pilot_authorized','full_runs_authorized'), TraceError)
            grant = P2ConformanceAuthority(authority['decision_record_id'], authority['acceptance_test_id'], authority['episode_id'])
        else:
            from .execution import ExecutionAuthority
            if type(execution_authority) is not ExecutionAuthority or execution_authority._guard is not None:
                raise ScopeError('Artifact replay requires a non-executing authority')
            grant = execution_authority
            assert_exact_tree(authority,grant.to_dict())
        engine = Engine(config, grant)  # constructor only; never run an episode here
        version = manifest.get('schema_id')
        if version not in (('EMBORA-MANIFEST-P3-v1.0',) if execution_authority is not None else ('EMBORA-MANIFEST-C6-P2-v1.0', 'EMBORA-MANIFEST-C6-P2-v1.4')):
            raise TraceError('Unknown implementation manifest schema')
        validate_inventory('MANIFEST_SCHEMA_P3_v1.0.json' if execution_authority is not None else 'MANIFEST_SCHEMA_C6_v1.4.json' if version.endswith('v1.4') else 'MANIFEST_SCHEMA_C6_v1.0.json',manifest)
        identity = verify_source_identity(manifest)
        if identity_requirement == 'required' and not identity['strict_identity_satisfied']:
            raise IdentityError('Required source identity is UNVERIFIED: '+identity['reason'])
        expected_manifest = engine.manifest(original,manifest.get('original_config_text'))
        if allow_partial:
            if execution_authority is None: raise ScopeError('Partial replay is administrative-only')
            if manifest['failure_status'] != failures: raise TraceError('Partial failure/manifest mismatch')
            expected_manifest['failure_status'] = failures
            if len(failures) > 1: raise TraceError('Failed episode cannot resume')
            for failure in failures:
                if failure.get('committed') is not False or failure.get('round') != len(rounds)+1 or failure.get('effective_config') != config:
                    raise TraceError('Partial failure position/config mismatch')
        if version == 'EMBORA-MANIFEST-C6-P2-v1.0':
            expected_manifest.pop('source_identity')
        keys(manifest, expected_manifest, TraceError)
        # Immutable source identity is verified independently above. Historical
        # branch/dirty labels are descriptive, never compared with today's labels.
        for k in expected_manifest:
            if k not in ('schema_id','source_identity','source_hashes','code_hash','code_commit','code_branch','dirty_state','trajectory_hash'):
                if canonical(manifest[k])!=canonical(expected_manifest[k]): raise TraceError('Manifest mismatch: '+k)
        if len(rounds) > config['horizon'] or (not allow_partial and len(rounds) != config['horizon']): raise TraceError('Incomplete conformance artifact')
        states = engine.states; history = []
        for t, record in enumerate(rounds,1):
            validate_inventory('PRIVATE_ROUND_SCHEMA_P3_v1.0.json' if execution_authority is not None else 'PRIVATE_ROUND_SCHEMA_C6_v1.0.json',record)
            keys(record, ('schema_id','specification_id','condition_id','pair_id','episode_id','model_mode','game','round','selected_adapter_convention','selected_adapter_id','run_purpose','administrative_authority','agent_descriptors_by_seat','observations_by_seat','pre_states_by_seat','decisions_by_seat','actions_by_seat','payoffs_by_seat','results_by_seat','updates_by_seat','post_states_by_seat','intervention','event_order','event_counters','failure_status'), TraceError)
            observations=[];decisions=[];computed=[]
            for j, agent in enumerate(engine.agents):
                offer = decisions[0]['action']['offer'] if config['game']=='UG' and j==1 else None
                obs = observation(config, agent.descriptor, history, offer)
                observations.append(obs)
                decisions.append(agent.decide({'public_observation':obs,'own_pre_state':None if states[j] is None else states[j].to_dict()}))
            actions=[d['action'] for d in decisions]; payoffs=payoffs_for(config['game'],actions)
            results=[Result.build(config['game'],t,a.descriptor,actions,payoffs) for a in engine.agents]
            for j,a in enumerate(engine.agents):computed.append(a.prepare_update(states[j],observations[j],decisions[j],results[j],t))
            post=tuple(x[0] for x in computed)
            expected={'schema_id':'EMBORA-PRIVATE-ROUND-P3-v1.0' if execution_authority is not None else 'EMBORA-PRIVATE-ROUND-C6-P2-v1.0','specification_id':SPEC_ID,
                      'condition_id':config['condition_id'],'pair_id':config['pair_id'],'episode_id':grant.episode_id,
                      'model_mode':'journal_reference_v1','game':config['game'],'round':t,
                      'selected_adapter_convention':engine.adapter.selected_adapter_convention,'selected_adapter_id':engine.adapter.adapter_id,
                      'run_purpose':config['run_purpose'],'administrative_authority':grant.to_dict(),
                      'agent_descriptors_by_seat':[a.descriptor for a in engine.agents], 'observations_by_seat':observations,
                      'pre_states_by_seat':[None if s is None else s.to_dict() for s in states], 'decisions_by_seat':decisions,
                      'actions_by_seat':actions,'payoffs_by_seat':list(payoffs),'results_by_seat':[r.to_dict() for r in results],
                      'updates_by_seat':[c[1] for c in computed],'post_states_by_seat':[None if s is None else s.to_dict() for s in post],
                      'intervention':{'target_agent_id':config['focal_agent_id'],'variant':next(a['variant'] for a in config['agents'] if a['agent_id']==config['focal_agent_id'])},
                      'failure_status':None, 'event_order':expected_events(config['game']), 'event_counters':{'game_executions_this_round':1,'updates_this_round_by_seat':[1,1],'total_game_executions':t,'total_updates_by_seat':[t,t]}}
            assert_exact_tree(record,expected)
            states=post;history.append({'round':t,'actions_by_seat':actions,'payoffs_by_seat':list(payoffs)})
        if allow_partial:
            for failure in failures:
                assert_exact_tree(failure['history_before_failure'],history)
                assert_exact_tree(failure['pre_states_by_seat'],[None if s is None else s.to_dict() for s in states])
                if type(failure.get('error_type')) is not str or type(failure.get('reason')) is not str:
                    raise TraceError('Malformed partial failure cause')
                events=failure.get('events_before_failure');expected=expected_events(config['game'])[:-1]
                if type(events) is not list or events!=expected[:len(events)]:raise TraceError('Malformed partial failure event prefix')
        if manifest['trajectory_hash']!=trajectory_hash(rounds):raise TraceError('Trajectory hash mismatch')
    except (KeyError, TypeError, StopIteration) as exc:
        raise TraceError('Malformed artifact') from exc
    result = {'status':'PASS' if identity['strict_identity_satisfied'] else 'CONTENT_VALID_IDENTITY_UNVERIFIED',
            'interface_id':'EMBORA-ARTIFACT-VALIDATOR-C6-v1.1','validated_rounds':len(rounds),
            'content_status':'PASS', 'identity':identity, 'identity_requirement':identity_requirement,
            'accepted_code_binding_authorized':False,
            'rounds_executed':0,'trajectory_hash':manifest['trajectory_hash']}
    if allow_partial:
        result.update(interface_id='EMBORA-PARTIAL-CONTENT-VALIDATOR-P3-v1.1',
                      status='PARTIAL_CONTENT_VERIFIED' if identity['strict_identity_satisfied'] else 'PARTIAL_CONTENT_IDENTITY_UNVERIFIED')
    else: validate_inventory('ARTIFACT_VALIDATOR_RECEIPT_C6_v1.1.json',result)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(prog='journal_reference_v1')
    sub = parser.add_subparsers(dest='command',required=True)
    v=sub.add_parser('validate-config');v.add_argument('config');v.add_argument('--receipt')
    r=sub.add_parser('run-conformance');r.add_argument('config');r.add_argument('--authority',required=True);r.add_argument('--acceptance-id',required=True);r.add_argument('--episode-id',required=True);r.add_argument('--output',required=True)
    a=sub.add_parser('validate-artifact');a.add_argument('artifact');a.add_argument('--receipt')
    a.add_argument('--identity-requirement',choices=('required','report'),default='required')
    args=parser.parse_args(argv)
    try:
        if args.command=='validate-artifact':result=validate_artifact(args.artifact,args.identity_requirement)
        else:
            text=Path(args.config).read_text();receipt=validate_config_text(text)
            if args.command=='validate-config':result=receipt
            else:
                engine=Engine(receipt['effective_config'],P2ConformanceAuthority(args.authority,args.acceptance_id,args.episode_id))
                try: engine.run()
                except ContractError:
                    engine.save(args.output,receipt['original_config'],text);raise
                engine.save(args.output,receipt['original_config'],text)
                result={'status':'PASS','work_kind':'conformance','artifact':args.output,'rounds':len(engine.records),'trajectory_hash':trajectory_hash(engine.records)}
        if getattr(args,'receipt',None):
            with Path(args.receipt).open('x') as f:f.write(canonical(result)+'\n')
        print(canonical(result));return 0 if result['status']=='PASS' else 3
    except (ContractError, OSError, json.JSONDecodeError) as exc:
        print(canonical({'status':'FAIL','error_type':type(exc).__name__,'message':str(exc)}),file=sys.stderr);return 2


if __name__=='__main__':sys.exit(main())
