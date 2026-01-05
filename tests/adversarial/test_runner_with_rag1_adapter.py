from sniper.adversarial.runner import run_all
from sniper.integrations.rag1_adapter import answer_fn


def test_runner_can_call_rag1_adapter_on_non_harness_cases():
    # This should run the non-harness cases through the real adapter without crashing.
    results = run_all(answer_fn=answer_fn, include_harness=False)
    assert results
    for r in results:
        assert r["verdict"] in {"GREEN", "YELLOW", "RED"}
