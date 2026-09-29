from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any


def dumps(v: Any) -> str:
    return json.dumps(v, sort_keys=True, separators=(",", ":"))


class Runtime:
    """Small durable runtime used only by the public synthetic demo."""

    def __init__(self, db_path: str | Path):
        self.db = sqlite3.connect(str(db_path))
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS events(id TEXT PRIMARY KEY, kind TEXT, payload TEXT, status TEXT, source TEXT);
        CREATE TABLE IF NOT EXISTS cases(id TEXT PRIMARY KEY, state TEXT, claims TEXT, facts TEXT, authority TEXT, next_step TEXT);
        CREATE TABLE IF NOT EXISTS actions(id TEXT PRIMARY KEY, case_id TEXT, kind TEXT, status TEXT, attempts INTEGER, result TEXT);
        CREATE TABLE IF NOT EXISTS approvals(case_id TEXT PRIMARY KEY, actor TEXT, status TEXT);
        CREATE TABLE IF NOT EXISTS external_state(case_id TEXT PRIMARY KEY, value TEXT);
        CREATE TABLE IF NOT EXISTS audit(seq INTEGER PRIMARY KEY AUTOINCREMENT, case_id TEXT, at TEXT, actor TEXT, event TEXT, detail TEXT);
        """)
        self.db.commit()

    def audit(self, case_id: str, actor: str, event: str, detail: dict[str, Any]) -> None:
        self.db.execute("INSERT INTO audit(case_id,at,actor,event,detail) VALUES (?,?,?,?,?)", (case_id, "demo-clock", actor, event, dumps(detail)))
        self.db.commit()

    def receive(self, event_id: str, kind: str, payload: dict[str, Any], source: str = "synthetic-input") -> dict[str, Any]:
        if self.db.execute("SELECT 1 FROM events WHERE id=?", (event_id,)).fetchone():
            self.audit(payload.get("case_id", event_id), "runtime", "duplicate-rejected", {"event_id": event_id})
            return {"accepted": False, "reason": "DUPLICATE"}
        self.db.execute("INSERT INTO events VALUES (?,?,?,?,?)", (event_id, kind, dumps(payload), "RECEIVED", source))
        self.db.commit()
        self.audit(payload.get("case_id", event_id), "runtime", "received", {"event_id": event_id, "source": source})
        return {"accepted": True, "event_id": event_id}

    def case(self, case_id: str, **values: Any) -> None:
        old = self.db.execute("SELECT * FROM cases WHERE id=?", (case_id,)).fetchone()
        current = {"state": "NEW", "claims": {}, "facts": {}, "authority": {}, "next_step": "inspect"}
        if old:
            current.update({k: json.loads(old[k]) if k in {"claims", "facts", "authority"} else old[k] for k in ("state", "claims", "facts", "authority", "next_step")})
        current.update(values)
        self.db.execute("INSERT OR REPLACE INTO cases VALUES (?,?,?,?,?,?)", (case_id, current["state"], dumps(current["claims"]), dumps(current["facts"]), dumps(current["authority"]), current["next_step"]))
        self.db.commit()

    def approval(self, case_id: str, actor: str) -> dict[str, Any]:
        if actor not in {"reviewer", "approver"}:
            self.audit(case_id, actor, "approval-blocked", {"reason": "unauthorized"})
            return {"approved": False, "reason": "UNAUTHORIZED"}
        self.db.execute("INSERT OR REPLACE INTO approvals VALUES (?,?,?)", (case_id, actor, "APPROVED")); self.db.commit()
        self.audit(case_id, actor, "approval-granted", {"scope": "demo action"})
        self.case(case_id, state="READY", authority={"approved_by": actor}, next_step="execute")
        return {"approved": True, "actor": actor}

    def action(self, case_id: str, kind: str, failure: str | None = None) -> dict[str, Any]:
        action_id = hashlib.sha256(f"{case_id}:{kind}".encode()).hexdigest()[:12]
        row = self.db.execute("SELECT * FROM actions WHERE id=?", (action_id,)).fetchone()
        if row and row["status"] == "VERIFIED":
            self.audit(case_id, "runtime", "duplicate-action-blocked", {"action": kind})
            return {"status": "ALREADY_VERIFIED", "action_id": action_id}
        attempts = (row["attempts"] if row else 0) + 1
        if not row:
            self.db.execute("INSERT INTO actions VALUES (?,?,?,?,?,?)", (action_id, case_id, kind, "STARTED", attempts, None))
        else:
            self.db.execute("UPDATE actions SET status=?,attempts=? WHERE id=?", ("STARTED", attempts, action_id))
        self.db.commit()
        self.db.execute("INSERT OR REPLACE INTO external_state VALUES (?,?)", (case_id, dumps({"action": kind, "executed": True}))); self.db.commit()
        if failure == "response_lost" and attempts == 1:
            self.db.execute("UPDATE actions SET status=?,result=? WHERE id=?", ("AMBIGUOUS", dumps({"response": "lost"}), action_id)); self.db.commit()
            self.audit(case_id, "external-system", "response-lost", {"action": kind})
            return {"status": "AMBIGUOUS", "action_id": action_id}
        readback = self.db.execute("SELECT value FROM external_state WHERE case_id=?", (case_id,)).fetchone()
        result = {"readback": json.loads(readback[0]) if readback else None, "attempts": attempts}
        self.db.execute("UPDATE actions SET status=?,result=? WHERE id=?", ("VERIFIED", dumps(result), action_id)); self.db.commit()
        self.audit(case_id, "runtime", "readback-verified", result)
        return {"status": "VERIFIED", "action_id": action_id, **result}

    def views(self, case_id: str) -> dict[str, Any]:
        case = self.db.execute("SELECT * FROM cases WHERE id=?", (case_id,)).fetchone()
        actions = [dict(r) for r in self.db.execute("SELECT id,kind,status,attempts,result FROM actions WHERE case_id=?", (case_id,))]
        timeline = [dict(r) for r in self.db.execute("SELECT at,actor,event,detail FROM audit WHERE case_id=? ORDER BY seq", (case_id,))]
        if not case:
            return {"operator": {}, "reviewer": {}, "audit": timeline}
        claims, facts, authority = map(json.loads, (case["claims"], case["facts"], case["authority"]))
        return {
            "operator": {"state": case["state"], "next": case["next_step"], "actions": actions},
            "reviewer": {"claims": claims, "verified_facts": facts, "authority": authority},
            "audit": timeline,
        }

    def close(self) -> None:
        self.db.close()

