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


def load_latest_record(kind: str) -> dict[str, Any] | None:
    init_db()
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "SELECT payload FROM records WHERE kind = ? ORDER BY rowid DESC LIMIT 1",
            (kind,),
        ).fetchone()
    return json.loads(row[0]) if row else None


def delete_records(kind: str, record_ids: list[str] | None = None) -> None:
    init_db()
    with sqlite3.connect(DB_PATH) as conn:
        if record_ids is None:
            conn.execute("DELETE FROM records WHERE kind = ?", (kind,))
        elif record_ids:
            placeholders = ",".join("?" for _ in record_ids)
            conn.execute(f"DELETE FROM records WHERE kind = ? AND id IN ({placeholders})", (kind, *record_ids))
        conn.commit()
