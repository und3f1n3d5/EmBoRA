"""Focused synthetic readout + real saved native replay + temporary retention I/O."""
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile
import pytest
from journal_reference_v1 import alternative_export as x, archive_ops as ops
from journal_reference_v1.metric_tests.test_pap_metrics import config, records


def pair(delta, pay=5):
    f, c = config(), config(variant='no_mood')
    ef = x.m.episode_metrics(f, records(f, [pay]*4, [delta]*4))
    ec = x.m.episode_metrics(c, records(c, [0]*4, [0]*4))
    return ef, ec


@pytest.mark.parametrize('raw,rank', [(0., 0), (4e-9, 0), (-4e-9, 0),
    (math.nextafter(4e-9, math.inf), 1), (math.nextafter(-4e-9, -math.inf), -1),
    (math.nextafter(4e-9, 0), 0), (math.nextafter(-4e-9, 0), 0)])
def test_divisor4_exact_boundary(raw, rank):
    f, c = pair(raw)
    result = x.pair_readout(f, c, 'component', 'Wtilde')
    assert result['normalized_delta_Q'] == raw/4 and result['rank_Q'] == rank
    assert result['strict_discordance'] == int(rank == -1)


def test_all_settings_and_primary_repeat_and_minus_f():
    f, c = pair(-2)
    for axis, setting in x.SETTINGS:
        d = x.pair_readout(f, c, axis, setting)
        assert d['normalized_delta_Q'] == d['delta_Q']/4
    assert len(x.SETTINGS) == 30
    # Behavioral unit lambdas are (1,1,1). Nonzero components prevent a vacuous
    # primary-repeat test on mood=fatigue=0.
    for state in f['series']['states']:
        state.update(m=.5, f=.25, S=-1.75)
    f['Q'] = -1.75
    assert x.pair_readout(f, c, 'lambda', [1, 1, 1])['normalized_delta_Q'] == x.m.pair_metrics(f, c)['normalized_delta_Q']
    for state in f['series']['states']:
        state['f'] = 0
    f['series']['states'][0]['f'] = 1
    assert x.pair_readout(f, c, 'component', 'minus_f')['normalized_delta_Q'] == -.0625
    with pytest.raises(ValueError): x.pair_readout(f, c, 'lambda', [4, 1, 1])
    with pytest.raises(ValueError): x.pair_readout(f, c, 'lambda', [True, .5, .5])


@pytest.mark.parametrize('pay,delta,category', [(0, 0, 'both_tied'), (0, 1, 'payoff_only_tied'),
    (5, 0, 'state_only_tied'), (5, 1, 'strict_concordant'), (5, -1, 'strict_discordant')])
def test_five_categories(pay, delta, category):
    assert x.pair_readout(*pair(delta, pay), 'component', 'Wtilde')['category'] == category


@pytest.fixture
def saved_admission(tmp_path):
    root = Path(os.environ['EMBORA_PRE_RENT_ROOT'])
    a = x.admission
    spec = json.loads((root/'owner_ce01/applicable_cli/admission.json').read_text())
    originals = root/'accepted_ce01/independent_64_case_inputs/test_integrated_native_whole_g0'
    for variant, source in spec['sources'].items():
        target = tmp_path/variant
        shutil.copytree(originals/variant, target)
        source.update(path=str(target), inventory_sha256=a.digest(a.files_digest(target)))
    spec['analysis_source'] = a.snapshot(Path(x.__file__).resolve().parents[2])
    return spec, root


def export(spec, root):
    raw = (x.admission.canonical(spec)+'\n').encode()
    return x.admitted_export(raw, x.admission.sha(raw), (root/'PAP.md').read_bytes(), root/'validator', root/'qualified-python')


