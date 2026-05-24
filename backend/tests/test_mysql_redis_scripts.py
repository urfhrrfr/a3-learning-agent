import sqlite3

from scripts import migrate_sqlite_to_mysql as migration


def test_read_sqlite_records_validates_json_payloads(tmp_path):
    sqlite_path = tmp_path / "app.db"
    with sqlite3.connect(sqlite_path) as conn:
        conn.execute(
            "CREATE TABLE records (kind TEXT NOT NULL, id TEXT NOT NULL PRIMARY KEY, payload TEXT NOT NULL)"
        )
        conn.execute(
            "INSERT INTO records(kind, id, payload) VALUES (?, ?, ?)",
            ("profile", "student_demo", '{"id":"student_demo"}'),
        )
        conn.commit()

    records = migration.read_sqlite_records(sqlite_path)

    assert records == [("profile", "student_demo", '{"id":"student_demo"}')]
    assert migration.counts_by_kind(records) == {"profile": 1}


def test_compare_counts_reports_mismatched_kinds():
    errors = migration.compare_counts({"profile": 2, "job": 1}, {"profile": 1, "job": 1})

    assert errors == ["profile: sqlite=2, mysql=1"]


def test_compare_counts_allows_mysql_extra_records():
    errors = migration.compare_counts({"profile": 2, "resource": 1}, {"profile": 2, "resource": 2})

    assert errors == []
