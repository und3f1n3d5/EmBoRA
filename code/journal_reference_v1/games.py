"""Legal games/payloads and immutable selected-adapter outcome mapping F-01..04/31."""
from dataclasses import dataclass
from .schema import *

TABLES = {
    'PD': {('C', 'C'): (3, 3), ('C', 'D'): (0, 5), ('D', 'C'): (5, 0), ('D', 'D'): (1, 1)},
    'BoS': {('O', 'O'): (3, 2), ('O', 'F'): (0, 0), ('F', 'O'): (0, 0), ('F', 'F'): (2, 3)},
}
OFFERS = tuple(REGISTRY['game_parameters']['ug_legal_offers'])


def legal_actions(game, role):
    enum(game, REGISTRY['enums']['game'], ActionError)
    if game == 'UG':
        enum(role, ('proposer', 'responder'), ActionError)
        return [{'name': 'offer', 'offer': o} for o in OFFERS] if role == 'proposer' else [{'name': 'accept'}, {'name': 'reject'}]
    if role != 'player': raise ActionError('Wrong simultaneous-game role')
    return [{'name': a} for a in ('C', 'D') if game == 'PD'] if game == 'PD' else [{'name': 'O'}, {'name': 'F'}]


def validate_action(game, role, action):
    if game == 'UG' and role == 'proposer':
        keys(action, ('name', 'offer'), ActionError)
        if action['name'] != 'offer': raise ActionError('Offer action required')
        integer(action['offer'], 2, 8, ActionError)
    else: keys(action, ('name',), ActionError)
    if action not in legal_actions(game, role): raise ActionError('Illegal action')
    return action


def descriptor(game):
    if game == 'UG': return {'endowment': 10, 'offer_grid': list(OFFERS)}
    enum(game, TABLES, PayloadError)
    return {'payoff_table': [{'actions': list(a), 'payoffs': list(p)} for a, p in TABLES[game].items()]}


def execute(game, actions):
    if type(actions) is not list or len(actions) != 2: raise ActionError('Two seat-ordered actions required')
    for seat, action in enumerate(actions, 1):
        role = ('proposer' if seat == 1 else 'responder') if game == 'UG' else 'player'
        validate_action(game, role, action)
    if game == 'UG':
        o = actions[0]['offer']
        return (10 - o, o) if actions[1]['name'] == 'accept' else (0, 0)
    return TABLES[game][tuple(a['name'] for a in actions)]


def validate_history(history, game, round_number):
    if type(history) is not list or len(history) != round_number - 1: raise PayloadError('Complete consecutive history required')
    for t, entry in enumerate(history, 1):
        keys(entry, ('round', 'actions_by_seat', 'payoffs_by_seat'), PayloadError)
        if integer(entry['round'], 1, round_number - 1, PayloadError) != t: raise PayloadError('Wrong history round')
        payoffs = execute(game, entry['actions_by_seat'])
        if type(entry['payoffs_by_seat']) is not list or len(entry['payoffs_by_seat']) != 2: raise PayloadError('Wrong history payoffs')
        for actual, expected in zip(entry['payoffs_by_seat'], payoffs):
            if real(actual, error=PayloadError) != expected: raise PayloadError('History payoff mismatch')


def observation(config, agent, history, current_offer=None):
    t = len(history) + 1
    obs = {'schema_id': REGISTRY['serialization']['observation_schema_id'], 'game': config['game'],
           'round': t, 'horizon': config['horizon'], 'agent_id': agent['agent_id'], 'seat': agent['seat'], 'role': agent['role'],
           'game_parameters': descriptor(config['game']), 'legal_actions': legal_actions(config['game'], agent['role']),
           'history': copy.deepcopy(history)}
    if config['game'] == 'UG' and agent['role'] == 'responder': obs['current_offer'] = current_offer
    validate_observation(obs, config, agent)
    return obs


def validate_observation(obs, config, agent):
    fields = {'schema_id', 'game', 'round', 'horizon', 'agent_id', 'seat', 'role', 'game_parameters', 'legal_actions', 'history'}
    responder = config['game'] == 'UG' and agent['role'] == 'responder'
    if responder: fields.add('current_offer')
    keys(obs, fields, PayloadError)
    for field in ('game', 'horizon', 'agent_id', 'seat', 'role'):
        expected = config[field] if field in ('game', 'horizon') else agent[field]
        if canonical(obs[field]) != canonical(expected): raise PayloadError('Observation identity/config mismatch: ' + field)
    if obs['schema_id'] != REGISTRY['serialization']['observation_schema_id']: raise PayloadError('Wrong observation schema')
    t = integer(obs['round'], 1, config['horizon'], PayloadError)
    if canonical(obs['game_parameters']) != canonical(descriptor(config['game'])): raise PayloadError('Wrong game descriptor/grid or extra nested fields')
    if canonical(obs['legal_actions']) != canonical(legal_actions(config['game'], agent['role'])): raise PayloadError('Wrong legal actions/order')
    validate_history(obs['history'], config['game'], t)
    if responder: integer(obs['current_offer'], 2, 8, PayloadError)
    return obs


