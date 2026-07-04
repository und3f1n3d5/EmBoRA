from agent_core.agents import create_core_agent, get_legal_actions
from agent_core.model_schema import GameState, ModelMode


def test_decide_does_not_change_state_values_or_replay():
    agent = create_core_agent(agent_type="emotional_rational", name="A", model_mode=ModelMode.INTEGRATED_MODEL)
    actions = get_legal_actions("Prisoners Dilemma")
    obs = GameState("Prisoners Dilemma", available_actions=actions)
    before = agent.snapshot_before_decision()
    action, trace = agent.decide(obs, actions, 1)
    after = agent.snapshot_before_decision()
    assert before["state"].__dict__ == after["state"].__dict__
    assert before["values"].as_plain_dict() == after["values"].as_plain_dict()
    assert before["em_buffer_size"] == after["em_buffer_size"] == 0
    assert before["rm_buffer_size"] == after["rm_buffer_size"] == 0
