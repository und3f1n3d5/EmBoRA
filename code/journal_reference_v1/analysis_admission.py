"""C6 downstream admission v1.0; read-only native replay, no execution/grant API.

Trust is an independently supplied raw admission digest, never an artifact PASS.
A separate exact checkout runs its own unchanged native validator. This module
neither generalizes historical readback nor changes native identity semantics.
"""
import argparse
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
from . import pap_metrics as metrics
from .identity import capture_source_identity, git, digest
from .schema import canonical, parse_json, prepare_config, TraceError, IdentityError
from .inventory import validate_inventory
from .evidence import runtime_hash

VERSION = 'EMBORA-ADMITTED-ANALYSIS-C6-v1.0'
ADMISSION = 'EMBORA-ANALYSIS-ADMISSION-C6-v1.0'
PAP = 'EMBORA-P3-PAP-2026-10-18-C6-P2v1.4-v1.0'
PAP_SHA = 'e093a94888ef4f510aeb4cfd3e035022245d260672a204c7d8361988fef40b80'


def require(ok, message):
    if not ok: raise TraceError(message)


def sha(data):
    import hashlib
    return hashlib.sha256(data).hexdigest()


def read(path): return parse_json(Path(path).read_text())


def snapshot(root):
    root=Path(root).resolve(); i=capture_source_identity(root)
    if git(root,'status','--porcelain=v1').strip() or not i['tracked_content_matches_commit']:
        raise IdentityError('Exact clean checkout required')
    return dict(commit=git(root,'rev-parse','HEAD').decode().strip(),tree=i['code_tree'],
                inventory_sha256=i['tracked_inventory_sha256'])


# Executed by the pinned interpreter in the pinned validator checkout. No run,
# Engine.step or external game dispatch occurs. Native replay remains mandatory.
WORKER = '''import json,sys
from pathlib import Path
from journal_reference_v1.evidence import runtime_hash
from journal_reference_v1.identity import capture_source_identity,git,ROOT
p=json.loads(sys.argv[1]);i=capture_source_identity()
s=dict(commit=git(ROOT,'rev-parse','HEAD').decode().strip(),tree=i['code_tree'],inventory_sha256=i['tracked_inventory_sha256'])
assert not git(ROOT,'status','--porcelain=v1').strip() and i['tracked_content_matches_commit']
assert s==p['validator_source'] and runtime_hash()==p['runtime_sha256']
if p['route']=='queue':
 from journal_reference_v1.accounting import verify_accounting
 from journal_reference_v1.execution import read,digest
 q=Path(p['path']);plan=read(q/'plan.json')
 assert digest(plan)==p['plan_sha256'] and plan['source']==dict(**s,runtime_sha256=p['runtime_sha256'])
 result=verify_accounting(q,p['permission_sha256'],identity_requirement='required')
 assert result['identity_verified']
else:
 from journal_reference_v1.cli import validate_artifact
 result=validate_artifact(p['path'],'required')
 assert result['status']=='PASS' and result['identity']['strict_identity_satisfied']
print(json.dumps(dict(source=s,runtime_sha256=runtime_hash(),result=result)))
'''


def validate_source(spec, validator_root, python, validator_source):
    """Return actual native checks and process receipt, never consume a PASS file."""
    require(spec['route'] in ('queue','conformance_test_only'),'Unknown native route')
    require(spec['route']!='queue' or (type(spec['permission_sha256']) is str and len(spec['permission_sha256'])==64 and type(spec['plan_sha256']) is str and len(spec['plan_sha256'])==64),'Queue requires independently pinned permission/plan hashes')
    payload=dict(spec,validator_source=validator_source)
    root=Path(validator_root).resolve(); before=snapshot(root)
    require(before==validator_source,'Validator source binding mismatch')
    env=os.environ.copy();env.pop('PYTHONOPTIMIZE',None);env.update(PYTHONPATH=str(root/'code'),PYTHONDONTWRITEBYTECODE='1')
    argv=[str(Path(python).absolute()),'-c',WORKER,canonical(payload)]
    p=subprocess.run(argv,cwd=root,env=env,capture_output=True,text=True)
    require(snapshot(root)==before,'Validator checkout changed during replay')
    require(p.returncode==0,'Native strict validation rejected: '+p.stderr[-1600:])
    out=parse_json(p.stdout)
    require(out['source']==validator_source and out['runtime_sha256']==spec['runtime_sha256'],'Native verifier provenance mismatch')
    out['invocation']=dict(argv=argv,cwd=str(root),exit_code=p.returncode,stdout=p.stdout,stderr=p.stderr,
                           environment={k:env[k] for k in ('PYTHONPATH','PYTHONDONTWRITEBYTECODE')})
    return out


