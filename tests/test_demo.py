from scenarios.run_scenarios import run_all
from scenarios.scenario_d import ScenarioDRuntime, scenario_d
import tempfile
from pathlib import Path


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


def test_scenario_d():
    with tempfile.TemporaryDirectory() as td:
        out = scenario_d(str(Path(td) / "d.sqlite"))
        assert out["first"]["classification"]["reference_scoring_only"] is True
        assert out["first"]["state"] == "RETRYABLE"
        assert out["after_restart"]["state"] == "VERIFIED"
        assert out["after_restart"]["crm"]["status"] == "VERIFIED"
        assert out["after_restart"]["notification"]["status"] == "VERIFIED"
        assert out["views"]["operator"]["state"] == "VERIFIED"

    for failure in ("crm_timeout", "rate_limit", "notification_failure"):
        with tempfile.TemporaryDirectory() as td:
            out = scenario_d(str(Path(td) / f"{failure}.sqlite"), failure=failure)
            assert out["after_restart"]["state"] == "VERIFIED", failure

    with tempfile.TemporaryDirectory() as td:
        db = str(Path(td) / "cases.sqlite")
        malformed = ScenarioDRuntime(db)
        result = malformed.process({"event_id": "malformed-1", "case_id": "malformed", "name": "Synthetic", "message": "hello", "ai_failure": "malformed"})
        assert result["state"] == "UNRESOLVED"
        review = malformed.process({"event_id": "review-1", "case_id": "review", "name": "Synthetic", "message": "urgent request", "risk_indicator": True})
        assert review["state"] == "ROUTED_REVIEW"
        duplicate = malformed.process({"event_id": "review-2", "case_id": "review", "name": "Synthetic", "message": "urgent request", "risk_indicator": True})
        assert duplicate["event"]["status"] == "REPLAY"
        malformed.close()


if __name__ == "__main__":
    test_three_scenarios()
    test_scenario_d()
    print("PUBLIC_DEMO_VERIFY=PASS")
