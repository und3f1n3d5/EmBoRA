from pathlib import Path
from experiment_config import Condition, AgentSpec
from experiment_utils import load_project_main, run_episode


def test_single_observe_per_round():
    main_module = load_project_main(Path('.'))
    cond = Condition('t', 'S0', 'Prisoners Dilemma', AgentSpec('emotional_rational'), AgentSpec('fixed_strategy', fixed_strategy='tit_for_tat'))
    rows, info = run_episode(main_module, cond, run_profile='quick', episode_id=1, rounds=3, seed=1, model_mode='integrated_model', strict=True)
    assert len(rows) == 3
    assert info['duplicate_observe_count'] == 0
    assert rows[-1]['agent_1_observations_count'] == 3
    assert rows[-1]['agent_2_observations_count'] == 3
