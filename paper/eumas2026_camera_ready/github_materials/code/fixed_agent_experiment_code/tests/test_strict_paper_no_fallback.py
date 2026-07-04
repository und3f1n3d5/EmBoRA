from pathlib import Path
import pytest
from experiment_config import Condition, AgentSpec
from experiment_utils import load_project_main, run_episode


def test_strict_mode_raises_instead_of_fallback_for_bad_game():
    main_module = load_project_main(Path('.'))
    cond = Condition('bad', 'S0', 'Unknown Game', AgentSpec('emotional_rational'), AgentSpec('rational'))
    with pytest.raises(Exception):
        run_episode(main_module, cond, run_profile='paper', episode_id=1, rounds=1, seed=1, model_mode='reported_runs_compat', strict=True, allow_fallback=False)
