from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from ..storage import save_record


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def save_retrieval_log(
    *,
    scenario: str,
    query: str,
    profile_snapshot: dict,
    selected_sources: list[dict],
    job_id: str = "",
    user_id: str = "",
    request_context: dict | None = None,
    warnings: list[str] | None = None,
) -> dict:
    payload = {
        "id": f"retrieval_{uuid4().hex[:10]}",
        "scenario": scenario,
        "job_id": job_id,
        "user_id": user_id,
        "query": query,
        "profile_snapshot": profile_snapshot,
        "request_context": request_context or {},
        "selected_source_ids": [str(source.get("id", "")) for source in selected_sources if source.get("id")],
        "selected_sources": selected_sources,
        "warnings": warnings or [],
        "created_at": _now(),
    }
    save_record("retrieval_log", payload["id"], payload)
    return payload
