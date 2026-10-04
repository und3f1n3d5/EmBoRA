"""Single pure constructor→policy→adapter→update path for every model variant."""
from dataclasses import dataclass
from .schema import *
from .games import Adapter, Result, validate_observation, validate_action
from .formulas import *


def candidate_choice(state, offer, adapter):
    """F-18/35; both candidates project the identical pre-state, never q_star."""
    if type(state) is not State or type(adapter) is not Adapter: raise TraceError('Immutable State and selected Adapter required')
    integer(offer, 2, 8, ActionError)
    candidates = {}
    for action in ('accept', 'reject'):
        q = adapter.raw('UG', 2, 'responder', [{'name': 'offer', 'offer': offer}, {'name': action}])
        candidates[action] = {'adapter_id': adapter.adapter_id, 'selected_adapter_convention': adapter.selected_adapter_convention,
                              'q': mapping(q), **projection(state, q)}
    z = tuple((candidates['accept']['uhat_signed'][k] > candidates['reject']['uhat_signed'][k]) -
              (candidates['accept']['uhat_signed'][k] < candidates['reject']['uhat_signed'][k]) for k in K)
    return {'candidates': candidates, **directional_vote(state.p_clip, z)}


def validate_choice(trace, state, offer, adapter):
    assert_exact_tree(trace,candidate_choice(state, offer, adapter))


def baseline_policy(baseline_id, obs):
    """B01 policies, stateless and pure."""
    game = obs['game']; seat = obs['seat']; history = obs['history']
    if baseline_id in ('PD_AllC', 'PD_AllD'): return {'name': 'C' if baseline_id == 'PD_AllC' else 'D'}
    if baseline_id == 'PD_TFT': return {'name': 'C'} if not history else copy.deepcopy(history[-1]['actions_by_seat'][2 - seat])
    if baseline_id == 'PD_WSLS':
        if not history: return {'name': 'C'}
        last = history[-1]; own = last['actions_by_seat'][seat - 1]['name']
        return {'name': own if last['payoffs_by_seat'][seat - 1] in (3, 5) else ('D' if own == 'C' else 'C')}
    if baseline_id == 'BoS_Opera': return {'name': 'O'}
    if baseline_id == 'BoS_Fight': return {'name': 'F'}
    if baseline_id == 'BoS_Convention': return convention(obs['round'])
    if baseline_id in ('UG_Offer2', 'UG_Offer4', 'UG_Offer5', 'UG_Offer8'): return {'name': 'offer', 'offer': int(baseline_id[-1])}
    if baseline_id == 'UG_Cycle': return {'name': 'offer', 'offer': obs['game_parameters']['offer_grid'][(obs['round'] - 1) % 7]}
    if baseline_id == 'UG_AcceptAll': return {'name': 'accept'}
    if baseline_id == 'UG_RejectAll': return {'name': 'reject'}
    if baseline_id in ('UG_Threshold4', 'UG_Threshold5'): return {'name': 'accept' if obs['current_offer'] >= int(baseline_id[-1]) else 'reject'}
    raise ConfigError('Unknown baseline policy')


