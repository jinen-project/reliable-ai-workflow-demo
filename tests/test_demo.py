from scenarios.run_scenarios import run_all


def test_three_scenarios():
    out = run_all()
    import json
    assert "local-fixture-key" not in json.dumps(out)
    assert out["A"]["blocked"]["reason"] == "UNAUTHORIZED"
    assert out["A"]["approved"]["approved"] is True
    assert out["A"]["action"]["status"] == "VERIFIED"
    assert out["B"]["direct_tool"]["ok"] is True
    assert out["B"]["write_tools"] == []
    assert out["C"]["first"]["status"] == "AMBIGUOUS"
    assert out["C"]["after_restart"]["status"] == "VERIFIED"
    assert out["C"]["after_restart"]["attempts"] == 2
    assert all(key in out["C"]["views"] for key in ("operator", "reviewer", "audit"))


if __name__ == "__main__":
    test_three_scenarios()
    print("PUBLIC_DEMO_VERIFY=PASS")
