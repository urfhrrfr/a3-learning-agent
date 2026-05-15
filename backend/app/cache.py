from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Any


DEFAULT_TTL_SECONDS = 60 * 60


def redis_url() -> str:
    return os.getenv("REDIS_URL", "").strip()


def is_enabled() -> bool:
    return bool(redis_url())


@lru_cache(maxsize=1)
def _redis_client():
    url = redis_url()
    if not url:
        return None
    try:
        import redis  # type: ignore
    except Exception:  # noqa: BLE001
        return None
    try:
        return redis.Redis.from_url(url, decode_responses=True)
    except Exception:  # noqa: BLE001
        return None


def reset_cache_client() -> None:
    _redis_client.cache_clear()


def cache_json(kind: str, record_id: str, payload: dict[str, Any], ttl_seconds: int = DEFAULT_TTL_SECONDS) -> bool:
    client = _redis_client()
    if client is None:
        return False
    try:
        client.setex(f"a3:{kind}:{record_id}", ttl_seconds, json.dumps(payload, ensure_ascii=False))
        return True
    except Exception:  # noqa: BLE001
        return False


def get_cached_json(kind: str, record_id: str) -> dict[str, Any] | None:
    client = _redis_client()
    if client is None:
        return None
    try:
        raw = client.get(f"a3:{kind}:{record_id}")
    except Exception:  # noqa: BLE001
        return None
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def cache_job(job_id: str, payload: dict[str, Any]) -> bool:
    return cache_json("job", job_id, payload)


def get_cached_job(job_id: str) -> dict[str, Any] | None:
    return get_cached_json("job", job_id)


def status() -> dict[str, Any]:
    url = redis_url()
    client = _redis_client()
    if not url:
        return {"enabled": False, "available": False, "reason": "REDIS_URL not configured"}
    if client is None:
        return {"enabled": True, "available": False, "reason": "redis package or client unavailable"}
    try:
        client.ping()
    except Exception as exc:  # noqa: BLE001
        return {"enabled": True, "available": False, "reason": str(exc)}
    return {"enabled": True, "available": True, "reason": ""}
