"""Regressions for the two auditor counterexamples; no experiment authority."""
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import pytest
from journal_reference_v1 import schema as s
from journal_reference_v1.cli import validate_config_text, validate_artifact
from journal_reference_v1.identity import capture_source_identity, verify_source_identity, digest
from journal_reference_v1.numeric import bits, channel_projection
from journal_reference_v1.games import Adapter, observation, Result
from journal_reference_v1.model import Agent
from test_integration_s12 import fixture, engine


@pytest.mark.parametrize('token,negative',[('-0',True),('-0.0',True),('-0e0',True),('-0.00e+0',True),('0',False),('0.0',False),('0e0',False)])
def test_AT_INVALID_STATE_signed_json_zero_lineage_serialization_qv_F32(token,negative):
    cfg=fixture(variant='material_only',v=-0.)
    text=s.canonical(cfg).replace(':-0.0',':'+token)
    receipt=validate_config_text(text)
    original=receipt['original_config']['agents'][1]['initial_primary_state']['v']
    effective=receipt['effective_config']['agents'][1]['initial_primary_state']['v']
    expected='8000000000000000' if negative else '0000000000000000'
    assert receipt['original_numeric_tokens']['/agents/1/initial_primary_state/v/material']==token
    for values in (original,effective,s.parse_json(s.canonical(effective))):
        assert all(bits(v)==expected for v in values.values())
    assert receipt['original_text_sha256']==hashlib.sha256(text.encode()).hexdigest()
    assert receipt['effective_config_sha256']==hashlib.sha256(s.canonical(receipt['effective_config']).encode()).hexdigest()
    # Distinct hash domains can coincide when their input bytes coincide.
    spaced=validate_config_text(text+'\n')
    assert spaced['original_text_sha256']!=receipt['original_text_sha256']
    assert spaced['effective_config_sha256']==receipt['effective_config_sha256']
    cfg=receipt['effective_config'];agent=Agent.construct(cfg,2,Adapter(cfg['selected_adapter_convention'],cfg['run_purpose']))
    state=agent.initial_state
    assert bits(channel_projection(state.v[0],-0.)['current'])==expected
    obs=observation(cfg,agent.descriptor,[],8);decision=agent.decide({'public_observation':obs,'own_pre_state':state.to_dict()})
    result=Result.build('UG',1,agent.descriptor,[{'name':'offer','offer':8},decision['action']])
    post,trace=agent.prepare_update(state,obs,decision,result,1)
    assert all(bits(v)==expected for v in post.v[1:])
    assert trace['update_count']==1
    manifest=engine(cfg).manifest(receipt['original_config'],text)
    assert all(bits(v)==expected for v in manifest['source_initial_states_by_seat'][1]['v'].values())
    assert all(bits(v)==expected for v in manifest['effective_initial_states_by_seat'][1]['v'].values())


@pytest.mark.parametrize('token',['0','1','-1','2147483647'])
def test_AT_INVALID_integer_tokens_remain_integers(token):
    value=s.parse_json(token)
    assert type(value) is int and value==int(token)


@pytest.mark.parametrize('token',['-0','-0.0','0.0','true','false','null','"0"'])
def test_AT_INVALID_integer_fields_are_not_coerced(token):
    with pytest.raises(s.ContractError):s.integer(s.parse_json(token),0,5)


@pytest.mark.parametrize('text',['+0','01','NaN','Infinity','{"x":0,"x":-0}'])
def test_AT_INVALID_signed_zero_patch_keeps_strict_json(text):
    with pytest.raises((s.ContractError,json.JSONDecodeError)):s.parse_json(text)


def rehash_artifact(path,mutate):
    manifest=s.parse_json((path/'manifest.json').read_text());mutate(manifest)
    (path/'manifest.json').write_text(s.canonical(manifest)+'\n')
    hashes=s.parse_json((path/'artifact_hashes.json').read_text())
    hashes['manifest.json']=hashlib.sha256((path/'manifest.json').read_bytes()).hexdigest()
    (path/'artifact_hashes.json').write_text(s.canonical(hashes)+'\n')


@pytest.fixture
def artifact(tmp_path):
    cfg=fixture(horizon=1);e=engine(cfg);e.run();path=tmp_path/'artifact';e.save(path,cfg)
    return path


@pytest.mark.parametrize('commit',['this-is-not-a-git-commit','a'*39,'A'*40,'--help','',None,False])
def test_AT_INVALID_artifact_malformed_identity_fails_hard(artifact,commit):
    rehash_artifact(artifact,lambda m:m.update(code_commit=commit))
    with pytest.raises(s.TraceError):validate_artifact(artifact)


