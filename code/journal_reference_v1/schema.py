"""Closed schemas, frozen constants and primary/derived state (F-06,24..28,30)."""
from dataclasses import dataclass
import copy
import hashlib
import json
import math
from pathlib import Path
import yaml

CONTRACT = Path(__file__).parent / 'contract'
C6_CONTRACT = Path(__file__).parent / 'contract_c6'
PARAMETER_SHA256 = 'e22fceab6edcb99de00d04e4ef547e813bb05ce4f296cf4594ad59bc69196a86'
SPEC_SHA256 = '6000a98f2fc6451522b56f932ab93f4a36a1e8947301c871a5951bce55a7fb70'
raw = (C6_CONTRACT / 'PARAMETER_TABLE_R1C6.yaml').read_bytes()
if hashlib.sha256(raw).hexdigest() != PARAMETER_SHA256:
    raise RuntimeError('Frozen C6 parameter bytes differ')
if hashlib.sha256((C6_CONTRACT / 'MODEL_SPEC_JOURNAL_V1_R1C6.md').read_bytes()).hexdigest() != SPEC_SHA256:
    raise RuntimeError('Frozen C6 specification bytes differ')
REGISTRY = yaml.safe_load(raw)
C = REGISTRY['constants']
K = tuple(REGISTRY['enums']['value_keys_order'])
SPEC_ID = REGISTRY['specification_id']
SCHEMA_ID = REGISTRY['schema_id']
U1_ID = 'EMBORA-U1-ADDENDUM-2026-10-04-C6-v1.1-v1.0'
NUMERIC_POLICY_ID = 'EMBORA-NUMERIC-2026-10-04-C6-v1.1'
EVIDENCE_ID = 'EMBORA-NUMERIC-EVIDENCE-2026-10-04-C6-v1.1'


def ordered_sum(terms):
    total = 0.
    for term in terms:
        total = total + term
    return total

class ContractError(ValueError):
    """Malformed input; never replace an invalid value with a fallback."""
class ConfigError(ContractError): pass
class PayloadError(ContractError): pass
class StateError(ContractError): pass
class ActionError(ContractError): pass
class TraceError(ContractError): pass
class UpdateError(ContractError): pass
class ScopeError(ContractError): pass


def canonical(data):
    return json.dumps(data, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)


def assert_exact_tree(actual, expected, error=TraceError):
    """Closed structural types and exact rounded values, including zero sign."""
    if type(expected) is dict:
        keys(actual, expected, error)
        for key in expected: assert_exact_tree(actual[key], expected[key], error)
    elif type(expected) is list:
        if type(actual) is not list or len(actual) != len(expected): raise error('Trace array mismatch')
        for a,b in zip(actual,expected): assert_exact_tree(a,b,error)
    elif type(expected) is float:
        if real(actual,error=error).hex() != expected.hex(): raise error('Rounded scalar/zero-sign mismatch')
    elif type(actual) is not type(expected) or actual != expected:
        raise error('Exact trace value/type mismatch')


def parse_json(text):
    def unique(pairs):
        out = {}
        for k, v in pairs:
            if k in out: raise ContractError('Duplicate JSON key: ' + k)
            out[k] = v
        return out
    def invalid(s): raise ContractError('Nonfinite JSON: ' + s)
    return json.loads(text, object_pairs_hook=unique, parse_constant=invalid)


def keys(obj, expected, error=ContractError):
    if type(obj) is not dict or set(obj) != set(expected):
        raise error(f'Expected exactly keys {sorted(expected)}')


def real(x, lo=-math.inf, hi=math.inf, error=ContractError):
    try:
        valid = type(x) in (int, float) and math.isfinite(x) and lo <= x <= hi
        value = float(x) if valid else None
    except (OverflowError, ValueError, TypeError):
        valid = False
    if not valid:
        raise error('Expected finite real in declared domain')
    return value


def integer(x, lo, hi, error=ContractError):
    if type(x) is not int or not lo <= x <= hi:
        raise error('Expected integer in declared domain (Boolean forbidden)')
    return x


def enum(x, allowed, error=ContractError):
    if type(x) is not str or x not in allowed:
        raise error('Unknown or missing enum: ' + repr(x))
    return x


def clip(lo, hi, x): return min(hi, max(lo, x))


def vector(obj, lo=0, hi=1, positive=False):
    keys(obj, K, StateError)
    values = tuple(real(obj[k], lo, hi, StateError) for k in K)
    if positive and any(v <= 0 for v in values): raise StateError('Priority must be positive')
    return values


def mapping(values): return dict(zip(K, values))