def test_actual_admitted_export_and_missing_full_and_semantic_rejection(saved_admission, tmp_path):
    spec, root = saved_admission
    out = export(spec, root)
    assert out['admitted_export']['status'] == 'COMPLETE'
    assert len(out['rows']) == 150 and len(out['cells']) == 150
    assert all(r['status'] == 'VALID' for r in out['rows'])
    assert all(v['invocation']['exit_code'] == 0 and v['result']['status'] == 'PASS'
               for v in out['admitted_export']['native_validation'].values())
    assert out['experimental_rounds_executed'] == 0
    assert out['admitted_export']['alternatives']['normalized_delta_Q'] is None
    for row in out['rows']:
        if row['axis'] == 'lambda' and row['setting'] == [1, 1, 1]:
            primary = next(p['metrics'] for p in out['admitted_export']['metrics']['pair_metrics'] if p['contrast_id'] == row['contrast_id'])
            assert row['metrics']['normalized_delta_Q'] == primary['normalized_delta_Q']
    receipt_dir = root/'receipts'; receipt_dir.mkdir(exist_ok=True)
    (receipt_dir/'alternative_positive.json').write_text(x.admission.canonical(out)+'\n')
    # Semantic oracle after admitted extraction: a missing full invalidates all
    # dependent alternatives and all-cell denominators stay unchanged.
    base = copy.deepcopy(out['admitted_export']); base['metrics']['run_inventory']['registered-full'] = dict(status='MISSING', reason='ARTIFACT_INCOMPLETE')
    cs = [dict(c, _full_config=x.admission.prepare_config(x.admission.parse_json(spec['config_texts'][c['full_run_id']])),
                   _comparison_config=x.admission.prepare_config(x.admission.parse_json(spec['config_texts'][c['comparison_run_id']]))) for c in spec['contrasts']]
    rows, cells, _ = x.alternatives(base, cs)
    assert all(r['metrics'] is None and r['status'] == 'UNAVAILABLE' for r in rows)
    assert all(c['N_expected'] == 1 and c['N_valid'] == 0 and c['D'] is None for c in cells)
    # Rehash corrupted content: actual native semantic replay must reject it.
    p = Path(spec['sources']['full']['path']); rounds = x.admission.read(p/'rounds.json')
    rounds[0]['post_states_by_seat'][1]['S'] += .1
    (p/'rounds.json').write_text(x.admission.canonical(rounds)+'\n')
    hashes = x.admission.read(p/'artifact_hashes.json'); hashes['rounds.json'] = x.admission.sha((p/'rounds.json').read_bytes())
    (p/'artifact_hashes.json').write_text(x.admission.canonical(hashes)+'\n')
    spec['sources']['full']['inventory_sha256'] = x.admission.digest(x.admission.files_digest(p))
    with pytest.raises(ValueError, match='Native strict validation rejected'): export(spec, root)


def test_alternative_cli_export_verify_and_changed_export_reject(saved_admission, tmp_path):
    spec, root = saved_admission; a = x.admission
    ap = tmp_path/'admission.json'; ap.write_text(a.canonical(spec)+'\n')
    output = tmp_path/'alternatives.json'
    command = [str(root/'qualified-python'), '-m', 'journal_reference_v1.alternative_export']
    options = ['--admission', str(ap), '--admission-sha256', a.sha(ap.read_bytes()), '--protocol', str(root/'PAP.md'),
               '--validator-source', str(root/'validator'), '--python', str(root/'qualified-python'), '--output', str(output)]
    invocations = []
    for action, expected in [('export', 0), ('verify', 0), ('verify', 2)]:
        if expected == 2:
            changed = a.read(output); changed['rows'][0]['metrics']['normalized_delta_Q'] = 99
            output.write_text(a.canonical(changed)+'\n')
        argv = command+[action]+options
        p = subprocess.run(argv, cwd=Path(x.__file__).resolve().parents[2], capture_output=True, text=True)
        invocations.append(dict(argv=argv, cwd=str(Path.cwd()), exit=p.returncode, stdout=p.stdout, stderr=p.stderr))
        assert p.returncode == expected, p.stderr
    (root/'receipts/alternative_cli.json').write_text(json.dumps(invocations, indent=2)+'\n')