@dataclass(frozen=True)
class Result:
    """JSON storage isolates caller data; every read yields an independent value."""
    serialized: str

    @classmethod
    def build(cls, game, t, agent, actions):
        payoffs = execute(game, actions)
        return cls(canonical({'schema_id': REGISTRY['serialization']['result_schema_id'], 'game': game, 'round': t,
                              'agent_id': agent['agent_id'], 'seat': agent['seat'], 'role': agent['role'],
                              'actions_by_seat': actions, 'payoffs_by_seat': list(payoffs)}))

    def to_dict(self): return parse_json(self.serialized)

    def validate(self, config, agent):
        data = self.to_dict()
        keys(data, ('schema_id', 'game', 'round', 'agent_id', 'seat', 'role', 'actions_by_seat', 'payoffs_by_seat'), PayloadError)
        if data['schema_id'] != REGISTRY['serialization']['result_schema_id']: raise PayloadError('Wrong result schema')
        if data['game'] != config['game']: raise PayloadError('Wrong result game')
        integer(data['round'], 1, config['horizon'], PayloadError)
        for field in ('agent_id', 'seat', 'role'):
            if canonical(data[field]) != canonical(agent[field]): raise PayloadError('Wrong result identity')
        expected = execute(config['game'], data['actions_by_seat'])
        if type(data['payoffs_by_seat']) is not list or len(data['payoffs_by_seat']) != 2: raise PayloadError('Malformed payoffs')
        for value, oracle in zip(data['payoffs_by_seat'], expected):
            if real(value, error=PayloadError) != oracle: raise PayloadError('Illegal payoff, never clip into q')
        return data


def normalize(payoff, minimum, maximum):
    """F-01, also F-03 normalization; equal-range convention is helper-only."""
    minimum = real(minimum); maximum = real(maximum)
    if minimum > maximum: raise ContractError('Reversed normalization range')
    payoff = real(payoff, minimum, maximum)
    return 1. if maximum == minimum else clip(0, 1, (payoff - minimum) / (maximum - minimum))


def inverse_regret(g, maximum):
    """F-04; zero-max branch allowed only on valid zero regret."""
    maximum = real(maximum, 0); g = real(g, 0, maximum)
    return 1. if maximum == 0 else clip(0, 1, 1 - g / maximum)


@dataclass(frozen=True)
class Adapter:
    selected_adapter_convention: str
    run_purpose: str

    def __post_init__(self): validate_adapter(self.selected_adapter_convention, self.run_purpose)
    @property
    def adapter_id(self):
        return next(x['id'] for x in REGISTRY['adapter_contract'].values()
                    if type(x) is dict and x.get('config_key') == self.selected_adapter_convention)

    def raw(self, game, seat, role, actions):
        integer(seat, 1, 2, PayloadError)
        expected_role = ('proposer' if seat == 1 else 'responder') if game == 'UG' else 'player'
        if role != expected_role: raise PayloadError('Adapter role/seat mismatch')
        payoffs = execute(game, actions); idx = seat - 1
        if game == 'UG':
            offer = actions[0]['offer']; accepted = actions[1]['name'] == 'accept'
            inequity = abs(10 - 2 * offer) / 10
            fairness = 1 - inequity if accepted else (inequity if self.selected_adapter_convention == 'normative_resisted_inequity_v1' else
                        0. if self.selected_adapter_convention == 'sensitivity_zero_exchange_v1' else .5)
            relationship = 1. if accepted else (.5 if self.selected_adapter_convention == 'sensitivity_neutral_no_exchange_v1' else 0.)
            alternatives = [execute('UG', [{'name': 'offer', 'offer': o}, actions[1]])[0] for o in OFFERS] if seat == 1 else [offer, 0]
            maximum_regret = 6 if seat == 1 else 8
            q = (normalize(payoffs[idx], 0, 8), fairness, relationship,
                 inverse_regret(max(alternatives) - payoffs[idx], maximum_regret))
        else:
            table = TABLES[game]; max_payoff = 5 if game == 'PD' else 3
            normalized = [normalize(p, 0, max_payoff) for p in payoffs]
            own_action = actions[idx]['name']; opponent_action = actions[1 - idx]['name']
            own_slice = [p[idx] for a, p in table.items() if a[idx] == own_action]
            counterfactual = [p[idx] for a, p in table.items() if a[1 - idx] == opponent_action]
            q = (normalized[idx], 1 - abs(normalized[0] - normalized[1]),
                 normalize(payoffs[idx], min(own_slice), max(own_slice)),
                 inverse_regret(max(counterfactual) - payoffs[idx], 2 if game == 'PD' else 3))
        for value in q: real(value, 0, 1, PayloadError)
        return q
