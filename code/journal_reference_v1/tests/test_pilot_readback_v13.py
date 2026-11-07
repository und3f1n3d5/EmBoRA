"""Saved-data/schema/readback checks; no Engine.step or external games."""
import copy
import json
from pathlib import Path
import pytest
from journal_reference_v1 import readback as rb
from journal_reference_v1 import identity as ident
from journal_reference_v1.inventory import validate_inventory, validate_structure
from journal_reference_v1.schema import TraceError, IdentityError, ContractError
from journal_reference_v1.numeric import channel_projection
from journal_reference_v1.evidence import channel_evidence, validate_evidence

ROOT = Path(__file__).resolve().parents[1]
SLOT = ('properties','decisions_by_seat','items','properties','choice','anyOf',1,
        'properties','candidates','properties','accept','properties','numeric_evidence',
        'properties','material','properties','nodes')


def node_schema():
    schema = json.loads((ROOT/'schemas/PRIVATE_ROUND_SCHEMA_P3_v1.1.json').read_text())
    for key in SLOT: schema = schema[key]
    return schema


def test_saved_round81_old_schema_fails_successor_schema_passes():
    record = json.loads((ROOT/'tests/fixtures/initial01_round81.json').read_text())
    with pytest.raises(TraceError,match='No schema alternative matches'):
        validate_inventory('PRIVATE_ROUND_SCHEMA_P3_v1.0.json',record)
    validate_inventory('PRIVATE_ROUND_SCHEMA_P3_v1.1.json',record)
    evidence = record['decisions_by_seat'][1]['choice']['candidates']['accept']['numeric_evidence']['material']
    assert evidence['nodes']['identity'] is True
    assert evidence['rounded_inputs']['v']['bits_hex'] == evidence['rounded_inputs']['q']['bits_hex'] == '3fe4000000000000'
    assert evidence['executable_B']['bits_hex']=='0000000000000000'
    validate_evidence(evidence)


@pytest.mark.parametrize('identity',[True,False])
def test_exact_branch_shapes(identity):
    evidence=channel_evidence(.625,.625 if identity else .75,channel_projection(.625,.625 if identity else .75))
    validate_structure(node_schema(),evidence['nodes']);validate_evidence(evidence)
    assert len(evidence['nodes'])==(9 if identity else 13)
    for key in evidence['nodes']:
        broken=copy.deepcopy(evidence['nodes']);broken.pop(key)
        with pytest.raises(TraceError):validate_structure(node_schema(),broken)
    for mutate in (lambda n:n.update(identity=not identity),lambda n:n.update(extra=0),lambda n:n.update(identity=1)):
        broken=copy.deepcopy(evidence['nodes']);mutate(broken)
        with pytest.raises(TraceError):validate_structure(node_schema(),broken)


@pytest.mark.parametrize('field',['bits_hex','float','fraction','hex','sign_bit'])
def test_semantic_numeric_mutation_still_rejects(field):
    evidence=channel_evidence(.625,.625,channel_projection(.625,.625))
    evidence['nodes']['u'][field]={'bits_hex':'8000000000000000','float':.1,'fraction':'1/10','hex':'0x1.0p-1','sign_bit':1}[field]
    with pytest.raises(TraceError):validate_evidence(evidence)


@pytest.mark.parametrize('case',['plan','generation','runtime','dependency','dirty'])
def test_compatibility_preparation_fail_closed(monkeypatch,case):
    plan={'source':copy.deepcopy(rb.GENERATION),'parent_queue':None}
    monkeypatch.setattr(rb,'digest',lambda p:rb.PLAN_SHA256 if case!='plan' else '0'*64)
    def snapshot(path):
        if case=='dirty':raise IdentityError('dirty source')
        value=copy.deepcopy(rb.GENERATION)
        if case=='generation':value['commit']='0'*40
        if case=='runtime':value['runtime_sha256']='0'*64
        return value
    monkeypatch.setattr(rb,'source',snapshot)
    monkeypatch.setattr(rb,'worktree_inventory',lambda p: {'engine.py':str(p)} if case=='dependency' else {})
    with pytest.raises(IdentityError):rb.prepare(plan,Path('/historical'))


@pytest.mark.parametrize('commit',['this-is-not-a-git-commit','f'*40,False,None])
def test_compatibility_does_not_relabel_generation(commit):
    context=rb.Readback(Path('/missing'),rb.GENERATION,rb.GENERATION,[])
    with pytest.raises(IdentityError):context.verify_manifest({'code_commit':commit})


def test_generation_drift_before_receipt_rejects(monkeypatch):
    context=rb.Readback(Path('/historical'),rb.GENERATION,rb.GENERATION,[])
    monkeypatch.setattr(rb,'source',lambda p:{})
    with pytest.raises(IdentityError):context.receipt()


@pytest.mark.parametrize('commit',['not-a-commit','A'*40,'a'*39,None,True])
def test_original_strict_identity_parser_unchanged(commit):
    with pytest.raises(IdentityError):ident.verify_source_identity({'code_commit':commit})
