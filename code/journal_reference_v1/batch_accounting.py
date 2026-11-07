"""Sequential external reservation/reconciliation v1.0; no dispatch or permission.

Allocation bytes are proposals. A hash chain detects edits only relative to an
independently retained tip; it is not an authority or an anti-rollback service.
Production checkpoints are computed from native validation and archive readback,
not accepted from caller-authored PASS receipts. Synthetic audit controls have a
separate kind. Reservations are never recycled, including failure/unknown tails.
"""
import argparse
import copy
import os
from pathlib import Path
import sys
import zipfile
from .identity import digest
from .schema import canonical, parse_json
from .inventory import validate_inventory
from .analysis_admission import require, read, sha, files_digest, validate_source

VERSION='EMBORA-SEQUENTIAL-ACCOUNTING-v1.0'
DOMAINS=('attempts','rounds','wall_seconds','output_bytes')
ZERO_REPLAY=dict(additional_attempts=0,additional_rounds=0,max_groups=0,max_per_group=0)



INITIAL_REPLAY_POLICY_BRIDGE='EMBORA-INITIAL-ZERO-REPLAY-BRIDGE-v1.1'


def verify_initial_replay_policy(allocation_policy,native_policy):
    """Map the closed four-limit allocation domain to native initial reason=null.

    No replay allowance, coercion, unknown key or repair reason is admitted.
    Native schema/permission/content verification still runs independently.
    """
    require(type(allocation_policy) is dict and set(allocation_policy)==set(ZERO_REPLAY) and
            all(type(allocation_policy[k]) is int and allocation_policy[k]==0 for k in ZERO_REPLAY),
            'Initial allocation requires exact zero replay limits')
    require(type(native_policy) is dict and set(native_policy)==set(ZERO_REPLAY)|{'reason'} and
            native_policy['reason'] is None and
            all(type(native_policy[k]) is int and native_policy[k]==allocation_policy[k] for k in ZERO_REPLAY),
            'Native initial zero-replay policy differs from allocation')


def verify_allocations(proposal):
    validate_inventory('ACCOUNTING_C6_v1.0.json',proposal)
    require(proposal['schema_id']==VERSION and proposal['status']=='PROPOSED_NOT_AUTHORIZED','Only explicit preparation allocations')
    batches=proposal['allocations'];require(batches,'Empty allocation')
    seen={k:set() for k in ('batch_id','run_ids','attempt_ids','group_ids','output_id')};totals={k:0 for k in DOMAINS}
    for b in batches:
        for k in seen:
            values=b[k] if type(b[k]) is list else [b[k]]
            require(len(values)==len(set(values)) and (not seen[k].intersection(values) or (k=='group_ids' and b['kind']=='REPAIR')),'Duplicate/overlapping allocation '+k);seen[k].update(values)
        require(b['kind'] in ('INITIAL','REPAIR'),'Unknown allocation kind')
        require(b['parent_queue'] is None,'Successful-parent recovery is not batch continuation')
        require(b['stop_rule']=='first_error_or_bound' and b['replay_policy']==ZERO_REPLAY,'No implicit replay allowance')
        require(type(b['caps']['episode_seconds']) is int and b['caps']['episode_seconds']>0 and type(b['caps']['rss_bytes']) is int and b['caps']['rss_bytes']>0,'Invalid non-additive cap')
        for k in DOMAINS:
            v=b['caps'][k];require(type(v) is int and v>0,'Invalid allocation cap')
            require(b['reservation_intervals'][k]==[totals[k],totals[k]+v],'Noncontiguous/overlapping reservation interval')
            totals[k]+=v
        require(b['caps']['attempts']==len(b['run_ids'])==len(b['attempt_ids']),'Exact planned attempts required')
        require(set(b['members'])==set(b['group_ids']) and [r for g in b['group_ids'] for r in b['members'][g]]==b['run_ids'],'Whole group allocation mismatch')
        if b['kind']=='INITIAL':require(b['repair_authority'] is None,'Original allocation cannot invent repair')
        else:
            a=b['repair_authority'];require(a and a['decision_id'] and a['status']=='EXPLICIT_SEPARATE_REPAIR_ALLOCATION','Repair needs separately pinned allocation authority')
            require(len(b['group_ids'])==1 and set(a['replay_of'])==set(b['attempt_ids']) and len(set(a['replay_of'].values()))==len(b['attempt_ids']),'Repair must replace whole group with new IDs')
            require(not set(a['replay_of']).intersection(a['replay_of'].values()),'Repair IDs must be new')
    require(proposal['aggregate_reservations']==totals,'Global cap proposal must equal exact allocation sums')
    require(proposal['nonadditive_caps']==dict(rss_bytes=max(b['caps']['rss_bytes'] for b in batches),episode_seconds=max(b['caps']['episode_seconds'] for b in batches)),'RSS/episode are maxima, not sums')
    return totals


