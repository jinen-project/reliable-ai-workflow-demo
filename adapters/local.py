from __future__ import annotations
import os
from typing import Any


class ReadOnlyMCP:
    """Synthetic REST/MCP-shaped adapter. It never performs writes."""

    def __init__(self):
        self.api_key = os.environ.get("DEMO_API_KEY")

    def list_items(self, query: str = "") -> dict[str, Any]:
        return {"ok": True, "data": [{"id": "item-1", "label": "synthetic result", "query": query}], "source": "local-read-only-api", "error": None}


class LocalCRM:
    def upsert(self, case_id: str, facts: dict[str, Any]) -> dict[str, Any]:
        return {"case_id": case_id, "stored": True, "source": "local-crm-fixture", "facts": facts}


class LocalMailSink:
    def queue(self, case_id: str, recipient: str) -> dict[str, Any]:
        return {"case_id": case_id, "status": "ACCEPTED_BY_LOCAL_SINK", "recipient": recipient}
