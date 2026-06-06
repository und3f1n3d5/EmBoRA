from agent_core.value_adapter import GameValueAdapter
from agent_core.model_schema import ValueType


def assert_range(vals):
    assert set(vals) == {ValueType.MATERIAL, ValueType.FAIRNESS, ValueType.RELATIONSHIP, ValueType.SAFETY}
    for v in vals.values():
        assert 0.0 <= v <= 1.0


def test_pd_outcomes_have_expected_shape_and_safety():
    a = GameValueAdapter()
    cc = a.compute_event_values(game_name="Prisoners Dilemma", focal_agent_id=1, own_action="cooperate", opponent_action="cooperate", own_payoff=3, opponent_payoff=3)
    cd = a.compute_event_values(game_name="Prisoners Dilemma", focal_agent_id=1, own_action="cooperate", opponent_action="defect", own_payoff=0, opponent_payoff=5)
    dc = a.compute_event_values(game_name="Prisoners Dilemma", focal_agent_id=1, own_action="defect", opponent_action="cooperate", own_payoff=5, opponent_payoff=0)
    dd = a.compute_event_values(game_name="Prisoners Dilemma", focal_agent_id=1, own_action="defect", opponent_action="defect", own_payoff=1, opponent_payoff=1)
    for vals in (cc, cd, dc, dd):
        assert_range(vals)
    assert cd[ValueType.SAFETY] < dc[ValueType.SAFETY]
    assert dc[ValueType.MATERIAL] > cc[ValueType.MATERIAL]


def test_bos_outcomes():
    a = GameValueAdapter()
    oo = a.compute_event_values(game_name="Battle of Sexes", focal_agent_id=1, own_action="opera", opponent_action="opera", own_payoff=3, opponent_payoff=2)
    mis = a.compute_event_values(game_name="Battle of Sexes", focal_agent_id=1, own_action="opera", opponent_action="fight", own_payoff=0, opponent_payoff=0)
    assert_range(oo)
    assert_range(mis)
    assert oo[ValueType.RELATIONSHIP] > mis[ValueType.RELATIONSHIP]


def test_ug_fair_accept_vs_reject():
    a = GameValueAdapter()
    fair = a.compute_event_values(game_name="Ultimatum Game", focal_agent_id=2, role="responder", own_action="accept", opponent_action="offer(offer=5)", own_payoff=5, opponent_payoff=5)
    reject = a.compute_event_values(game_name="Ultimatum Game", focal_agent_id=2, role="responder", own_action="reject", opponent_action="offer(offer=2)", own_payoff=0, opponent_payoff=0)
    assert_range(fair)
    assert_range(reject)
    assert fair[ValueType.FAIRNESS] >= reject[ValueType.FAIRNESS]
    assert fair[ValueType.MATERIAL] > reject[ValueType.MATERIAL]
