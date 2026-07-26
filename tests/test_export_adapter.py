from pathlib import Path

from nokkam.data.db import connect
from nokkam.data.migrations import apply_migrations
from nokkam.data.repositories.tag_repository import TagRepository
from nokkam.data.repositories.task_repository import TaskRepository
from nokkam.domain.models import Task
from nokkam.infra.export_adapter import (
    export_csv,
    export_ics,
    export_json,
    import_csv,
    import_json,
)


def setup_repo(db_path: Path):
    conn = connect(db_path)
    apply_migrations(conn)
    return TaskRepository(conn), TagRepository(conn)


def test_json_round_trip_preserves_tags(tmp_path: Path) -> None:
    task_repo, tag_repo = setup_repo(tmp_path / "source.db")
    tag_ids = tag_repo.get_or_create_many(["home", "urgent"])
    task_repo.create(Task(title="Water plants", due_date="2026-08-01", tag_ids=tag_ids))

    out_path = tmp_path / "export.json"
    export_json(task_repo.list(), str(out_path), tag_repo)

    task_repo2, tag_repo2 = setup_repo(tmp_path / "target.db")
    count = import_json(str(out_path), task_repo2, tag_repo2)
    assert count == 1

    imported = task_repo2.list()[0]
    assert imported.title == "Water plants"
    assert imported.due_date == "2026-08-01"
    assert {t.name for t in tag_repo2.get_many(imported.tag_ids)} == {"home", "urgent"}


def test_csv_round_trip_preserves_tags(tmp_path: Path) -> None:
    task_repo, tag_repo = setup_repo(tmp_path / "source.db")
    tag_ids = tag_repo.get_or_create_many(["errand"])
    task_repo.create(Task(title="Buy milk", tag_ids=tag_ids))

    out_path = tmp_path / "export.csv"
    export_csv(task_repo.list(), str(out_path), tag_repo)

    task_repo2, tag_repo2 = setup_repo(tmp_path / "target.db")
    count = import_csv(str(out_path), task_repo2, tag_repo2)
    assert count == 1
    imported = task_repo2.list()[0]
    assert imported.title == "Buy milk"
    assert {t.name for t in tag_repo2.get_many(imported.tag_ids)} == {"errand"}


def test_ics_export_produces_valid_vtodo_block(tmp_path: Path) -> None:
    task_repo, _ = setup_repo(tmp_path / "source.db")
    task_repo.create(Task(title="Renew passport", due_date="2026-09-01"))

    out_path = tmp_path / "export.ics"
    export_ics(task_repo.list(), str(out_path))

    content = out_path.read_text()
    assert "BEGIN:VCALENDAR" in content
    assert "BEGIN:VTODO" in content
    assert "SUMMARY:Renew passport" in content
    assert "DUE:20260901" in content
    assert "END:VCALENDAR" in content


def test_ics_escapes_special_characters(tmp_path: Path) -> None:
    task_repo, _ = setup_repo(tmp_path / "source.db")
    task_repo.create(Task(title="Buy milk, eggs; bread"))

    out_path = tmp_path / "export.ics"
    export_ics(task_repo.list(), str(out_path))
    content = out_path.read_text()
    assert "Buy milk\\, eggs\\; bread" in content