def chain(events):
    previous=None
    for n,event in enumerate(events):
        require(event['sequence']==n and event['previous']==previous,'External ledger chain mismatch')
        previous=digest(event)
    return previous


def event(events,kind,batch_id,receipt=None):
    return dict(sequence=len(events),previous=chain(events),event=kind,batch_id=batch_id,receipt=receipt)


def audit(proposal,events,trusted_tip=None):
    """Rebuild state from pinned allocations/events; never authorizes execution."""
    totals=verify_allocations(proposal);tip=chain(events)
    require(tip==trusted_tip,'External expected ledger tip mismatch')
    allocations=proposal['allocations'];by_id={b['batch_id']:b for b in allocations};states={};active=None;halt=None;consumed={k:0 for k in DOMAINS};reserved={k:0 for k in DOMAINS};receipts={}
    for e in events:
        bid=e['batch_id'];require(bid in by_id,'Unknown batch ID');b=by_id[bid];kind=e['event']
        if kind=='RESERVE':
            require(bid not in states and active is None and halt is None,'Duplicate/unresolved/failed batch halts next reservation')
            earlier=[x['batch_id'] for x in allocations[:allocations.index(b)]]
            require(all(states.get(x)=='COMPLETE' for x in earlier if by_id[x]['kind']=='INITIAL'),'Sequential allocation order violated')
            require(b['kind']=='INITIAL','Repair requires separate RESOLVE_REPAIR event')
            active=bid;states[bid]='RESERVED'
            for k in DOMAINS:reserved[k]+=b['caps'][k];require(reserved[k]<=totals[k],'Global reservation exhausted')
        elif kind=='RESOLVE_REPAIR':
            a=b['repair_authority'];require(b['kind']=='REPAIR' and bid not in states and active is None and halt is not None,'No unresolved failed group to repair')
            parent=a['parent_batch_id'];require(parent==halt and states[parent]=='FAILED' and receipts[parent]['recoverable_transient'],'Healthy/unknown/nontransient parent cannot recover')
            require(a['group_id']==receipts[parent]['failed_group'] and b['group_ids']==[a['group_id']] and
                    set(b['members'][a['group_id']])==set(a['new_run_ids']) and
                    set(a['replay_of'].values())==set(receipts[parent]['group_attempt_ids'][a['group_id']]),'Repair must replace exact whole failed group')
            require(a['group_id'] in by_id[parent]['members'] and len(b['run_ids'])==len(by_id[parent]['members'][a['group_id']]),'Incomplete repair group')
            halt=None;active=bid;states[bid]='RESERVED'
            for k in DOMAINS:reserved[k]+=b['caps'][k];require(reserved[k]<=totals[k],'Repair allocation exhausted')
        elif kind=='RECONCILE':
            require(active==bid and states.get(bid)=='RESERVED','Reconcile requires the sole outstanding reservation')
            r=e['receipt'];require(r['allocation_sha256']==digest(b) and r['kind']==proposal['receipt_kind'],'Wrong/synthetic receipt domain')
            require(r['plan_sha256']==b['plan_sha256'] and r['output_id']==b['output_id'],'Wrong plan/output identity')
            require(r['status'] in ('COMPLETE','FAILED','UNKNOWN'),'Unknown completion status')
            for k in DOMAINS:
                v=r['consumption'][k];require(type(v) in (int,float) and type(v) is not bool and v>=0 and v<float('inf'),'Invalid consumption')
                if k in ('attempts','rounds','output_bytes'):require(type(v) is int,'Integer resource domain required')
                consumed[k]+=v
            if r['status']=='COMPLETE':
                require(r['consumption']['attempts']==b['caps']['attempts'] and r['consumption']['rounds']==b['caps']['rounds'] and
                        r['committed_rounds']==b['caps']['rounds'] and r['known_unstarted_attempts']==0,'Complete accounting prefix mismatch')
                require(all(r['consumption'][k]<b['caps'][k] for k in ('wall_seconds','output_bytes')) and
                        r['peak_rss_bytes']<b['caps']['rss_bytes'] and r['episode_seconds']<b['caps']['episode_seconds'],'Late bound cannot complete')
                require(r['native_validation_sha256'] and r['archive_sha256'] and r['readback_sha256']==r['archive_sha256'],'Validation/archive/readback checkpoints required')
                states[bid]='COMPLETE'
            else:states[bid]=r['status'];halt=bid
            receipts[bid]=r;active=None
        elif kind=='LATE_FAILURE':
            require(states.get(bid) in ('COMPLETE','FAILED','UNKNOWN'),'Late failure for unknown batch')
            states[bid]='FAILED';halt=bid
        else:raise ValueError('Unknown sequential accounting event')
    return dict(schema_id=VERSION,status='HALTED' if halt or active else 'CHECKPOINTED',states=states,active=active,halt=halt,
                aggregate_reservations=totals,reserved_ever=reserved,charged_consumption=consumed,
                reservation_release='NONE_CONSERVATIVE',tip_sha256=tip,execution_authorized=False)


