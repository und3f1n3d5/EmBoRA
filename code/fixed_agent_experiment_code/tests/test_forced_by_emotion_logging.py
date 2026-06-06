from agent_core.agents import create_core_agent, get_legal_actions
from agent_core.model_schema import GameState, GameResult, ModelMode
from experiment_utils import count_forced_by_emotion


def test_forced_by_emotion_is_stored_in_replay():
    agent = create_core_agent(agent_type='emotional_rational', name='A', intensity='high', model_mode=ModelMode.INTEGRATED_MODEL)
    agent.state.mood = 0.5
    agent.state.fatigue = 1.0
    agent.chunk_1 = 0.15
    actions = get_legal_actions('Prisoners Dilemma')
    obs = GameState('Prisoners Dilemma', available_actions=actions)
    action, trace = agent.decide(obs, actions, 1)
    assert trace.forced_by_emotion is True
    result = GameResult('Prisoners Dilemma', 1, 'player', action, 'cooperate', 3.0 if action == 'cooperate' else 5.0, 3.0 if action == 'cooperate' else 0.0)
    agent.observe(result, trace)
    assert count_forced_by_emotion(agent) > 0
