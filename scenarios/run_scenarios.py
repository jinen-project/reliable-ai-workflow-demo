from __future__ import annotations
import tempfile
from pathlib import Path
from core.runtime import Runtime
from adapters.local import ReadOnlyMCP
from scenarios.scenario_d import ScenarioDRuntime, scenario_d


def scenario_a(db: str):
    r = Runtime(db); cid = "approval-1"
    r.receive("a-event", "request", {"case_id": cid, "request": "standard action"})
    r.case(cid, state="REVIEW_REQUIRED", claims={"ai_recommendation": "continue"}, facts={"input_valid": True}, next_step="approval")
    blocked = r.approval(cid, "ai-model")
    approved = r.approval(cid, "reviewer")
    action = r.action(cid, "external-action")
    result = {"blocked": blocked, "approved": approved, "action": action, "views": r.views(cid)}
    r.close(); return result


def scenario_b():
    return {"direct_tool": ReadOnlyMCP().list_items("demo query"), "write_tools": []}


def scenario_c(db: str):
    cid = "async-1"; r = Runtime(db)
    r.receive("c-event", "webhook", {"case_id": cid, "email": "synthetic@example.test"})
    r.case(cid, state="READY", claims={"webhook_received": True}, facts={"normalized": True}, next_step="execute")
    first = r.action(cid, "crm-upsert", failure="response_lost"); r.close()
    r = Runtime(db); second = r.action(cid, "crm-upsert"); views = r.views(cid); r.close()
    return {"first": first, "after_restart": second, "views": views}


def run_all():
    with tempfile.TemporaryDirectory() as td:
        a = scenario_a(str(Path(td) / "a.sqlite")); c = scenario_c(str(Path(td) / "c.sqlite")); d = scenario_d(str(Path(td) / "d.sqlite"))
    return {"A": a, "B": scenario_b(), "C": c, "D": d}


if __name__ == "__main__":
    import json
    print(json.dumps(run_all(), indent=2))