@pytest.mark.parametrize('mutation', ['trust', 'identity', 'authority', 'schema', 'native_hash'])
def test_export_rejects_through_existing_provenance(saved_admission, mutation):
    spec, root = saved_admission; p = Path(spec['sources']['full']['path'])
    if mutation == 'trust':
        raw = x.admission.canonical(spec).encode()
        with pytest.raises(ValueError): x.admitted_export(raw, 'f'*64, (root/'PAP.md').read_bytes(), root/'validator', root/'qualified-python')
        return
    if mutation == 'native_hash':
        spec['sources']['full']['inventory_sha256'] = 'f'*64
    else:
        m = x.admission.read(p/'manifest.json')
        if mutation == 'identity': m['code_commit'] = 'f'*40
        elif mutation == 'authority': m['administrative_authority']['full_runs_authorized'] = True
        else: m['original_config']['horizon'] = True
        (p/'manifest.json').write_text(x.admission.canonical(m)+'\n')
        hashes = x.admission.read(p/'artifact_hashes.json'); hashes['manifest.json'] = x.admission.sha((p/'manifest.json').read_bytes())
        (p/'artifact_hashes.json').write_text(x.admission.canonical(hashes)+'\n')
        spec['sources']['full']['inventory_sha256'] = x.admission.digest(x.admission.files_digest(p))
    with pytest.raises(ValueError): export(spec, root)


@pytest.fixture
def archived(tmp_path):
    source = tmp_path/'raw'; source.mkdir(); (source/'nested').mkdir(); (source/'empty-dir').mkdir()
    (source/'nested/данные.bin').write_bytes(bytes(range(256))*2048)
    (source/'empty').write_bytes(b''); (source/'failure.json').write_bytes(b'{"status":"FAILED","cause":"synthetic"}\r\n')
    archive, manifest = tmp_path/'native.zip', tmp_path/'manifest.json'
    original = ops.inventory(source)
    ops.pack(source, archive, manifest, 'SYNTHETIC_TEST_ONLY', 0)
    restored, rr = tmp_path/'restored', tmp_path/'restore.json'
    ops.restore(archive, manifest, restored, rr, 0)
    return dict(source=source, archive=archive, manifest_path=manifest, restored=restored, restore_receipt=rr), original


def test_lossless_deflate_restore_and_gated_cleanup(archived, tmp_path):
    args, original = archived
    assert ops.inventory(args['source']) == ops.inventory(args['restored']) == original
    with zipfile.ZipFile(args['archive']) as z:
        assert all(i.compress_type == zipfile.ZIP_DEFLATED for i in z.infolist())
    # Merely copying/archiving never creates a confirmation.
    with pytest.raises(FileNotFoundError):
        ops.cleanup(**args, confirmation=tmp_path/'absent', trusted_confirmation_sha256='f'*64,
                    receipt=tmp_path/'cleanup.json', acknowledge=True)
    assert args['source'].is_dir() and args['restored'].is_dir()
    ext = tmp_path/'SYNTHETIC_EXTERNAL_COPY'; ext.mkdir()
    shutil.copyfile(args['archive'], ext/'native.zip'); shutil.copyfile(args['manifest_path'], ext/'manifest.json')
    ops.restore(ext/'native.zip', ext/'manifest.json', ext/'readback', ext/'restore.json')
    confirmation = ext/'confirmed.json'
    ops.confirm(ext/'native.zip', ext/'manifest.json', ext/'readback', confirmation, 'SYNTHETIC_TEST_ONLY', True)
    with pytest.raises(ValueError, match='pinned'):
        ops.cleanup(**args, confirmation=confirmation, trusted_confirmation_sha256='f'*64,
                    receipt=tmp_path/'cleanup.json', acknowledge=True)
    result = ops.cleanup(**args, confirmation=confirmation, trusted_confirmation_sha256=ops.hash_file(confirmation),
                         receipt=tmp_path/'cleanup.json', acknowledge=True, remove_archive=True)
    assert result['status'] == 'REDUNDANT_COPIES_REMOVED' and not args['source'].exists() and not args['restored'].exists()
    assert not args['archive'].exists() and ops.inventory(ext/'readback') == original
    assert args['manifest_path'].is_file() and (tmp_path/'cleanup.json.intent.json').is_file()