@dataclass(frozen=True)
class State:
    v: tuple
    d: tuple
    p: tuple
    m: float
    f: float
    personality: str
    intensity: str

    def __post_init__(self):
        for v in (self.v, self.d, self.p):
            if type(v) is not tuple or len(v) != 4: raise StateError('Immutable K-vector required')
        for v in self.v: real(v, 0, 1, StateError)
        for d in self.d:
            if real(d, 1, 1, StateError) != 1: raise StateError('d is singleton 1')
        for p in self.p:
            if real(p, error=StateError) <= 0: raise StateError('Nonpositive priority')
        real(self.m, -.5, .5, StateError); real(self.f, 0, 1, StateError)
        enum(self.personality, REGISTRY['personality_map'], StateError)
        enum(self.intensity, REGISTRY['intensity_map'], StateError)
        for field in ('v','d','p'):
            object.__setattr__(self,field,tuple(float(x) for x in getattr(self,field)))
        object.__setattr__(self,'m',float(self.m)); object.__setattr__(self,'f',float(self.f))

    @classmethod
    def from_primary(cls, primary, personality, intensity):
        keys(primary, ('v', 'd', 'p', 'm', 'f'), StateError)
        return cls(vector(primary['v']), vector(primary['d'], 1, 1),
                   vector(primary['p'], positive=True, hi=math.inf),
                   real(primary['m'], -.5, .5, StateError), real(primary['f'], 0, 1, StateError),
                   personality, intensity)

    @property
    def p_clip(self): return tuple(clip(C['p_min'], C['p_max'], p) for p in self.p)
    @property
    def pbar(self):
        p = self.p_clip
        return tuple(x / ordered_sum(p) for x in p)  # F-06, fixed K
    @property
    def r(self): return 1 - self.f  # F-24
    @property
    def W(self): return ordered_sum(p * v for p, v in zip(self.pbar, self.v))  # F-25
    @property
    def Wtilde(self): return clip(C['wellbeing_min'], C['wellbeing_max'], 2 * self.W - 1)  # F-26
    @property
    def S(self): return C['lambda_W'] * self.Wtilde + C['lambda_m'] * self.m - C['lambda_f'] * self.f  # F-27
    @property
    def chi1(self): return REGISTRY['personality_map'][self.personality]
    @property
    def chi2(self): return REGISTRY['intensity_map'][self.intensity]

    def primary(self):
        return {'v': mapping(self.v), 'd': mapping(self.d), 'p': mapping(self.p), 'm': self.m, 'f': self.f}

    def to_dict(self):
        return {**self.primary(), 'personality': self.personality, 'intensity': self.intensity,
                'pbar': mapping(self.pbar), 'r': self.r, 'W': self.W, 'Wtilde': self.Wtilde, 'S': self.S}

    @classmethod
    def from_dict(cls, data):
        keys(data, ('v', 'd', 'p', 'm', 'f', 'personality', 'intensity', 'pbar', 'r', 'W', 'Wtilde', 'S'), StateError)
        state = cls.from_primary({k: data[k] for k in ('v', 'd', 'p', 'm', 'f')}, data['personality'], data['intensity'])
        expected = state.to_dict()
        if tuple(x.hex() for x in vector(data['pbar'])) != tuple(x.hex() for x in state.pbar): raise StateError('Inconsistent derived pbar')
        for field in ('r','W','Wtilde','S'):
            if real(data[field],error=StateError).hex() != float(expected[field]).hex(): raise StateError('Inconsistent derived state: '+field)
        return state

    def project(self, variant):
        enum(variant, REGISTRY['enums']['variant'], StateError)
        return State(self.v, self.d, self.p, 0. if variant == 'no_mood' else self.m,
                     0. if variant == 'no_fatigue' else self.f, self.personality, self.intensity)


def validate_adapter(selection, purpose):
    enum(selection, REGISTRY['adapter_contract']['context_matrix'], ConfigError)
    enum(purpose, REGISTRY['enums']['run_purpose'], ConfigError)
    if purpose not in REGISTRY['adapter_contract']['context_matrix'][selection]:
        raise ConfigError('Adapter forbidden in this run_purpose')


def prepare_config(source):
    """Only YAML-declared defaults may be resolved, before constructor validation."""
    if type(source) is not dict: raise ConfigError('Configuration is an object')
    contract = REGISTRY['effective_config_contract']
    required = set(contract['required_no_default'])
    if not required <= set(source): raise ConfigError('Missing required_no_default field')
    if not set(source) <= required | set(contract['common_default_resolution']): raise ConfigError('Unknown top-level field')
    config = copy.deepcopy(source)
    for key, default in contract['common_default_resolution'].items(): config.setdefault(key, default)
    if type(config['agents']) is not list: raise ConfigError('agents must be a list')
    for a in config['agents']:
        if type(a) is not dict: raise ConfigError('agent must be an object')
        if a.get('controller_type') == 'model':
            for key, default in contract['agent_default_resolution'].items():
                if key != 'initial_primary_state': a.setdefault(key, default)
            if 'initial_primary_state' not in a:
                enum(a['priority_profile'], REGISTRY['priority_profiles'], ConfigError)
                primary = copy.deepcopy(REGISTRY['initial_primary_defaults'])
                primary['p'] = mapping(REGISTRY['priority_profiles'][a['priority_profile']])
                a['initial_primary_state'] = primary
    validate_config(config)
    return config


