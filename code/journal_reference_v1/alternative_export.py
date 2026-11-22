"""Adopted alternative /4; read-only export through unchanged native admission."""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys
from . import analysis_admission as admission, pap_metrics as m
from .inventory import validate_inventory

VERSION = 'EMBORA-ADMITTED-ALTERNATIVES-C6-v1.1'
ADDENDUM = Path(__file__).with_name('ALT_READOUT4_v1.0.json')
SETTINGS = [('lambda', [w, mood, f]) for w in (.5, 1, 2)
            for mood in (0, .5, 1) for f in (0, .5, 1)] + [
                ('component', k) for k in ('Wtilde', 'm', 'minus_f')]


def pair_readout(full, comparison, axis, setting):
    """Registered mean/reference-cutoff readout; no own-range normalization."""
    m.matched(full, comparison, 'single_switch')
    if (axis, setting) not in SETTINGS:
        raise m.MetricError('Unregistered alternative setting')
    kw = {'weights': setting} if axis == 'lambda' else {'component': setting}
    f = m.alternative_readout(full, **kw)
    c = m.alternative_readout(comparison, **kw)
    dp = m.finite((f['P'] - c['P']) / m.MAX_PAYOFF[full['stratum']])
    dq = m.finite(f['Q'] - c['Q'])
    normalized = dq / 4
    rp, rq = m.rank_sign(dp), m.rank_sign(normalized)
    return dict(delta_Q=dq, normalized_delta_Q=normalized,
                normalized_delta_P=dp, rank_P=rp, rank_Q=rq,
                category=m.tie_category(rp, rq), strict_discordance=int(rp * rq == -1))


def alternatives(base, contrasts):
    """Internal transformation of an admitted result, not an acceptance API."""
    runs = base['metrics']['run_inventory']; rows = []; excluded = []
    cells = {}
    for contrast in contrasts:
        full_id, other_id = contrast['full_run_id'], contrast['comparison_run_id']
        full, other = runs[full_id], runs[other_id]
        # Source configs are supplied below by the admission wrapper even for
        # unavailable episodes. Eligibility never depends on observed effects.
        cfg = contrast['_full_config']
        synthetic = base['kind'] == 'SYNTHETIC_TEST_ONLY'
        eligible = (cfg['run_purpose'] == 'structural_fixture' and cfg['horizon'] <= 8) if synthetic else (
            cfg['horizon'] == 200 and cfg['run_purpose'] == 'confirmatory_frame' and
            cfg['selected_adapter_convention'] == 'normative_resisted_inequity_v1')
        if contrast['contrast_family'] != 'single_switch' or not eligible:
            excluded.append(contrast['contrast_id']); continue
        primary = next(r for r in base['metrics']['pair_metrics'] if r['contrast_id'] == contrast['contrast_id'])
        comparison_cfg = contrast['_comparison_config']
        descriptor = m.focal(comparison_cfg)
        stratum = ('UG-P' if m.focal(cfg)['role'] == 'proposer' else 'UG-R') if cfg['game'] == 'UG' else cfg['game']
        for index, (axis, setting) in enumerate(SETTINGS):
            row = dict(contrast_id=contrast['contrast_id'], full_run_id=full_id,
                       comparison_run_id=other_id, readout_id=f'{axis}-{index:02}',
                       axis=axis, setting=setting, status='UNAVAILABLE', metrics=None)
            if primary['status'] == 'VALID' and full['status'] == other['status'] == 'VALID':
                row.update(status='VALID', metrics=pair_readout(full['metrics'], other['metrics'], axis, setting))
            rows.append(row)
            key = (contrast['block'], stratum, descriptor['variant'], cfg['horizon'],
                   cfg['selected_adapter_convention'], cfg['run_purpose'], row['readout_id'])
            cells.setdefault(key, []).append(row)
    summaries = []
    for key, values in cells.items():
        n = len(values); valid = [v for v in values if v['status'] == 'VALID']
        complete = len(valid) == n
        counts = Counter(v['metrics']['category'] for v in valid)
        summaries.append(dict(cell_key=list(key), N_expected=n, N_valid=len(valid),
            status='COMPLETE' if complete else 'INCOMPLETE',
            D=counts['strict_discordant']/n if complete else None,
            categories={k:dict(count=counts[k], fraction=counts[k]/n) for k in m.CATEGORIES} if complete else None))
    return rows, summaries, excluded


def admitted_export(raw, trusted_hash, protocol, validator_root, python):
    # Actual required native replay, strict source/runtime, whole-group selection
    # and immutable-input checks always run before any normalized output.
    base = admission.admitted_analysis(raw, trusted_hash, protocol, validator_root, python)
    a = admission.parse_json(raw.decode())
    contrasts = [dict(c, _full_config=admission.prepare_config(admission.parse_json(a['config_texts'][c['full_run_id']])),
                        _comparison_config=admission.prepare_config(admission.parse_json(a['config_texts'][c['comparison_run_id']])))
                 for c in a['contrasts']]
    rows, cells, excluded = alternatives(base, contrasts)
    out = dict(schema_id=VERSION, addendum_sha256=admission.sha(ADDENDUM.read_bytes()),
               base_export_sha256=admission.digest(base), admitted_export=base,
               divisor=4, cutoff=1e-9, aggregation='mean', rows=rows, cells=cells,
               excluded_contrast_ids=excluded, experimental_rounds_executed=0)
    validate_inventory('ALTERNATIVES_C6_v1.1.json', out)
    return out


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', choices=('export', 'verify'))
    for name in ('admission', 'admission-sha256', 'protocol', 'validator-source', 'python', 'output'):
        p.add_argument('--'+name, required=True)
    args = p.parse_args(argv)
    try:
        raw = Path(args.admission).read_bytes()
        out = admitted_export(raw, args.admission_sha256, Path(args.protocol).read_bytes(), args.validator_source, args.python)
        if args.command == 'verify':
            admission.require(admission.canonical(admission.read(args.output)) == admission.canonical(out), 'Alternative export mismatch')
        else:
            admission.write_export(args.output, out, admission.parse_json(raw.decode()))
        print(admission.canonical(dict(schema_id=VERSION, status=out['admitted_export']['status'], experimental_rounds_executed=0)))
        return 0 if out['admitted_export']['status'] == 'COMPLETE' else 2
    except (ValueError, OSError, KeyError, TypeError, AssertionError) as e:
        print(json.dumps(dict(status='FAIL', error_type=type(e).__name__, message=str(e))), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
