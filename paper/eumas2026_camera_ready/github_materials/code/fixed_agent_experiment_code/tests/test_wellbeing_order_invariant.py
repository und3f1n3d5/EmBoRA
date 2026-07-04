from agent_core.model_schema import ValueType, Values
from agent_core.state_updater import StateUpdater


def test_wellbeing_order_invariant():
    updater = StateUpdater()
    v1 = Values()
    v2 = Values()
    vals = {ValueType.MATERIAL: 0.2, ValueType.FAIRNESS: 0.4, ValueType.RELATIONSHIP: 0.8, ValueType.SAFETY: 1.0}
    # Insert in different order.
    v1.current = dict(vals)
    v2.current = {k: vals[k] for k in reversed(list(vals.keys()))}
    assert updater.weighted_wellbeing(v1) == updater.weighted_wellbeing(v2)