def files_digest(path):
    path=Path(path).resolve()
    require(path.is_dir(),'Native input directory missing')
    require(not any(p.is_symlink() for p in path.rglob('*')),'Symlink native input forbidden')
    return {str(p.relative_to(path)):sha(p.read_bytes()) for p in sorted(path.rglob('*')) if p.is_file()}



def native_whole_group(candidate, group, sources):
    ids={v['source_id'] for v in candidate['members'].values()}
    require(len(ids)==1,'Whole native group must come from one queue')
    spec=sources[next(iter(ids))];require(spec['route']=='queue','Production whole group requires a native queue')
    plan=read(Path(spec['path'])/'plan.json')
    actual=[r['base_run_id'] for r in plan['runs'] if r['group_id']==group['condition_id']]
    require(actual==group['members'],'Native queue does not contain exact ordered whole group')


def admitted_analysis(admission_raw, trusted_sha256, protocol, validator_root, python):
    require(sha(admission_raw)==trusted_sha256,'Externally trusted admission digest mismatch')
    a=parse_json(admission_raw.decode());validate_inventory('ANALYSIS_C6_v1.0.json',a)
    require(a['schema_id']==ADMISSION and a['protocol_id']==PAP and sha(protocol)==a['protocol_sha256']==PAP_SHA,'PAP binding mismatch')
    require(a['kind'] in ('PRODUCTION','SYNTHETIC_TEST_ONLY') and bool(a['decision_id']),'Unknown admission kind/decision')
    root=Path(__file__).resolve().parents[2]; analysis=snapshot(root)
    require(analysis==a['analysis_source'],'Analysis source binding mismatch')
    require(runtime_hash()==a['runtime_sha256'],'Analysis runtime mismatch')
    configs={k:prepare_config(parse_json(v)) for k,v in a['config_texts'].items()}
    require(a['validator_source']['commit']=='deea6aa72e003da646887e2a41029fbf2ef9c506','Unreviewed validator requires explicit successor policy')
    groups=a['groups'];require(groups and a['contrasts'],'Nonempty expected group/contrast inventory required');expected=[r for g in groups for r in g['members']]
    require(len(expected)==len(set(expected)) and set(expected)==set(configs),'Expected group/config inventory mismatch')
    require(len({g['condition_id'] for g in groups})==len(groups),'Duplicate condition group')
    source_results={};source_hashes={};rounds={};invalid={};lineage=[];generation={};used=set()
    for source_id,spec in a['sources'].items():
        require(spec['route']=='queue' or a['kind']=='SYNTHETIC_TEST_ONLY','Conformance receipt cannot admit production')
        before=files_digest(spec['path']);source_hashes[source_id]=before
        require(digest(before)==spec['inventory_sha256'],'Native directory hash binding mismatch')
        # A missing selected leaf is handled below as incomplete, never by mixing
        # another attempt. Semantic/binding failures reject the whole invocation.
        source_results[source_id]=validate_source(spec,validator_root,python,a['validator_source'])
        require(files_digest(spec['path'])==before,'Native bytes changed during validation')
    for g in groups:
        members=g['members'];require(all(configs[k]['condition_id']==g['condition_id'] for k in members),'Wrong condition group')
        variants={(metrics.focal(configs[k])['kind'],metrics.focal(configs[k])['variant']) for k in members}
        wanted={('hybrid','full')}|{('hybrid',v) for v in metrics.SWITCHES}
        if g['group_kind']=='base':wanted|={('emotional_only','full'),('rational_only','full')}
        require(g['group_kind'] in ('base','sensitivity') and variants==wanted and len(members)==len(wanted),'Incomplete registered whole group')
        candidates=g['candidates'];ids=[c['group_attempt_id'] for c in candidates]
        require(len(ids)==len(set(ids)) and ids and g['selected'] in ids,'Ambiguous selected group attempt')
        by_id={c['group_attempt_id']:c for c in candidates};selected=by_id[g['selected']]
        full=next(k for k in members if (metrics.focal(configs[k])['kind'],metrics.focal(configs[k])['variant'])==('hybrid','full'))
        contrasts=[c for c in a['contrasts'] if c['full_run_id'] in members or c['comparison_run_id'] in members]
        require(len(contrasts)==len(members)-1 and {c['comparison_run_id'] for c in contrasts}==set(members)-{full} and
                all(c['full_run_id']==full for c in contrasts),'Incomplete registered group contrast inventory')
        for c in candidates:
            if a['kind']=='PRODUCTION':native_whole_group(c,g,a['sources'])
            require(set(c['members'])==set(members),'Mixed-leaf/incomplete attempt group')
            predecessor=c['replaces']
            if predecessor is None:
                require(c is candidates[0] and c['repair_authority'] is None,'Only first group attempt may be original')
            else:
                require(predecessor in by_id and ids.index(predecessor)<ids.index(c['group_attempt_id']),'Invalid repair ancestry')
                auth=c['repair_authority']
                require(auth and auth['decision_id'] and auth['status']=='WHOLE_GROUP_REPAIR_AUTHORIZED' and
                        auth['replaces']==predecessor and auth['group_attempt_id']==c['group_attempt_id'],'Unauthorized repair')
                require(auth['kind']==a['kind'],'Synthetic repair authority cannot admit production')
            for k,leaf in c['members'].items():
                require(leaf['group_attempt_id']==c['group_attempt_id'],'Mixed attempt leaves')
                require(leaf['source_id'] in a['sources'],'Unknown native source')
                old=None if predecessor is None else by_id[predecessor]['members'][k]
                require((leaf['replay_of'] is None and leaf['run_id']==k) if old is None else
                        (leaf['replay_of']==old['attempt_id'] and leaf['run_id']!=old['run_id'] and leaf['attempt_id']!=old['attempt_id']),
                        'Repair requires new IDs and exact replay_of')
                if a['kind']=='PRODUCTION':
                    spec=a['sources'][leaf['source_id']];src=Path(spec['path']).resolve();plan=read(src/'plan.json')
                    rows=[r for r in plan['runs'] if r['attempt_id']==leaf['attempt_id']]
                    require(len(rows)==1 and (rows[0]['base_run_id'],rows[0]['run_id'],rows[0]['group_id'],rows[0]['replay_of'],rows[0]['config_text'])==
                            (k,leaf['run_id'],g['condition_id'],leaf['replay_of'],a['config_texts'][k]),'Candidate native attempt mismatch')
                    if old is not None:
                        parent=a['sources'][old['source_id']];pr=source_results[old['source_id']]['result']
                        require(pr['status']=='FAILED' and pr['failed_group']==g['condition_id'] and pr['recoverable_transient'] and
                                plan['parent_queue'] is not None and Path(plan['parent_queue']['path']).resolve()==Path(parent['path']).resolve(),
                                'Repair cannot replace a healthy/unknown/different native parent')
        for k,leaf in selected['members'].items():
            token=leaf['attempt_id'];require(token not in used,'Duplicate selected attempt');used.add(token)
            spec=a['sources'][leaf['source_id']];src=Path(spec['path']).resolve();native=(src/leaf['native_relative_path']).resolve()
            require(native==src or src in native.parents,'Native leaf escapes admitted source')
            if not native.exists():invalid[k]='ARTIFACT_INCOMPLETE';continue
            m=read(native/'manifest.json');config=configs[k]
            require(m['original_config_text']==a['config_texts'][k] and m['config_hash']==digest(config),'Native source/effective config mismatch')
            require(m['runtime_lock_sha256']==a['runtime_sha256'] and m['code_commit']==a['validator_source']['commit'] and
                    m['source_identity']['code_tree']==a['validator_source']['tree'] and
                    m['source_identity']['tracked_inventory_sha256']==a['validator_source']['inventory_sha256'],'Generation source/runtime binding mismatch')
            if a['kind']=='SYNTHETIC_TEST_ONLY':
                require(config['run_purpose']=='structural_fixture' and config['horizon']<=8,'Synthetic scope cannot admit PAP trajectories')
            else:
                require(spec['route']=='queue' and config['run_purpose']!='structural_fixture','Production requires administrative content')
            if spec['route']=='queue':
                plan=read(src/'plan.json'); matches=[r for r in plan['runs'] if r['attempt_id']==leaf['attempt_id']]
                require(len(matches)==1,'Attempt absent from validated plan');r=matches[0]
                require((r['base_run_id'],r['run_id'],r['group_id'],r['replay_of'],r['config_text'])==
                        (k,leaf['run_id'],g['condition_id'],leaf['replay_of'],a['config_texts'][k]),'Native attempt lineage mismatch')
                require(leaf['native_relative_path']==leaf['attempt_id']+'/native','Wrong native attempt path')
                require(source_results[leaf['source_id']]['result']['status']=='COMPLETE','Incomplete queue cannot admit scientific export')
            else:
                require(m['administrative_authority']['episode_id']==leaf['attempt_id'],'Conformance fixture attempt mismatch')
            require(not read(native/'failures.json'),'Failed native content');rounds[k]=read(native/'rounds.json')
            generation[k]=dict(commit=m['code_commit'],tree=m['source_identity']['code_tree'],
                inventory_sha256=m['source_identity']['tracked_inventory_sha256'],runtime_sha256=m['runtime_lock_sha256'],
                source_config_sha256=sha(a['config_texts'][k].encode()),effective_config_sha256=m['config_hash'],
                trajectory_sha256=m['trajectory_hash'],native_source_id=leaf['source_id'])
        lineage.append(copy.deepcopy(g))
    result=metrics.inventory_metrics(configs,rounds,a['contrasts'],invalid)
    cells=metrics.registered_cells(configs,a['contrasts'],result['pair_metrics'])
    complete=(all(r['status']=='VALID' for r in result['run_inventory'].values()) and
              all(r['status']=='VALID' for r in result['pair_metrics']) and all(c['summary']['status']=='COMPLETE' for c in cells))
    # Unselected sources/extra leaves cannot silently become observed successes.
    require(all(files_digest(a['sources'][k]['path'])==v for k,v in source_hashes.items()),'Input changed before export')
    require(snapshot(root)==analysis,'Analysis source changed during export')
    out=dict(schema_id=VERSION,protocol_id=PAP,protocol_sha256=PAP_SHA,kind=a['kind'],status='COMPLETE' if complete else 'INCOMPLETE',
             admission_sha256=trusted_sha256,decision_id=a['decision_id'],analysis_identity=analysis,
             validation_identity=dict(source=a['validator_source'],runtime_sha256=a['runtime_sha256']),
             generation_identities=generation,native_input_hashes=source_hashes,native_validation=source_results,
             whole_group_lineage=lineage,metrics=result,cells=cells,
             alternatives=dict(normalized_delta_Q=None,rank_Q=None,strict_discordance=None,persistence=None,
                               reason='PAP_OWNER_DISPOSITION_REQUIRED'),experimental_rounds_executed=0)
    validate_inventory('ANALYSIS_C6_v1.0.json',out)
    return out


