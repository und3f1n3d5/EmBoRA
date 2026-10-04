"""Audit-only I/R/B/O evidence, independent of the native action computation."""
from fractions import Fraction as Q
import importlib.util
import ctypes
import platform
import sys
import sysconfig
from .schema import *
from .numeric import bits

REFERENCE_SHA256 = '32f3a17610a45a6713222dde013fc1741edcfaa12b1aaf887c8f110a57eae1e8'
path = C6_CONTRACT / 'reference_binary64.py'
if hashlib.sha256(path.read_bytes()).hexdigest() != REFERENCE_SHA256:
    raise RuntimeError('Independent executable oracle hash mismatch')
spec = importlib.util.spec_from_file_location('embora_c6_oracle', path)
oracle = importlib.util.module_from_spec(spec)
spec.loader.exec_module(oracle)
ARITHMETIC_BOUND = 8 * Q(2)**-52 / oracle.EB
_qualification = None


def check_fp_controls():
    # Linux FE_TONEAREST == 0; unqualified platforms fail rather than assume.
    if sys.version_info[:3] != (3, 12, 14) or platform.system() != 'Linux' or platform.machine() != 'x86_64':
        raise ContractError('Runtime outside qualified CPython 3.12.14 Linux x86_64 lock')
    if ctypes.CDLL(None).fegetround() != 0:
        raise ContractError('FP rounding mode is not FE_TONEAREST')
    tiny = math.ldexp(1., -1074)
    if tiny == 0. or tiny * 1. != tiny or tiny + tiny != math.ldexp(1., -1073):
        raise ContractError('Gradual underflow/DAZ/FTZ qualification failed')
    if sys.float_info.mant_dig != 53 or sys.float_info.radix != 2:
        raise ContractError('binary64 required')
    flags = str(sysconfig.get_config_var('CFLAGS'))
    if any(x in flags for x in ('-ffast-math', '-Ofast', '-fassociative-math')):
        raise ContractError('Unqualified compiler flags')


def runtime_record():
    check_fp_controls()
    record = {'python': sys.version, 'implementation': platform.python_implementation(),
              'platform': platform.platform(), 'machine': platform.machine(),
              'compiler': platform.python_compiler(), 'cflags': sysconfig.get_config_var('CFLAGS'),
              'float_info': str(sys.float_info), 'rounding_control': 'FE_TONEAREST',
              'gradual_underflow': True, 'ftz_daz_probe': 'PASS',
              'runtime_vector_qualification': qualify_runtime(),
              'reference_sha256': REFERENCE_SHA256,
              'dependency_lock_sha256': hashlib.sha256((Path(__file__).parent/'requirements.lock').read_bytes()).hexdigest()}
    return record


def qualify_runtime():
    """Qualify native scalar nodes and the runtime accumulator, without episodes."""
    global _qualification
    if _qualification is not None: return copy.deepcopy(_qualification)
    from .numeric import channel_projection
    scalar = parse_json((C6_CONTRACT/'ORACLE_FIXTURES_C6.json').read_text())
    signed = parse_json((C6_CONTRACT/'SIGNED_ZERO_FIXTURES_C6.json').read_text())['fixtures']
    votes = parse_json((C6_CONTRACT/'F35_FIXTURES_C6.json').read_text())
    for row in scalar + signed:
        actual = channel_projection(row['rounded_inputs']['v']['float'],row['rounded_inputs']['q']['float'])
        if actual['identity'] is not row['nodes']['identity']: raise ContractError('Runtime identity qualification failed')
        for key,value in actual['nodes'].items(): assert_exact_tree(value,row['nodes'][key],ContractError)
    for row in votes:
        terms = [p*z for p,z in zip(row['p'],row['z'])]
        exact_n = float(oracle.rn(sum(map(Q.from_float,terms),Q(0))))
        exact_p = float(oracle.rn(sum(map(Q.from_float,row['p']),Q(0))))
        n=math.fsum(terms);p=math.fsum(row['p'])
        if bits(n)!=bits(exact_n) or bits(p)!=bits(exact_p) or bits(n/p)!=row['D']['bits_hex']:
            raise ContractError('Runtime math.fsum qualification failed')
    _qualification = {'status':'PASS','scalar_vectors':len(scalar),'signed_zero_vectors':len(signed),
                      'accumulator_vectors':len(votes), 'episodes_executed':0,
                      'fixture_sha256':{name:hashlib.sha256((C6_CONTRACT/name).read_bytes()).hexdigest()
                                        for name in ('ORACLE_FIXTURES_C6.json','SIGNED_ZERO_FIXTURES_C6.json','F35_FIXTURES_C6.json')}}
    return copy.deepcopy(_qualification)


def runtime_hash():
    return hashlib.sha256(canonical(runtime_record()).encode()).hexdigest()


def compare_continuous(observed, expected):
    observed = real(observed); expected = real(expected)
    difference = abs(observed - expected)
    if difference > max(1e-12, 1e-12 * max(abs(observed), abs(expected))):
        raise TraceError('O minus B exceeds unchanged absolute/relative tolerance 1e-12')
    return difference


def rational_record(value):
    return {'exact_rational': str(value), 'binary64_display': float(value),
            'display_role': 'rounded_display_only'}