@dataclass(frozen=True)
class Agent:
    effective_config_json: str
    agent_id: int
    adapter: Adapter

    @classmethod
    def construct(cls, config, agent_id, adapter):
        validate_config(config); integer(agent_id, 1, 2, ConfigError)
        if type(adapter) is not Adapter: raise ConfigError('Selected immutable Adapter required')
        if (adapter.selected_adapter_convention, adapter.run_purpose) != (config['selected_adapter_convention'], config['run_purpose']):
            raise ConfigError('Constructor adapter mismatch')
        return cls(canonical(config), agent_id, adapter)

    @property
    def config(self): return parse_json(self.effective_config_json)
    @property
    def descriptor(self): return next(a for a in self.config['agents'] if a['agent_id'] == self.agent_id)
    @property
    def initial_source_state(self):
        a = self.descriptor
        return None if a['controller_type'] == 'baseline' else State.from_primary(a['initial_primary_state'], a['personality'], a['intensity'])
    @property
    def initial_state(self):
        s = self.initial_source_state
        return None if s is None else s.project(self.descriptor['variant'])

    def decide(self, payload):
        return self._compute_decision(payload)

    def validate_decision(self, decision, payload):
        assert_exact_tree(decision, self._compute_decision(payload))

    def _compute_decision(self, payload):
        keys(payload, ('public_observation', 'own_pre_state'), PayloadError)
        config = self.config; a = self.descriptor; obs = payload['public_observation']
        validate_observation(obs, config, a)
        if (self.adapter.selected_adapter_convention, self.adapter.run_purpose) != (config['selected_adapter_convention'], config['run_purpose']): raise TraceError('Run adapter switching')
        if a['controller_type'] == 'baseline':
            if payload['own_pre_state'] is not None: raise PayloadError('Baseline state is null')
            action = baseline_policy(a['baseline_id'], obs)
            validate_action(obs['game'], a['role'], action)
            return {'aE': None, 'aR': None, 'selected_branch': 'fixed', 'proposals_differ': None, 'action': action,
                    'iota': None, 'rho': None, 'theta': None, 'theta_reference': None, 'impulse_mode': None,
                    'source_pre_state': None, 'decision_pre_state': None, 'choice': None,
                    'selected_adapter_convention': self.adapter.selected_adapter_convention, 'adapter_id': self.adapter.adapter_id}
        state = State.from_dict(payload['own_pre_state'])
        if (state.personality, state.intensity) != (a['personality'], a['intensity']): raise StateError('Private config/state mismatch')
        if config['run_purpose'] != 'structural_fixture' and state.p != tuple(REGISTRY['priority_profiles'][a['priority_profile']]): raise StateError('Unregistered priority override')
        source = state; state = state.project(a['variant'])
        iota = impulse(state, a['kind']); theta_reference = threshold(state)
        theta = clip(C['theta_min'], C['theta_max'], state.chi1) if a['variant'] == 'fixed_threshold' else theta_reference
        choice = None
        if obs['game'] == 'PD': aE, aR = pd_proposals(iota, state.S, a['kind'])
        elif obs['game'] == 'BoS': aE, aR = convention(obs['round']), convention(obs['round'])
        elif a['role'] == 'proposer': aE, aR = ug_offer(iota), ug_rational(a['kind'], a['role'])
        else:
            choice = candidate_choice(state, obs['current_offer'], self.adapter)
            aE, aR = choice['action'], ug_rational(a['kind'], a['role'])
        branch = select_branch(a['kind'], iota, theta)
        action = aE if branch == 'E' else aR
        for ac in (aE, aR, action): validate_action(obs['game'], a['role'], ac)
        return {'aE': aE, 'aR': aR, 'selected_branch': branch, 'proposals_differ': aE != aR, 'action': action,
                'iota': iota, 'rho': None, 'theta': theta, 'theta_reference': theta_reference,
                'impulse_mode': 'zero_by_kind' if a['kind'] == 'rational_only' else 'state_formula',
                'source_pre_state': source.to_dict(), 'decision_pre_state': state.to_dict(), 'choice': choice,
                'selected_adapter_convention': self.adapter.selected_adapter_convention, 'adapter_id': self.adapter.adapter_id}

    def prepare_update(self, state, observation, decision, result, expected_round):
        """Compute without mutation; orchestrator alone owns exactly-once atomic commit."""
        a = self.descriptor
        if type(result) is not Result: raise PayloadError('Immutable Result required')
        validate_observation(observation, self.config, a)
        data = result.validate(self.config, a)
        if type(expected_round) is not int or data['round'] != expected_round or observation['round'] != expected_round: raise UpdateError('Duplicate/stale result before mutation')
        payload = {'public_observation': observation, 'own_pre_state': None if state is None else state.to_dict()}
        self.validate_decision(decision,payload)
        if decision['action'] != data['actions_by_seat'][a['seat'] - 1]: raise TraceError('Final action/result mismatch')
        if self.config['game'] == 'UG' and a['role'] == 'responder' and observation['current_offer'] != data['actions_by_seat'][0]['offer']: raise TraceError('Current offer/result mismatch')
        if state is None:
            return None, {**{k: None for k in ('raw_q','q_star','delta','u_signed','u','V','L','k_star','rho','sigma','Csup_raw','Csup_applied','mood_preclip','fatigue_preclip','unprojected_post_state','post_state','numeric_evidence','variant')},
                          'adapter_id': self.adapter.adapter_id, 'selected_adapter_convention': self.adapter.selected_adapter_convention, 'update_count': 1}

        pre = state.project(a['variant'])
        q = self.adapter.raw(data['game'], a['seat'], a['role'], data['actions_by_seat'])
        q_star = tuple(q[j] if j == 0 or a['variant'] != 'material_only' else pre.v[j] for j in range(4))  # F-32
        projected = projection(pre, q_star)
        vnew = tuple(projected['vhat'][k] for k in K)
        delta = tuple(projected['Deltahat'][k] for k in K)
        signed = tuple(projected['uhat_signed'][k] for k in K)
        u = tuple(projected['uhat_absolute'][k] for k in K)
        V = ordered_sum(p * s for p, s in zip(pre.pbar, signed))
        L = ordered_sum(p * x for p, x in zip(pre.pbar, u))
        rho = reaction(V, pre.chi2)  # F-11
        sigma = int(decision['aE'] != decision['action']); cost_raw = sigma * abs(decision['iota'])  # F-21
        cost_applied = 0. if a['variant'] == 'no_suppression' else cost_raw
        mood_preclip = C['mood_decay'] * pre.m + rho / C['mood_scale']  # F-22
        fatigue_preclip = pre.f + C['fatigue_load_rate'] * L + C['fatigue_impulse_rate'] * min(C['impulse_abs_max'], abs(decision['iota'])) / C['impulse_abs_max'] + C['suppression_cost_rate'] * cost_applied - C['recovery_rate'] * (1 - min(1, L))  # F-23
        unprojected = State(vnew, pre.d, pre.p, clip(C['mood_min'], C['mood_max'], mood_preclip), clip(0, 1, fatigue_preclip), pre.personality, pre.intensity)
        post = unprojected.project(a['variant'])
        return post, {'raw_q': mapping(q), 'q_star': mapping(q_star), 'delta': mapping(delta), 'u_signed': mapping(signed), 'u': mapping(u),
                      'V': V, 'L': L, 'k_star': focus(pre.pbar, signed), 'rho': rho, 'sigma': sigma,
                      'Csup_raw': cost_raw, 'Csup_applied': cost_applied, 'mood_preclip': mood_preclip, 'fatigue_preclip': fatigue_preclip,
                      'unprojected_post_state': unprojected.to_dict(), 'post_state': post.to_dict(),
                      'adapter_id': self.adapter.adapter_id, 'selected_adapter_convention': self.adapter.selected_adapter_convention,
                      'variant': a['variant'], 'numeric_evidence': projected['numeric_evidence'], 'update_count': 1}
