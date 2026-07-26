from pathlib import Path

from cad_tui.data.db import connect
from cad_tui.data.migrations import apply_migrations

EXPECTED_TABLES = {
    "project",
    "tag",
    "recurrence",
    "task",
    "task_tag",
    "calendar",
    "event",
    "time_log",
    "reminder",
    "usage_log",
    "task_dependency",
}


def test_migrations_create_expected_schema(tmp_path: Path) -> None:
    conn = connect(tmp_path / "data.db")
    apply_migrations(conn)

    tables = {
        row["name"] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    assert tables >= EXPECTED_TABLES
    conn.close()


def test_migrations_idempotent_same_connection(tmp_path: Path) -> None:
    conn = connect(tmp_path / "data.db")
    v1 = apply_migrations(conn)
    v2 = apply_migrations(conn)
    assert v1 == v2 == 3
    conn.close()


def test_migrations_idempotent_across_connections(tmp_path: Path) -> None:
    db_path = tmp_path / "data.db"

    conn1 = connect(db_path)
    apply_migrations(conn1)
    conn1.close()

    conn2 = connect(db_path)
    version = apply_migrations(conn2)
    assert version == 3
    conn2.close()
