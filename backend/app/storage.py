from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from urllib.parse import parse_qs, urlparse, unquote
from typing import Any

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "app.db"


def database_url() -> str:
    return (os.getenv("MYSQL_URL") or os.getenv("DATABASE_URL") or "").strip()


def _is_mysql_url(url: str) -> bool:
    return url.startswith(("mysql://", "mysql+pymysql://"))


def _use_mysql() -> bool:
    url = database_url()
    if not url:
        return False
    if not _is_mysql_url(url):
        raise RuntimeError("MYSQL_URL or DATABASE_URL must start with mysql:// or mysql+pymysql://")
    return True


def _require_mysql_url() -> str:
    url = database_url()
    if not _is_mysql_url(url):
        raise RuntimeError("MYSQL_URL or DATABASE_URL must start with mysql:// or mysql+pymysql://")
    return url


def _mysql_connect():
    url = _require_mysql_url()
    parsed = urlparse(url.replace("mysql+pymysql://", "mysql://", 1))
    query = parse_qs(parsed.query)
    charset = query.get("charset", ["utf8mb4"])[0]
    try:
        import pymysql  # type: ignore
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("pymysql package is required for MySQL storage") from exc
    return pymysql.connect(
        host=parsed.hostname or "127.0.0.1",
        port=parsed.port or 3306,
        user=unquote(parsed.username or ""),
        password=unquote(parsed.password or ""),
        database=(parsed.path or "/").lstrip("/"),
        charset=charset,
        autocommit=False,
    )


def init_db() -> None:
    if not _use_mysql():
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS records (
                    kind TEXT NOT NULL,
                    id TEXT NOT NULL PRIMARY KEY,
                    payload TEXT NOT NULL
                )
                """
            )
        return

    with _mysql_connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS records (
                    row_pk BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
                    kind VARCHAR(64) NOT NULL,
                    id VARCHAR(191) NOT NULL,
                    payload LONGTEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY uq_records_kind_id (kind, id),
                    KEY idx_records_kind_updated (kind, updated_at, row_pk)
                ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
                """
            )
        conn.commit()


def save_record(kind: str, record_id: str, payload: dict[str, Any]) -> None:
    init_db()
    payload_json = json.dumps(payload, ensure_ascii=False)
    if not _use_mysql():
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO records(kind, id, payload) VALUES (?, ?, ?)",
                (kind, record_id, payload_json),
            )
        return

    with _mysql_connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO records(kind, id, payload)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    payload = VALUES(payload),
                    updated_at = CURRENT_TIMESTAMP
                """,
                (kind, record_id, payload_json),
            )
        conn.commit()


def load_records(kind: str) -> list[dict[str, Any]]:
    init_db()
    if not _use_mysql():
        with sqlite3.connect(DB_PATH) as conn:
            rows = conn.execute("SELECT payload FROM records WHERE kind = ?", (kind,)).fetchall()
        return [json.loads(row[0]) for row in rows]

    with _mysql_connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT payload FROM records WHERE kind = %s ORDER BY updated_at ASC, row_pk ASC",
                (kind,),
            )
            rows = cursor.fetchall()
    return [json.loads(row[0]) for row in rows]


def load_latest_record(kind: str) -> dict[str, Any] | None:
    init_db()
    if not _use_mysql():
        with sqlite3.connect(DB_PATH) as conn:
            row = conn.execute(
                "SELECT payload FROM records WHERE kind = ? ORDER BY rowid DESC LIMIT 1",
                (kind,),
            ).fetchone()
        return json.loads(row[0]) if row else None

    with _mysql_connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT payload FROM records
                WHERE kind = %s
                ORDER BY updated_at DESC, row_pk DESC
                LIMIT 1
                """,
                (kind,),
            )
            row = cursor.fetchone()
    return json.loads(row[0]) if row else None


def delete_records(kind: str, record_ids: list[str] | None = None) -> None:
    init_db()
    if not _use_mysql():
        with sqlite3.connect(DB_PATH) as conn:
            if record_ids is None:
                conn.execute("DELETE FROM records WHERE kind = ?", (kind,))
            elif record_ids:
                placeholders = ",".join(["?"] * len(record_ids))
                conn.execute(
                    f"DELETE FROM records WHERE kind = ? AND id IN ({placeholders})",
                    (kind, *record_ids),
                )
        return

    with _mysql_connect() as conn:
        with conn.cursor() as cursor:
            if record_ids is None:
                cursor.execute("DELETE FROM records WHERE kind = %s", (kind,))
            elif record_ids:
                placeholders = ",".join(["%s"] * len(record_ids))
                cursor.execute(
                    f"DELETE FROM records WHERE kind = %s AND id IN ({placeholders})",
                    (kind, *record_ids),
                )
        conn.commit()


def status() -> dict[str, Any]:
    backend = "mysql" if database_url() else "sqlite"
    try:
        init_db()
    except Exception as exc:  # noqa: BLE001
        return {"backend": backend, "available": False, "reason": str(exc)}
    if backend == "sqlite":
        return {"backend": "sqlite", "available": True, "path": str(DB_PATH), "reason": ""}
    return {"backend": "mysql", "available": True, "reason": ""}
