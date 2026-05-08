from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


DB_PATH = Path(__file__).resolve().parents[1] / "data" / "app.db"


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS records (kind TEXT NOT NULL, id TEXT NOT NULL PRIMARY KEY, payload TEXT NOT NULL)"
        )
        conn.commit()


def save_record(kind: str, record_id: str, payload: dict[str, Any]) -> None:
    init_db()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO records(kind, id, payload) VALUES (?, ?, ?)",
            (kind, record_id, json.dumps(payload, ensure_ascii=False)),
        )
        conn.commit()


def load_records(kind: str) -> list[dict[str, Any]]:
    init_db()
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute("SELECT payload FROM records WHERE kind = ?", (kind,)).fetchall()
    return [json.loads(row[0]) for row in rows]
