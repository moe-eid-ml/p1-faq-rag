from sniper.adversarial.runner import load_cases, run_all


def test_runner_loads_cases():
    cases = load_cases()
    assert len(cases) >= 7
    assert all(c.id.startswith("ADV-") for c in cases)


def test_runner_returns_stable_result_shape():
    results = run_all(include_harness=False)
    assert results, "should return non-empty results when include_harness=False"
    for r in results:
        assert "id" in r and "verdict" in r and "reason" in r and "details" in r
        assert r["verdict"] in {"GREEN", "YELLOW", "RED"}
