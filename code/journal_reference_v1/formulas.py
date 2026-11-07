"""Pure model helpers. Branch comparisons are exact; no tolerances."""
from .schema import *
from .numeric import channel_projection


def urgency(prev, current, desired, epsilon=C['epsilon']):
    """F-07/08 helper; independent domain, not implicit production reachability."""
    prev = real(prev, 0, 1); current = real(current, 0, 1); desired = real(desired, 0, 1)
    epsilon = real(epsilon, 0)
    if epsilon <= 0: raise ContractError('epsilon must be positive')
    delta = current - prev
    if delta > 0: return min(1., abs(delta) / max(epsilon, abs(desired - prev)))
    if delta < 0: return -min(1., abs(delta) / max(epsilon, prev))
    return 0.


def projection(state, q):
    """F-05/07/08: side-effect-free projection from one immutable pre-state."""
    if type(q) is not tuple or len(q) != 4: raise StateError('K target vector required')
    for x in q: real(x, 0, 1, StateError)
    channels = [channel_projection(v, target, d) for v, target, d in zip(state.v, q, state.d)]
    from .evidence import channel_evidence
    evidence = [channel_evidence(v, target, result) for v, target, result in zip(state.v, q, channels)]
    return {'vhat': mapping([x['current'] for x in channels]),
            'Deltahat': mapping([x['delta'] for x in channels]),
            'uhat_signed': mapping([x['u'] for x in channels]),
            'uhat_absolute': mapping([x['u_abs'] for x in channels]),
            'numeric_evidence': mapping(evidence)}



def focus(pbar, signed):
    """F-10: frozen K tie rule, including JSON null for all-zero weights."""
    if len(pbar) != 4 or len(signed) != 4: raise StateError('Four weights/urgencies required')
    for p in pbar: real(p, 0, 1)
    for s in signed: real(s, -1, 1)
    w = tuple(p * abs(s) for p, s in zip(pbar, signed))
    if all(x == 0 for x in w): return None
    return K[w.index(max(w))]


def reaction(V, chi2):
    """F-11: declared wider helper permits protective clip tests."""
    V = real(V, -1, 1); chi2 = real(chi2, 0)
    return clip(C['reaction_min'], C['reaction_max'], chi2 * C['kappa'] * V)


def impulse(state, kind):
    """F-12, rational-only zero is a kind rule, not a switch."""
    enum(kind, REGISTRY['enums']['model_kind'])
    if kind == 'rational_only': return 0.
    return clip(C['impulse_min'], C['impulse_max'], state.chi2 *
                (C['b_m'] * state.m + C['b_f'] * state.f + C['b_W'] * (state.W - C['W_center'])))


def threshold(state):
    """F-13: equalities select zero modifiers."""
    M = C['m_negative_offset'] if state.m < C['m_negative_cut'] else C['m_positive_offset'] if state.m > C['m_positive_cut'] else 0
    R = C['resource_offset'] if state.r < C['resource_cut'] else 0
    return clip(C['theta_min'], C['theta_max'], state.chi1 * (1 - C['a_f'] * state.f) + M + R)


def select_branch(kind, iota, theta):
    """F-14: equality selects R."""
    enum(kind, REGISTRY['enums']['model_kind']); real(iota, -1.5, 1.5); real(theta, .15, 1.25)
    if kind == 'emotional_only': return 'E'
    if kind == 'rational_only': return 'R'
    return 'E' if abs(iota) > theta else 'R'


def pd_proposals(iota, S, kind):
    """F-15/F-16; emotional-only retains diagnostic state-based aR."""
    real(iota, -1.5, 1.5); real(S, -2.5, 1.5); enum(kind, REGISTRY['enums']['model_kind'])
    return ({'name': 'C' if iota >= C['pd_emotional_cut'] else 'D'},
            {'name': 'D' if kind == 'rational_only' else 'C' if S >= C['pd_rational_state_cut'] else 'D'})


def ug_offer(iota, grid=None):
    """F-17 helper permits enumeration permutations; external grid remains exact."""
    real(iota, -1.5, 1.5)
    grid = tuple(REGISTRY['game_parameters']['ug_legal_offers']) if grid is None else tuple(grid)
    if sorted(grid) != list(REGISTRY['game_parameters']['ug_legal_offers']) or any(type(x) is not int for x in grid): raise ActionError('Altered offer helper grid')
    z = C['ug_offer_center'] + clip(C['ug_proposer_impulse_min'], C['ug_proposer_impulse_max'], iota)
    return {'name': 'offer', 'offer': min(grid, key=lambda o: (abs(o - z), o))}


def ug_rational(kind, role):
    """F-19, only positive legal current offers; external validation owns offer."""
    enum(kind, REGISTRY['enums']['model_kind']); enum(role, ('proposer', 'responder'))
    if role == 'responder': return {'name': 'accept'}
    return {'name': 'offer', 'offer': C['ug_rational_only_offer'] if kind == 'rational_only' else C['ug_hybrid_system2_offer']}


def convention(t):
    """F-20, round origin 1."""
    integer(t, 1, 100000)
    return {'name': 'O' if t % 2 else 'F'}


def classify_numerator(N):
    """F-35 category source; negative branch can be exercised helper-only."""
    real(N, -6, 6)
    if N > 0: return ('positive_accept', {'name': 'accept'})
    if N < 0: return ('negative_reject', {'name': 'reject'})
    return ('tie_reject', {'name': 'reject'})


def directional_vote(p_clip, z):
    if type(p_clip) is not tuple or type(z) is not tuple or len(p_clip) != 4 or len(z) != 4: raise TraceError('Frozen K vectors required')
    for p in p_clip: real(p, .5, 1.5, TraceError)
    if any(type(v) is not int or v not in (-1, 0, 1) for v in z): raise TraceError('Invalid exact channel vote')
    N = math.fsum(p * vote for p, vote in zip(p_clip, z))  # sole F-35 branch sum
    P = math.fsum(p_clip)
    D = N / P  # diagnostic, never branch input
    category, action = classify_numerator(N)
    return {'p_clip': mapping(p_clip), 'z': mapping(z), 'N_VS': N, 'P_VS': P, 'D_VS': D, 'category': category, 'action': action}
