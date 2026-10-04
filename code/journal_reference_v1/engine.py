"""F-29 atomic rounds and complete private logs; P2 administrative scope separate from enum validity."""
from dataclasses import dataclass
import subprocess
from .schema import *
from .games import Adapter, Result, observation, execute, validate_action
from .model import Agent


@dataclass(frozen=True)
class P2ConformanceAuthority:
    decision_record_id: str
    acceptance_test_id: str
    episode_id: str

    def validate(self, config):
        if self.decision_record_id != U1_ID: raise ScopeError('Wrong administrative authority')
        if type(self.acceptance_test_id) is not str or not self.acceptance_test_id.startswith('AT-'): raise ScopeError('Declared acceptance fixture required')
        if type(self.episode_id) is not str or not self.episode_id: raise ScopeError('Explicit fixture episode ID required')
        # A/B vectors are checked via pure adapter/candidate helpers, never trajectories.
        if config['run_purpose'] != 'structural_fixture' or config['horizon'] > 8:
            raise ScopeError('P2 only permits necessary short structural conformance episodes (<=8 rounds); no experimental authority')

    def to_dict(self):
        return {'decision_record_id': self.decision_record_id, 'acceptance_test_id': self.acceptance_test_id,
                'episode_id': self.episode_id, 'work_kind': 'conformance', 'pilot_authorized': False, 'full_runs_authorized': False}


