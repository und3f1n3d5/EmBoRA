from pathlib import Path
from experiment_config import Condition, AgentSpec
from experiment_utils import load_project_main, run_episode


def _one_row(mode):
    main_module = load_project_main(Path('.'))
    cond = Condition('t', 'S0', 'Prisoners Dilemma', AgentSpec('emotional_rational'), AgentSpec('rational'))
    rows, _ = run_episode(main_module, cond, run_profile='quick', episode_id=1, rounds=1, seed=1, model_mode=mode, strict=True)
    return rows[0]


def test_reported_compat_marks_diagnostics_only():
    row = _one_row('reported_runs_compat')
    assert row['model_mode'] == 'reported_runs_compat'
    assert row['adapter_behavior_driving'] is False
    assert row['mechanism_status'] == 'diagnostic/explanatory'


def test_integrated_marks_behavior_driving():
    row = _one_row('integrated_model')
    assert row['model_mode'] == 'integrated_model'
    assert row['adapter_behavior_driving'] is True
    assert row['mechanism_status'] == 'behavior-driving'
