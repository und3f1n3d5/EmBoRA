from agent_core.agents import get_legal_actions


def test_ug_role_specific_actions():
    proposer = {a.name for a in get_legal_actions('Ultimatum Game', 'proposer')}
    responder = {a.name for a in get_legal_actions('Ultimatum Game', 'responder')}
    assert proposer == {'offer'}
    assert responder == {'accept', 'reject'}