def validate_config(config):
    contract = REGISTRY['effective_config_contract']
    keys(config, set(contract['required_no_default']) | set(contract['common_default_resolution']), ConfigError)
    if config['schema_id'] != SCHEMA_ID or config['specification_id'] != SPEC_ID: raise ConfigError('Wrong frozen identifiers')
    for k in ('condition_id', 'pair_id'):
        if type(config[k]) is not str or not 1 <= len(config[k]) <= 128: raise ConfigError('Explicit nonempty pair/condition key required')
    enum(config['game'], REGISTRY['enums']['game'], ConfigError)
    integer(config['focal_agent_id'], 1, 2, ConfigError)
    validate_adapter(config['selected_adapter_convention'], config['run_purpose'])
    if config['model_mode'] != 'journal_reference_v1': raise ConfigError('No legacy mode aliases')
    if config['training'] is not False or config['stochastic_mode'] != 'none': raise ConfigError('No training/stochastic execution')
    for k in ('rng_algorithm', 'stream_id', 'replicate_id', 'dqn_config', 'refocus_config'):
        if config[k] is not None: raise ConfigError('Forbidden config: ' + k)
    T = integer(config['horizon'], 1, 100000, ConfigError)
    if config['run_purpose'] != 'structural_fixture' and T not in (100, 200, 400): raise ConfigError('Undeclared horizon')
    if config['run_purpose'] == 'confirmatory_frame' and T != 200: raise ConfigError('Reference horizon required')
    if config['game'] == 'BoS' and config['run_purpose'] == 'confirmatory_frame' and T % 2: raise ConfigError('Odd confirmatory BoS')
    agents = config['agents']
    if type(agents) is not list or len(agents) != 2: raise ConfigError('Exactly two agents')
    for a in agents:
        if type(a) is not dict: raise ConfigError('Agent object required')
        enum(a.get('controller_type'), REGISTRY['enums']['controller_type'], ConfigError)
        expected = set(contract['required_agent_fields']) | (set(contract['model_agent_resolved_fields']) if a['controller_type'] == 'model' else {'baseline_id'})
        keys(a, expected, ConfigError)
        integer(a['agent_id'], 1, 2, ConfigError); integer(a['seat'], 1, 2, ConfigError)
        role = ('proposer' if a['seat'] == 1 else 'responder') if config['game'] == 'UG' else 'player'
        if a['role'] != role: raise ConfigError('Role/seat mismatch')
        if a['controller_type'] == 'model':
            for field, allowed in [('kind', REGISTRY['enums']['model_kind']), ('variant', REGISTRY['enums']['variant']),
                                   ('personality', REGISTRY['personality_map']), ('intensity', REGISTRY['intensity_map']),
                                   ('priority_profile', REGISTRY['priority_profiles'])]: enum(a[field], allowed, ConfigError)
            state = State.from_primary(a['initial_primary_state'], a['personality'], a['intensity'])
            if state.p != tuple(REGISTRY['priority_profiles'][a['priority_profile']]): raise ConfigError('Priority/profile mismatch')
            if config['run_purpose'] != 'structural_fixture':
                expected_primary = copy.deepcopy(REGISTRY['initial_primary_defaults']); expected_primary['p'] = mapping(state.p)
                if state.primary() != expected_primary: raise ConfigError('Nonneutral run initialization forbidden')
        else:
            baseline_key = ('UG_' + role) if config['game'] == 'UG' else config['game']
            enum(a['baseline_id'], REGISTRY['enums']['baseline_id'][baseline_key], ConfigError)
    if {a['agent_id'] for a in agents} != {1, 2} or {a['seat'] for a in agents} != {1, 2}: raise ConfigError('Identities/seats not bijective')
    if next(a for a in agents if a['agent_id'] == config['focal_agent_id'])['controller_type'] != 'model': raise ConfigError('Focal agent must be model')
    return config


def condition_identity(config, frame_id):
    """B03 identity excludes variant; selected adapter and purpose always participate."""
    validate_config(config)
    if type(frame_id) is not str or not frame_id: raise ConfigError('Explicit frame ID required')
    focal = next(a for a in config['agents'] if a['agent_id'] == config['focal_agent_id'])
    other = next(a for a in config['agents'] if a['agent_id'] != config['focal_agent_id'])
    if focal['controller_type'] != 'model': raise ConfigError('Focal agent must be model')
    opponent = other.get('baseline_id')
    if opponent is None:
        opponent = 'model:' + canonical({k: other[k] for k in ('kind', 'personality', 'intensity', 'priority_profile', 'variant', 'initial_primary_state')})
    return (frame_id, config['game'], focal['role'], focal['seat'], focal['personality'], focal['intensity'],
            focal['priority_profile'], opponent, config['horizon'], config['selected_adapter_convention'], config['run_purpose'])
