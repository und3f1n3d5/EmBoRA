from agent_core.appraisal import CurrentStateEvaluation, signed_urgency
from agent_core.model_schema import ValueType


def test_signed_urgency_delta_positive_negative_neutral():
    assert signed_urgency(0.4, 0.6, 1.0) > 0
    assert signed_urgency(0.6, 0.55, 1.0) < 0
    assert signed_urgency(0.6, 0.6, 1.0) == 0


def test_appraisal_reaction_signs_follow_delta():
    ots = CurrentStateEvaluation()
    prev = {vt: 0.4 for vt in ValueType}
    cur = {vt: 0.6 for vt in ValueType}
    app = ots.evaluate(prev, cur, chunk_2=1.0)
    assert app.reaction_intensity > 0
    app2 = ots.evaluate(cur, prev, chunk_2=1.0)
    assert app2.reaction_intensity < 0