def reconcile_native(proposal,batch_id,source_spec,validator_root,python,validator_source,archive_path):
    """Compute a production operator receipt from actual native validation/readback.

    Caller separately pins allocation bytes, permission digest and archive path.
    No native mutation, no grant creation and no invocation of run.
    """
    verify_allocations(proposal);require(proposal['receipt_kind']=='NATIVE_VERIFIED','Synthetic proposal cannot label production')
    b=next(x for x in proposal['allocations'] if x['batch_id']==batch_id);require(b['kind']=='INITIAL','Native repair reconciliation requires separately reviewed cumulative parent allocation; no implicit recovery');q=Path(source_spec['path']).resolve()
    require(source_spec['route']=='queue' and source_spec['plan_sha256']==b['plan_sha256'],'Exact allocation plan required')
    before=files_digest(q);require(digest(before)==source_spec['inventory_sha256'],'Queue bytes not pinned')
    plan=read(q/'plan.json');require(plan['parent_queue'] is None if b['kind']=='INITIAL' else plan['parent_queue'] is not None,'Batch continuation cannot masquerade as recovery')
    require([r['run_id'] for r in plan['runs']]==b['run_ids'] and [r['attempt_id'] for r in plan['runs']]==b['attempt_ids'],'Native dispatch IDs differ from allocation')
    require(read(q/'permission.json')['output']==b['output_id'],'Native output identity differs from allocation')
    grant=read(q/'permission.json')
    require(grant['caps']==b['caps'],'Native caps differ from allocation')
    verify_initial_replay_policy(b['replay_policy'],grant['replay_policy'])
    native=validate_source(source_spec,validator_root,python,validator_source)
    result=native['result'];seal=read(q/'seal.json');queue=read(q/'queue.json')
    archive=Path(archive_path).resolve();require(not archive.is_relative_to(q),'Archive must be outside immutable queue')
    with zipfile.ZipFile(archive) as z:
        require(len(z.namelist())==len(set(z.namelist())) and set(z.namelist())==set(before) and z.testzip() is None,'Archive file-set/CRC checkpoint failed')
        require(all(sha(z.read(k))==v for k,v in before.items()),'Archive lossless readback mismatch')
    require(before==files_digest(q),'Queue changed before reconciliation')
    ah=sha(archive.read_bytes());total=seal['output_bytes']+(q/'seal.json').stat().st_size
    # Native final-sealed wall/RSS and raw output domains; CPU sample stays separate.
    return dict(kind='NATIVE_VERIFIED',allocation_sha256=digest(b),plan_sha256=b['plan_sha256'],output_id=b['output_id'],status=result['status'],
                consumption=dict(attempts=len(queue['attempts']),rounds=sum(prepare_horizon(r) for r in plan['runs'][:len(queue['attempts'])]),wall_seconds=seal['wall_seconds'],output_bytes=total),
                committed_rounds=queue['committed_rounds'],known_unstarted_attempts=len(queue['not_started']),peak_rss_bytes=seal['peak_rss_bytes'],episode_seconds=seal['episode_seconds'],
                native_validation_sha256=digest(native),archive_sha256=ah,readback_sha256=ah,cpu_sample=queue['cpu_seconds'],
                failed_group=result['failed_group'],recoverable_transient=result['recoverable_transient'],
                group_attempt_ids={g:[r['attempt_id'] for r in plan['runs'] if r['group_id']==g] for g in b['group_ids']})


def prepare_horizon(run):
    from .schema import prepare_config
    return prepare_config(parse_json(run['config_text']))['horizon']


def save_event(path,events,expected_tip,new_event):
    """Exclusive next file. Caller retains tip externally; never overwrite history."""
    require(chain(events)==expected_tip,'Stale expected tip')
    require(new_event['previous']==expected_tip and new_event['sequence']==len(events),'Event chain mismatch')
    with Path(path).open('x') as f:f.write(canonical(new_event)+'\n');f.flush();os.fsync(f.fileno())


def main(argv=None):
    p=argparse.ArgumentParser(description='Read-only sequential allocation audit; never dispatches')
    p.add_argument('--proposal',required=True);p.add_argument('--proposal-sha256',required=True);p.add_argument('--events',required=True);p.add_argument('--tip')
    args=p.parse_args(argv)
    try:
        raw=Path(args.proposal).read_bytes();require(sha(raw)==args.proposal_sha256,'Trusted allocation proposal mismatch')
        out=audit(parse_json(raw.decode()),read(args.events),args.tip);print(canonical(out));return 2 if out['status']=='HALTED' else 0
    except (ValueError,OSError,KeyError,TypeError,StopIteration) as e:
        print(canonical(dict(status='FAIL',message=str(e),execution_authorized=False)),file=sys.stderr);return 2

if __name__=='__main__':sys.exit(main())
