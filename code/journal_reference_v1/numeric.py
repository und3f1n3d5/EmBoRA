"""Native C6 operation graph. This module never calls the reference oracle."""
import struct
from fractions import Fraction
from .schema import C, real, StateError


def bits(x):
    return struct.pack('>d', float(x)).hex()


def node(x):
    return {'fraction': str(Fraction.from_float(x)), 'float': x,
            'hex': x.hex(), 'bits_hex': bits(x),
            'sign_bit': int(bits(x)[0] in '89abcdef')}


def channel_projection(v, q, d=1.):
    """F05/07/08: exact equality is the sole identity shortcut."""
    v = real(v, 0, 1, StateError)
    q = real(q, 0, 1, StateError)
    d = real(d, 1, 1, StateError)
    alpha = float(C['alpha']); epsilon = float(C['epsilon'])
    c = 1. - alpha
    nodes = {'v': v, 'q': q, 'c': c}
    same = q == v
    if same:
        current, delta, signed, denominator = v, 0., 0., epsilon
    else:
        left = c * v
        right = alpha * q
        total = left + right
        current = min(1., max(0., total))
        delta = current - v
        distance = abs(d - v) if delta > 0 else v
        denominator = max(epsilon, distance)
        ratio = abs(delta) / denominator if delta else 0.
        magnitude = min(1., ratio)
        signed = -magnitude if delta < 0 else magnitude if delta > 0 else 0.
        nodes.update(left=left, right=right, total=total, ratio=ratio)
    nodes.update(current=current, delta=delta, denominator=denominator,
                 u=signed, u_abs=abs(signed))
    return {'identity': same, 'nodes': {k: node(x) for k, x in nodes.items()},
            'current': current, 'delta': delta, 'u': signed, 'u_abs': abs(signed)}