@pytest.mark.parametrize('mutation', ['missing', 'extra', 'tampered'])
def test_damaged_archive_rejects(archived, tmp_path, mutation):
    args, _ = archived; p = args['archive']; m = ops.read(args['manifest_path'])
    with zipfile.ZipFile(p) as z: files = {n:z.read(n) for n in z.namelist()}
    if mutation == 'missing': files.pop('empty')
    elif mutation == 'extra': files['extra'] = b'!'
    else: files['failure.json'] = b'false COMPLETE'
    p.unlink()
    with zipfile.ZipFile(p, 'x', compression=zipfile.ZIP_DEFLATED) as z:
        for n, data in files.items(): z.writestr(n, data)
    # Rehashed transport still fails exact payload semantics.
    m.update(archive_sha256=ops.hash_file(p), archive_bytes=p.stat().st_size)
    with pytest.raises(ValueError): ops.verify_archive(p, m)


def test_space_shortfall_stops_without_outputs(tmp_path):
    p = tmp_path/'raw'; p.mkdir(); (p/'payload').write_bytes(b'data')
    with pytest.raises(ValueError, match='Insufficient free space'):
        ops.pack(p, tmp_path/'a.zip', tmp_path/'m.json', 'SYNTHETIC_TEST_ONLY', 10**30)
    assert not (tmp_path/'a.zip').exists() and not (tmp_path/'m.json').exists()
    assert (p/'payload').read_bytes() == b'data'


def test_restore_shortfall_preserves_archive(archived, tmp_path):
    args, _ = archived; before = ops.hash_file(args['archive'])
    with pytest.raises(ValueError, match='Insufficient free space'):
        ops.restore(args['archive'], args['manifest_path'], tmp_path/'denied', tmp_path/'denied.json', 10**30)
    assert not (tmp_path/'denied').exists() and ops.hash_file(args['archive']) == before


def test_unsafe_source_and_unconfirmed_original_reject(archived, tmp_path):
    args, _ = archived
    with pytest.raises(ValueError): ops.confirm(args['archive'], args['manifest_path'], args['restored'], tmp_path/'c.json', 'original', True)
    link = args['source']/'link'; link.symlink_to(args['source']/'failure.json')
    with pytest.raises(ValueError, match='Symlink'): ops.inventory(args['source'])


@pytest.mark.parametrize('mutation', ['no_ack', 'wrong_batch', 'changed_working', 'missing_copy', 'hardlink'])
def test_cleanup_retains_data_when_confirmation_invariants_fail(archived, tmp_path, mutation):
    args, _ = archived; ext = tmp_path/'external'; ext.mkdir()
    shutil.copyfile(args['archive'], ext/'copy.zip')
    ops.restore(ext/'copy.zip', args['manifest_path'], ext/'readback', ext/'restore.json')
    conf = ext/'confirm.json'
    ops.confirm(ext/'copy.zip', args['manifest_path'], ext/'readback', conf, 'SYNTHETIC_TEST_ONLY', True)
    if mutation == 'wrong_batch':
        c = ops.read(conf); c['batch_id'] = 'other'; conf.write_text(ops.canonical(c)+'\n')
    elif mutation == 'changed_working': (args['source']/'failure.json').unlink()
    elif mutation == 'missing_copy': (ext/'copy.zip').unlink()
    elif mutation == 'hardlink':
        (ext/'copy.zip').unlink(); os.link(args['archive'], ext/'copy.zip')
    with pytest.raises((ValueError, OSError)):
        ops.cleanup(**args, confirmation=conf, trusted_confirmation_sha256=ops.hash_file(conf),
                    receipt=tmp_path/'cleanup.json', acknowledge=mutation != 'no_ack', remove_archive=True)
    assert args['source'].exists() and args['restored'].exists() and args['archive'].exists()