class Engine:
    def __init__(self, effective_config, authority):
        validate_config(effective_config)
        if type(authority) is not P2ConformanceAuthority: raise ScopeError('Explicit administrative authority required')
        authority.validate(effective_config)
        self._config_json = canonical(effective_config)
        self.authority = authority
        self.adapter = Adapter(effective_config['selected_adapter_convention'], effective_config['run_purpose'])
        self.agents = tuple(Agent.construct(effective_config, a['agent_id'], self.adapter) for a in sorted(effective_config['agents'], key=lambda a: a['seat']))
        self.states = tuple(a.initial_state for a in self.agents)
        self._history = []
        self._records = []
        self._failures = []
        self.update_counters = (0, 0)
        self.execution_counter = 0

    @property
    def config(self): return parse_json(self._config_json)
    @property
    def history(self): return copy.deepcopy(self._history)
    @property
    def records(self): return copy.deepcopy(self._records)
    @property
    def failures(self): return copy.deepcopy(self._failures)

    def step(self):
        if self._failures: raise UpdateError('Failed episode cannot resume')
        t = len(self._history) + 1
        if t > self.config['horizon']: raise UpdateError('Episode complete; duplicate round rejected')
        config = self.config
        self.authority.validate(config)
        events = ['validate_config_and_pre_states', 'snapshot_both_pre_states_and_history']
        pre = self.states
        history = self.history
        try:
            # Detect accidental replacement of the run selection before any affected round.
            if any(a.adapter != self.adapter for a in self.agents): raise TraceError('Agent/run adapter mismatch')
            decisions, observations = [], []
            for j, agent in enumerate(self.agents):
                offer = decisions[0]['action']['offer'] if config['game'] == 'UG' and j == 1 else None
                obs = observation(config, agent.descriptor, history, offer)
                observations.append(obs); events.append(f'build_observation_seat_{j+1}')
                payload = {'public_observation': copy.deepcopy(obs), 'own_pre_state': None if pre[j] is None else pre[j].to_dict()}
                before = canonical(payload)
                decision = agent.decide(payload)
                if canonical(payload) != before: raise TraceError('Decision mutated inputs')
                events.append(f'decide_seat_{j+1}')
                # Recompute exact typed trace before execution, not after mutation.
                if canonical(decision) != canonical(agent.decide({'public_observation': obs, 'own_pre_state': None if pre[j] is None else pre[j].to_dict()})): raise TraceError('Invalid returned trace')
                validate_action(config['game'], agent.descriptor['role'], decision['action'])
                decisions.append(decision); events.append(f'validate_decision_seat_{j+1}')
            actions = [d['action'] for d in decisions]
            payoffs = execute(config['game'], actions); events.append('execute_game_once')
            results = tuple(Result.build(config['game'], t, a.descriptor, actions) for a in self.agents)
            # Both immutable results exist before either update computation.
            for result, agent in zip(results, self.agents): result.validate(config, agent.descriptor)
            events.extend(['build_result_seat_1', 'build_result_seat_2'])
            computed = []
            for j, agent in enumerate(self.agents):
                if self.update_counters[j] != t - 1: raise UpdateError('Duplicate/stale update counter')
                computed.append(agent.prepare_update(pre[j], observations[j], decisions[j], results[j], t))
                events.append(f'prepare_update_seat_{j+1}')
            post = tuple(c[0] for c in computed)
            record = {'schema_id': 'EMBORA-PRIVATE-ROUND-C5-P2-v1.0', 'specification_id': SPEC_ID,
                      'condition_id': config['condition_id'], 'pair_id': config['pair_id'], 'episode_id': self.authority.episode_id,
                      'model_mode': 'journal_reference_v1', 'game': config['game'], 'round': t,
                      'selected_adapter_convention': self.adapter.selected_adapter_convention, 'selected_adapter_id': self.adapter.adapter_id,
                      'run_purpose': config['run_purpose'], 'administrative_authority': self.authority.to_dict(),
                      'agent_descriptors_by_seat': [a.descriptor for a in self.agents], 'observations_by_seat': observations,
                      'pre_states_by_seat': [None if s is None else s.to_dict() for s in pre], 'decisions_by_seat': decisions,
                      'actions_by_seat': actions, 'payoffs_by_seat': list(payoffs), 'results_by_seat': [r.to_dict() for r in results],
                      'updates_by_seat': [c[1] for c in computed], 'post_states_by_seat': [None if s is None else s.to_dict() for s in post],
                      'intervention': {'target_agent_id': config['focal_agent_id'], 'variant': next(a['variant'] for a in config['agents'] if a['agent_id'] == config['focal_agent_id'] and a['controller_type'] == 'model')},
                      'event_order': events + ['atomic_commit_both_states_history_and_log'],
                      'event_counters': {'game_executions_this_round': 1, 'updates_this_round_by_seat': [1, 1], 'total_game_executions': self.execution_counter + 1,
                                         'total_updates_by_seat': [n + 1 for n in self.update_counters]}, 'failure_status': None}
            canonical(record)  # validate finite, serializable complete record before commit
            new_history = history + [{'round': t, 'actions_by_seat': copy.deepcopy(actions), 'payoffs_by_seat': list(payoffs)}]
            new_records = self._records + [copy.deepcopy(record)]
            self.states, self._history, self._records, self.update_counters, self.execution_counter = post, new_history, new_records, tuple(n + 1 for n in self.update_counters), self.execution_counter + 1
            return copy.deepcopy(record)
        except Exception as error:
            self._failures.append({'round': t, 'error_type': type(error).__name__, 'reason': str(error), 'events_before_failure': events,
                                   'effective_config': config, 'pre_states_by_seat': [None if s is None else s.to_dict() for s in pre],
                                   'history_before_failure': history, 'committed': False})
            raise

    def run(self):
        while len(self._history) < self.config['horizon']: self.step()
        return self.records

    def manifest(self, original_config):
        cfg = self.config
        if canonical(prepare_config(original_config)) != canonical(cfg): raise ConfigError('Original/effective config mismatch')
        root = Path(__file__).resolve().parents[2]
        def git(*args):
            return subprocess.check_output(['git', '-C', str(root), *args], text=True).strip()
        lock = Path(__file__).parent / 'requirements.lock'
        hashes = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in sorted(Path(__file__).parent.rglob('*')) if p.is_file() and p.suffix in ('.py', '.yaml', '.md', '.csv', '.json', '.lock') and '__pycache__' not in p.parts}
        return {'schema_id': 'EMBORA-MANIFEST-C5-P2-v1.0', 'specification_id': SPEC_ID, 'parameter_schema_id': SCHEMA_ID,
                'original_config': copy.deepcopy(original_config), 'effective_config': cfg,
                'constants_and_enum_versions': copy.deepcopy(REGISTRY), 'u1_decision_record_id': U1_ID,
                'c4_author_decision_id': 'Drive file 1OLKGRr1ebA3Mi2I_YIqpyrG2MwGpBdAo (historical source; live authority U1 C5)',
                'spec_sha256': SPEC_SHA256, 'parameter_sha256': PARAMETER_SHA256,
                'selected_adapter_convention': self.adapter.selected_adapter_convention, 'selected_adapter_id': self.adapter.adapter_id,
                'source_initial_states_by_seat': [None if a.initial_source_state is None else a.initial_source_state.to_dict() for a in self.agents],
                'effective_initial_states_by_seat': [None if a.initial_state is None else a.initial_state.to_dict() for a in self.agents],
                'code_commit': git('rev-parse', 'HEAD'), 'code_branch': git('branch', '--show-current'), 'dirty_state': git('status', '--porcelain=v1'),
                'source_hashes': hashes, 'code_hash': hashlib.sha256(canonical(hashes).encode()).hexdigest(),
                'dependency_lock_hash': hashlib.sha256(lock.read_bytes()).hexdigest(), 'config_hash': hashlib.sha256(canonical(cfg).encode()).hexdigest(),
                'pairing_and_data_generating_process_descriptor': {'pair_id': cfg['pair_id'], 'mode': 'deterministic', 'active_rng': None, 'sampling_units': 0},
                'administrative_authority': self.authority.to_dict(), 'failure_status': self.failures, 'trajectory_hash': trajectory_hash(self.records)}

    def save(self, destination, original_config):
        destination = Path(destination)
        destination.mkdir(parents=True, exist_ok=False)  # preserve failed/existing artifacts
        for name, data in [('manifest.json', self.manifest(original_config)), ('rounds.json', self.records), ('failures.json', self.failures)]:
            with (destination / name).open('x', encoding='utf-8') as out: out.write(canonical(data) + '\n')


def trajectory_hash(records):
    """F-34 excludes run IDs, labels, streams, timestamps; retains role/action/payoff/state content."""
    contents = [{'game': r['game'], 'roles_by_seat': [a['role'] for a in r['agent_descriptors_by_seat']],
                 'actions_by_seat': r['actions_by_seat'], 'payoffs_by_seat': r['payoffs_by_seat'],
                 'pre_states_by_seat': r['pre_states_by_seat'], 'post_states_by_seat': r['post_states_by_seat']} for r in records]
    return hashlib.sha256(canonical(contents).encode()).hexdigest()


def sampling_unit_ids(draw_descriptors, mode):
    """F-33 fixed-input statistical helper; never a stochastic reference generator."""
    enum(mode, ('deterministic', 'stochastic'))
    if type(draw_descriptors) is not list: raise ContractError('Explicit DGP descriptors required')
    units = []
    for draw in draw_descriptors:
        keys(draw, ('draw_id', 'independent_cluster_id'), ContractError)
        for k in draw:
            if type(draw[k]) is not str or not draw[k]: raise ContractError('Unknown randomness provenance')
        if mode == 'stochastic' and draw['independent_cluster_id'] not in units: units.append(draw['independent_cluster_id'])
    return units