def channel_evidence(v, q, observed, ideal=None, origin='derived_binary64_ideal_unknown'):
    """Unknown actual I remains absent. Explicit known tokens must round to inputs."""
    if origin not in ('derived_binary64_ideal_unknown', 'binary64_hex_designated', 'exact_decimal_or_rational_known'):
        raise TraceError('Unknown numeric input origin')
    v = real(v, 0, 1); q = real(q, 0, 1)
    expected = oracle.graph(v, q)
    rb = oracle.real(Q.from_float(v), Q.from_float(q), oracle.AB, oracle.EB)[2]
    b = expected['u']; arith = b - rb
    if abs(arith) > ARITHMETIC_BOUND or abs(b) > oracle.AB + ARITHMETIC_BOUND:
        raise TraceError('Independent arithmetic/urgency bound failure')
    if not 0 <= expected['current'] <= 1 or abs(b) > 1:
        raise TraceError('Executable range invariant failure')
    keys(observed, ('identity', 'nodes', 'current', 'delta', 'u', 'u_abs'), TraceError)
    keys(observed['nodes'], expected['ieee_nodes'], TraceError)
    checks = {'endpoint_signs':'PASS','urgency_range':'PASS','vhat_range':'PASS'}
    if (v == 0 and expected['delta'] < 0) or (v == 1 and expected['delta'] > 0):
        raise TraceError('Impossible endpoint delta sign')
    for name, node in expected['ieee_nodes'].items():
        if canonical(observed['nodes'][name]) != canonical(node):
            raise TraceError('Prescribed intermediate IEEE node mismatch: ' + name)
    if observed['identity'] is not expected['identity']:
        raise TraceError('Exact identity branch mismatch')
    for name in ('current', 'delta', 'u', 'u_abs'):
        o = real(observed[name]); target = float(expected[name])
        compare_continuous(o, target)
        if bits(o) != expected['ieee_nodes'][name]['bits_hex']:
            raise TraceError('Exact output bit invariant failure')
        checks[name] = 'PASS'
    record = {'numeric_policy_id': NUMERIC_POLICY_ID, 'specification_id': SPEC_ID,
              'parameter_schema_id': SCHEMA_ID, 'runtime_lock_sha256': runtime_hash(),
              'input_origin': origin, 'executable_reference_sha256': REFERENCE_SHA256,
              'implementation_reference_comparison': 'PASS', 'exact_invariant_checks': checks,
              'ideal_input_known': ideal is not None,
              'rounded_inputs': {'v': expected['ieee_nodes']['v'], 'q': expected['ieee_nodes']['q']},
              'nodes': expected['ieee_nodes'] | {'identity': expected['identity']},
              'real_on_rounded_R': rational_record(rb), 'executable_B': expected['ieee_nodes']['u'],
              'arithmetic_residual_B_minus_R': rational_record(arith),
              'independently_derived_bounds': {'arithmetic': rational_record(ARITHMETIC_BOUND)},
              'observed_O': observed['u'], 'implementation_discrepancy_O_minus_B': observed['u']-float(b),
              'absolute_tolerance_1e-12': 1e-12, 'relative_tolerance_1e-12': 1e-12,
              'exact_categories': {'identity': expected['identity'], 'delta_sign': (expected['delta']>0)-(expected['delta']<0)}}
    if ideal is None:
        if origin == 'exact_decimal_or_rational_known': raise TraceError('Known origin requires original tokens')
        record['actual_ideal_status'] = 'unavailable_no_known_preconversion_state'
    else:
        if origin != 'exact_decimal_or_rational_known': raise TraceError('Actual ideal prohibited for unknown origin')
        keys(ideal, ('v', 'q'), TraceError)
        if any(type(ideal[k]) is not str for k in ideal): raise TraceError('Exact original tokens/rationals required')
        vi, qi = Q(ideal['v']), Q(ideal['q'])
        if not (0 <= vi <= 1 and 0 <= qi <= 1) or bits(float(ideal['v']) if '/' not in ideal['v'] else float(vi)) != bits(v) or bits(float(ideal['q']) if '/' not in ideal['q'] else float(qi)) != bits(q):
            raise TraceError('Exact-token lineage does not match rounded inputs')
        iv = oracle.real(vi, qi)[2]
        emin = min(oracle.EPS, oracle.EB); amax = max(oracle.A, oracle.AB)
        bound = abs(oracle.AB-oracle.A)/emin + amax*abs(Q.from_float(q)-qi)/emin + amax*abs(Q.from_float(v)-vi)*(1/emin+1/emin**2) + amax*abs(oracle.EB-oracle.EPS)/emin**2
        inp = rb-iv; total = b-iv
        if abs(inp)>bound or abs(total)>bound+ARITHMETIC_BOUND:
            raise TraceError('Independent input/total bound failure')
        record.update(ideal_I=rational_record(iv), input_residual_R_minus_I=rational_record(inp),
                      total_residual_B_minus_I=rational_record(total),
                      original_exact_tokens=ideal | {'alpha': '0.35', 'epsilon': '0.000001'})
        record['independently_derived_bounds'].update(input=rational_record(bound), total=rational_record(bound+ARITHMETIC_BOUND))
    return record


def validate_evidence(data):
    """Strict replay of the evidence object rejects extras and false diagnostics."""
    if type(data) is not dict: raise TraceError('Evidence object required')
    try:
        v = data['rounded_inputs']['v']['float']; q = data['rounded_inputs']['q']['float']
        from .numeric import channel_projection
        ideal = None
        if data.get('ideal_input_known') is True:
            ideal = {k: data['original_exact_tokens'][k] for k in ('v','q')}
        expected = channel_evidence(v, q, channel_projection(v,q), ideal, data['input_origin'])
        if canonical(expected) != canonical(data): raise TraceError('Evidence/schema/diagnostic mismatch')
    except (KeyError, TypeError, ValueError) as exc:
        raise TraceError('Malformed numeric evidence') from exc