def write_export(path,out,admission):
    path=Path(path).absolute()
    for spec in admission['sources'].values():
        src=Path(spec['path']).resolve()
        require(path.resolve()!=src and src not in path.resolve().parents,'Export must be outside immutable native directories')
    with path.open('x') as f:f.write(canonical(out)+'\n');f.flush();os.fsync(f.fileno())


def main(argv=None):
    p=argparse.ArgumentParser();p.add_argument('command',choices=('export','verify'));p.add_argument('--admission',required=True)
    p.add_argument('--admission-sha256',required=True);p.add_argument('--protocol',required=True);p.add_argument('--validator-source',required=True)
    p.add_argument('--python',required=True);p.add_argument('--output',required=True);args=p.parse_args(argv)
    try:
        raw=Path(args.admission).read_bytes();out=admitted_analysis(raw,args.admission_sha256,Path(args.protocol).read_bytes(),args.validator_source,args.python)
        if args.command=='verify':require(canonical(read(args.output))==canonical(out),'C6 schema/content/export mismatch')
        else:write_export(args.output,out,parse_json(raw.decode()))
        print(canonical(dict(status=out['status'],schema_id=VERSION,experimental_rounds_executed=0)));return 0 if out['status']=='COMPLETE' else 2
    except (ValueError,OSError,KeyError,TypeError,AssertionError) as e:
        print(canonical(dict(status='FAIL',error_type=type(e).__name__,message=str(e),experimental_rounds_executed=0)),file=sys.stderr);return 2

if __name__=='__main__':sys.exit(main())
