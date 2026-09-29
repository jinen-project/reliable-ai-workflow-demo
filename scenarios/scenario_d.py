"""Scenario D: a local, deterministic business-automation recovery fixture.

This module intentionally does not model a client's CRM, WhatsApp provider, or
predictive model.  It exercises the integration and recovery boundaries with
synthetic records and replaceable local adapters.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


class MockCRMAdapter:
    def __init__(self, db: sqlite3.Connection):
        self.db = db

    def upsert(self, case_id: str, payload: dict[str, Any], action_id: str, failure: str | None = None) -> dict[str, Any]:
        prior = self.db.execute("SELECT status, response FROM crm_actions WHERE action_id=?", (action_id,)).fetchone()
        if prior and prior[0] == "VERIFIED":
            return {"status": "ALREADY_VERIFIED", "action_id": action_id, "response": json.loads(prior[1])}
        if failure in {"crm_timeout", "rate_limit"} and not prior:
            status = "RATE_LIMITED" if failure == "rate_limit" else "TIMEOUT"
            self.db.execute("INSERT INTO crm_actions VALUES (?,?,?,?)", (action_id, case_id, status, _json({"error": status})))
            self.db.commit()
            return {"status": status, "action_id": action_id}
        response = {"case_id": case_id, "record_id": f"mock-crm:{case_id}", "updated": True, "source": "local-mock-crm"}
        if failure == "crm_response_lost" and not prior:
            self.db.execute("INSERT OR REPLACE INTO crm_actions VALUES (?,?,?,?)", (action_id, case_id, "AMBIGUOUS", _json(response)))
            self.db.commit()
            return {"status": "AMBIGUOUS", "action_id": action_id}
        self.db.execute("INSERT OR REPLACE INTO crm_actions VALUES (?,?,?,?)", (action_id, case_id, "VERIFIED", _json(response)))
        self.db.commit()
        return {"status": "VERIFIED", "action_id": action_id, "response": response}


class NotificationAdapter:
    def __init__(self, db: sqlite3.Connection):
        self.db = db

    def queue(self, case_id: str, message: str, action_id: str, failure: str | None = None) -> dict[str, Any]:
        prior = self.db.execute("SELECT status, response FROM notification_actions WHERE action_id=?", (action_id,)).fetchone()
        if prior and prior[0] == "VERIFIED":
            return {"status": "ALREADY_VERIFIED", "action_id": action_id, "response": json.loads(prior[1])}
        if failure == "notification_failure" and not prior:
            self.db.execute("INSERT INTO notification_actions VALUES (?,?,?,?)", (action_id, case_id, "FAILED", _json({"error": "DELIVERY_FAILED"})))
            self.db.commit()
            return {"status": "FAILED", "action_id": action_id}
        response = {"queued": True, "provider": "local-notification-sink", "message_length": len(message)}
        self.db.execute("INSERT OR REPLACE INTO notification_actions VALUES (?,?,?,?)", (action_id, case_id, "VERIFIED", _json(response)))
        self.db.commit()
        return {"status": "VERIFIED", "action_id": action_id, "response": response}


class ScenarioDRuntime:
    """Durable fixture runner; a new instance is the restart boundary."""

    def __init__(self, db_path: str | Path):
        self.db = sqlite3.connect(str(db_path))
        self.db.row_factory = sqlite3.Row
        self.db.executescript(
            """
            CREATE TABLE IF NOT EXISTS d_events(event_id TEXT PRIMARY KEY, case_id TEXT, payload_hash TEXT, version INTEGER, status TEXT, payload TEXT);
            CREATE TABLE IF NOT EXISTS d_cases(case_id TEXT PRIMARY KEY, state TEXT, classification TEXT, score REAL, confidence REAL, reason TEXT, next_step TEXT, claims TEXT, facts TEXT, version INTEGER);
            CREATE TABLE IF NOT EXISTS crm_actions(action_id TEXT PRIMARY KEY, case_id TEXT, status TEXT, response TEXT);
            CREATE TABLE IF NOT EXISTS notification_actions(action_id TEXT PRIMARY KEY, case_id TEXT, status TEXT, response TEXT);
            CREATE TABLE IF NOT EXISTS d_audit(seq INTEGER PRIMARY KEY AUTOINCREMENT, case_id TEXT, actor TEXT, event TEXT, detail TEXT);
            """
        )
        self.db.commit()

    def audit(self, case_id: str, actor: str, event: str, detail: dict[str, Any]) -> None:
        self.db.execute("INSERT INTO d_audit(case_id,actor,event,detail) VALUES (?,?,?,?)", (case_id, actor, event, _json(detail)))
        self.db.commit()

    def receive(self, event_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        case_id = str(payload.get("case_id", "unknown"))
        logical_payload = {k: v for k, v in payload.items() if k not in {"event_id", "delivery_id"}}
        payload_hash = hashlib.sha256(_json(logical_payload).encode()).hexdigest()
        existing = self.db.execute("SELECT event_id FROM d_events WHERE event_id=? OR payload_hash=?", (event_id, payload_hash)).fetchone()
        if existing:
            self.audit(case_id, "runtime", "duplicate-inbound-seen", {"event_id": event_id, "payload_hash": payload_hash})
            return {"status": "REPLAY", "event_id": event_id, "duplicate": True}
        version = int(payload.get("version", 1))
        current = self.db.execute("SELECT version FROM d_cases WHERE case_id=?", (case_id,)).fetchone()
        if current and version < current[0]:
            self.audit(case_id, "runtime", "out-of-order-ignored", {"version": version, "current_version": current[0]})
            return {"status": "OUT_OF_ORDER", "event_id": event_id}
        self.db.execute("INSERT INTO d_events VALUES (?,?,?,?,?,?)", (event_id, case_id, payload_hash, version, "RECEIVED", _json(payload)))
        self.db.commit()
        self.audit(case_id, "external-source", "inbound-received", {"event_id": event_id, "payload_hash": payload_hash})
        return {"status": "RECEIVED", "event_id": event_id}

    def classify(self, case_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        if payload.get("ai_failure") == "malformed":
            self.audit(case_id, "ai-classifier", "classification-malformed", {})
            self._save_case(case_id, "UNRESOLVED", "unknown", 0.0, 0.0, "malformed AI output", "manual-review", {}, {"input_received": True}, int(payload.get("version", 1)))
            return {"status": "UNRESOLVED", "reason": "MALFORMED_AI_OUTPUT"}
        missing = [field for field in ("name", "message") if not payload.get(field)]
        if missing:
            self._save_case(case_id, "BLOCKED_INCOMPLETE", "unknown", 0.0, 0.0, f"missing: {','.join(missing)}", "request-information", {"missing": missing}, {"input_received": True}, int(payload.get("version", 1)))
            self.audit(case_id, "validator", "validation-blocked", {"missing": missing})
            return {"status": "BLOCKED_INCOMPLETE", "missing": missing}
        high = bool(payload.get("risk_indicator")) or str(payload.get("message", "")).lower().find("urgent") >= 0
        classification = "manual_review" if high else "qualified"
        score = 0.42 if high else 0.86
        result = {"classification": classification, "score": score, "confidence": 0.80, "reason": "fixture rule: risk indicator" if high else "fixture rule: complete request"}
        self._save_case(case_id, "ROUTED_REVIEW" if high else "AUTO_CONTINUE", classification, score, result["confidence"], result["reason"], "human-review" if high else "crm-update", {"ai_result": result}, {"input_received": True, "validated": True}, int(payload.get("version", 1)))
        self.audit(case_id, "local-classifier", "classification-recorded", result)
        return {"status": "CLASSIFIED", **result, "reference_scoring_only": True}

    def _save_case(self, case_id: str, state: str, classification: str, score: float, confidence: float, reason: str, next_step: str, claims: dict[str, Any], facts: dict[str, Any], version: int) -> None:
        self.db.execute("INSERT OR REPLACE INTO d_cases VALUES (?,?,?,?,?,?,?,?,?,?)", (case_id, state, classification, score, confidence, reason, next_step, _json(claims), _json(facts), version))
        self.db.commit()

    def process(self, payload: dict[str, Any], failure: str | None = None) -> dict[str, Any]:
        case_id = str(payload["case_id"])
        event = self.receive(payload.get("event_id", f"event:{case_id}"), payload)
        if event["status"] not in {"RECEIVED", "REPLAY"}:
            return {"event": event, "state": "UNCHANGED"}
        classification = self.classify(case_id, payload)
        if classification["status"] != "CLASSIFIED":
            return {"event": event, "classification": classification, "state": classification["status"]}
        if classification["classification"] == "manual_review":
            self.audit(case_id, "router", "manual-review-required", {"reason": classification["reason"]})
            return {"event": event, "classification": classification, "state": "ROUTED_REVIEW"}
        crm_id = f"crm:{case_id}"
        crm = MockCRMAdapter(self.db).upsert(case_id, {"score": classification["score"]}, crm_id, failure=failure)
        self.audit(case_id, "mock-crm", "crm-action", crm)
        if crm["status"] not in {"VERIFIED", "ALREADY_VERIFIED"}:
            return {"event": event, "classification": classification, "crm": crm, "state": "RETRYABLE" if crm["status"] in {"TIMEOUT", "RATE_LIMITED", "AMBIGUOUS"} else "UNRESOLVED"}
        notification = NotificationAdapter(self.db).queue(case_id, f"Request {case_id} classified", f"notify:{case_id}", failure=failure)
        self.audit(case_id, "notification-sink", "notification-action", notification)
        state = "VERIFIED" if notification["status"] in {"VERIFIED", "ALREADY_VERIFIED"} else "RETRYABLE"
        self._save_case(case_id, state, classification["classification"], classification["score"], classification["confidence"], classification["reason"], "complete" if state == "VERIFIED" else "retry-notification", {"ai_result": classification}, {"input_received": True, "validated": True, "crm_readback": crm, "notification_readback": notification}, int(payload.get("version", 1)))
        return {"event": event, "classification": classification, "crm": crm, "notification": notification, "state": state}

    def views(self, case_id: str) -> dict[str, Any]:
        row = self.db.execute("SELECT * FROM d_cases WHERE case_id=?", (case_id,)).fetchone()
        events = [dict(r) for r in self.db.execute("SELECT event_id,status,version FROM d_events WHERE case_id=? ORDER BY rowid", (case_id,))]
        timeline = [dict(r) for r in self.db.execute("SELECT actor,event,detail FROM d_audit WHERE case_id=? ORDER BY seq", (case_id,))]
        if not row:
            return {"operator": {}, "reviewer": {}, "audit": timeline}
        claims, facts = json.loads(row["claims"]), json.loads(row["facts"])
        return {
            "operator": {"state": row["state"], "next": row["next_step"], "events": events},
            "reviewer": {"classification": row["classification"], "score": row["score"], "confidence": row["confidence"], "claims": claims, "verified_facts": facts, "reference_scoring_only": True},
            "audit": timeline,
        }

    def close(self) -> None:
        self.db.close()


def scenario_d(db_path: str, failure: str | None = "crm_response_lost") -> dict[str, Any]:
    payload = {"event_id": "d-event-1", "case_id": "business-automation-1", "version": 1, "name": "Synthetic Customer", "message": "Please route this request", "risk_indicator": False}
    runtime = ScenarioDRuntime(db_path)
    first = runtime.process(payload, failure=failure)
    runtime.close()
    restarted = ScenarioDRuntime(db_path)
    second = restarted.process({**payload, "event_id": "d-event-2"})
    views = restarted.views(payload["case_id"])
    restarted.close()
    return {"first": first, "after_restart": second, "views": views, "reference_scoring_only": True}