@pytest.mark.parametrize('mutator',[
    lambda m:m.update(code_commit='78f136e5f1719cda4c2a53df4b837bb5bf6ac461'),
    lambda m:m['source_identity'].update(code_tree='0'*40),
    lambda m:m['source_identity'].update(tracked_inventory_sha256='0'*64),
    lambda m:m['source_identity'].update(tracked_content_matches_commit=False),
    lambda m:m['source_identity'].update(logged_source_domain='all_files'),
])
def test_AT_INVALID_artifact_wrong_commit_tree_inventory_domains(artifact,mutator):
    rehash_artifact(artifact,mutator)
    with pytest.raises(s.TraceError):validate_artifact(artifact)


def test_AT_INVALID_artifact_available_identity_and_historical_labels(artifact):
    rehash_artifact(artifact,lambda m:m.update(code_branch='historical/different-label',dirty_state='?? historical-untracked-file'))
    result=validate_artifact(artifact)
    assert result['status']=='PASS' and result['identity']['status']=='VERIFIED'
    assert result['identity']['strict_identity_satisfied'] is True
    assert result['accepted_code_binding_authorized'] is False


def test_AT_INVALID_artifact_unknown_commit_report_is_not_binding_PASS(artifact):
    rehash_artifact(artifact,lambda m:m.update(code_commit='f'*40))
    with pytest.raises(s.IdentityError):validate_artifact(artifact)
    result=validate_artifact(artifact,'report')
    assert result['status']=='CONTENT_VALID_IDENTITY_UNVERIFIED'
    assert result['identity']['reason']=='recorded_commit_unavailable_locally'
    assert result['identity']['strict_identity_satisfied'] is False
    assert result['accepted_code_binding_authorized'] is False
    env=dict(os.environ,PYTHONPATH=str(Path(__file__).resolve().parents[2]))
    command=[sys.executable,'-m','journal_reference_v1','validate-artifact',str(artifact)]
    strict=subprocess.run(command,capture_output=True,text=True,env=env)
    assert strict.returncode==2 and json.loads(strict.stderr)['error_type']=='IdentityError'
    reporting=subprocess.run(command+['--identity-requirement','report'],capture_output=True,text=True,env=env)
    assert reporting.returncode==3 and json.loads(reporting.stdout)['status']=='CONTENT_VALID_IDENTITY_UNVERIFIED'


def test_AT_INVALID_artifact_legacy_mode_cannot_claim_full_identity(artifact):
    def legacy(m):m['schema_id']='EMBORA-MANIFEST-C6-P2-v1.0';m.pop('source_identity')
    rehash_artifact(artifact,legacy)
    with pytest.raises(s.IdentityError):validate_artifact(artifact)
    result=validate_artifact(artifact,'report')
    assert result['content_status']=='PASS' and result['status']!='PASS'
    assert result['identity']['logged_source_verified'] is True
    assert result['identity']['strict_identity_satisfied'] is False


def test_AT_INVALID_full_inventory_separate_from_logged_domain_and_equivalent_tree(tmp_path):
    repo=tmp_path/'git';repo.mkdir()
    def git(*args):return subprocess.check_output(['git','-C',str(repo),*args],text=True).strip()
    git('init','-q');git('config','user.name','Conformance fixture');git('config','user.email','fixture@example.invalid')
    module=repo/'code/journal_reference_v1/demo.py';module.parent.mkdir(parents=True);module.write_text('marker = 1\n')
    (repo/'outside.bin').write_bytes(b'one');git('add','.');git('commit','-qm','identity fixture')
    original=git('rev-parse','HEAD')
    hashes={'code/journal_reference_v1/demo.py':hashlib.sha256(module.read_bytes()).hexdigest()}
    manifest={'code_commit':original,'source_hashes':hashes,'code_hash':digest(hashes),'source_identity':capture_source_identity(repo)}
    assert verify_source_identity(manifest,repo)['status']=='VERIFIED'
    git('commit','--allow-empty','-qm','equivalent tree')
    assert verify_source_identity(manifest,repo)['relation_to_verifier']=='EQUIVALENT_TREE'
    (repo/'outside.bin').write_bytes(b'two');git('add','.');git('commit','-qm','outside logged domain')
    wrong=copy.deepcopy(manifest);wrong['code_commit']=git('rev-parse','HEAD')
    with pytest.raises(s.IdentityError):verify_source_identity(wrong,repo)
    assert verify_source_identity(manifest,repo)['relation_to_verifier']=='VERIFIED_HISTORICAL_TREE'
