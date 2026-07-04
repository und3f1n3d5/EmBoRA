from pathlib import Path
from agent_core.agents import create_core_agent


def test_threshold_not_negative_constant_and_in_range():
    agent = create_core_agent(agent_type='emotional_rational', name='A')
    th = agent._threshold()
    assert 0.15 <= th <= 1.25


def test_no_threshold_minus_one_literal_in_production_core():
    for path in Path('agent_core').rglob('*.py'):
        assert 'threshold = -1.0' not in path.read_text(encoding='utf-8')
