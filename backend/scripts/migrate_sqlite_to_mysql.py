from __future__ import annotations

import argparse
import json
import os
import shutil
import sqlite3
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Iterable
from urllib.parse import parse_qs, unquote, urlparse


BACKEND_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SQLITE_PATH = BACKEND_ROOT / "data" / "app.db"
DEFAULT_ENV_PATH = BACKEND_ROOT / ".env"


def load_env_file(env_path: Path) -> None:
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), os.path.expandvars(value.strip()))


def mysql_url_from_env() -> str:
    return (os.getenv("MYSQL_URL") or os.getenv("DATABASE_URL") or "").strip()


def parse_mysql_url(url: str) -> dict:
    if not url.startswith(("mysql://", "mysql+pymysql://")):
        raise ValueError("MYSQL_URL must start with mysql:// or mysql+pymysql://")
    parsed = urlparse(url.replace("mysql+pymysql://", "mysql://", 1))
    query = parse_qs(parsed.query)
    database = (parsed.path or "/").lstrip("/")
    if not database:
        raise ValueError("MYSQL_URL must include a database name, for example /a3_learning")
    return {
        "host": parsed.hostname or "127.0.0.1",
        "port": parsed.port or 3306,
        "user": unquote(parsed.username or ""),
        "password": unquote(parsed.password or ""),
        "database": database,
        "charset": query.get("charset", ["utf8mb4"])[0],
    }


def mysql_connect(url: str):
    try:
        import pymysql  # type: ignore
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("pymysql is required. Install backend/requirements.txt first.") from exc
    return pymysql.connect(**parse_mysql_url(url), autocommit=False)


def ensure_mysql_table(conn) -> None:
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


def read_sqlite_records(sqlite_path: Path) -> list[tuple[str, str, str]]:
    if not sqlite_path.exists():
        raise FileNotFoundError(f"SQLite database not found: {sqlite_path}")
    with sqlite3.connect(sqlite_path) as conn:
        table = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'records'"
        ).fetchone()
        if table is None:
            raise RuntimeError(f"{sqlite_path} does not contain a records table")
        rows = conn.execute("SELECT kind, id, payload FROM records ORDER BY rowid ASC").fetchall()
    for kind, record_id, payload in rows:
        if not kind or not record_id:
            raise RuntimeError("SQLite records table contains an empty kind or id")
        json.loads(payload)
    return [(str(kind), str(record_id), str(payload)) for kind, record_id, payload in rows]


def counts_by_kind(records: Iterable[tuple[str, str, str]]) -> Counter[str]:
    return Counter(kind for kind, _record_id, _payload in records)


def mysql_counts(conn) -> Counter[str]:
    with conn.cursor() as cursor:
        cursor.execute("SELECT kind, COUNT(*) FROM records GROUP BY kind")
        rows = cursor.fetchall()
    return Counter({str(kind): int(count) for kind, count in rows})


def backup_sqlite(sqlite_path: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = sqlite_path.with_name(f"{sqlite_path.name}.bak-{timestamp}")
    shutil.copy2(sqlite_path, backup_path)
    return backup_path


def upsert_records(conn, records: list[tuple[str, str, str]]) -> None:
    with conn.cursor() as cursor:
        cursor.executemany(
            """
            INSERT INTO records(kind, id, payload)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE
                payload = VALUES(payload),
                updated_at = CURRENT_TIMESTAMP
            """,
            records,
        )
    conn.commit()


def compare_counts(source: Counter[str], target: Counter[str]) -> list[str]:
    errors: list[str] = []
    for kind, expected in sorted(source.items()):
        actual = target.get(kind, 0)
        if actual < expected:
            errors.append(f"{kind}: sqlite={expected}, mysql={actual}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate backend/data/app.db records to MySQL.")
    parser.add_argument("--sqlite-path", type=Path, default=DEFAULT_SQLITE_PATH)
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_PATH)
    parser.add_argument("--mysql-url", default="")
    parser.add_argument("--dry-run", action="store_true", help="Read and validate SQLite only; do not connect to MySQL.")
    parser.add_argument("--verify-only", action="store_true", help="Compare SQLite and MySQL counts without writing.")
    parser.add_argument("--skip-backup", action="store_true", help="Do not create an app.db backup before writing.")
    args = parser.parse_args()

    load_env_file(args.env_file)
    records = read_sqlite_records(args.sqlite_path)
    source_counts = counts_by_kind(records)
    print(f"SQLite source: {args.sqlite_path}")
    print(f"SQLite records: {sum(source_counts.values())}")
    for kind, count in sorted(source_counts.items()):
        print(f"  {kind}: {count}")

    if args.dry_run:
        print("Dry run complete: SQLite records are readable and JSON payloads are valid.")
        return 0

    mysql_url = (args.mysql_url or mysql_url_from_env()).strip()
    if not mysql_url:
        print("ERROR: MYSQL_URL or DATABASE_URL is required for migration.", file=sys.stderr)
        return 2

    with mysql_connect(mysql_url) as conn:
        ensure_mysql_table(conn)
        if args.verify_only:
            target_counts = mysql_counts(conn)
        else:
            if not args.skip_backup:
                backup_path = backup_sqlite(args.sqlite_path)
                print(f"SQLite backup created: {backup_path}")
            upsert_records(conn, records)
            target_counts = mysql_counts(conn)

    errors = compare_counts(source_counts, target_counts)
    if errors:
        print("ERROR: MySQL count verification failed:", file=sys.stderr)
        for error in errors:
            print(f"  {error}", file=sys.stderr)
        return 1

    print("MySQL verification passed.")
    for kind, count in sorted(source_counts.items()):
        print(f"  {kind}: {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
