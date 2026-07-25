from pathlib import Path

from cad_tui.data.db import connect
from cad_tui.data.migrations import apply_migrations
from cad_tui.data.repositories.tag_repository import TagRepository
from cad_tui.data.repositories.task_repository import TaskRepository
from cad_tui.domain.models import Priority, Status, Task


def make_repo(db_path: Path) -> TaskRepository:
    conn = connect(db_path)
    apply_migrations(conn)
    return TaskRepository(conn)


def test_create_and_get(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "data.db")
    task_id = repo.create(Task(title="Buy milk", priority=Priority.HIGH))
    fetched = repo.get(task_id)
    assert fetched.title == "Buy milk"
    assert fetched.priority == Priority.HIGH
    assert fetched.status == Status.OPEN


def test_update_persists(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "data.db")
    task_id = repo.create(Task(title="Draft"))
    repo.update(task_id, title="Final", priority=Priority.LOW)
    fetched = repo.get(task_id)
    assert fetched.title == "Final"
    assert fetched.priority == Priority.LOW


def test_delete_removes_row(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "data.db")
    task_id = repo.create(Task(title="Temp"))
    repo.delete(task_id)
    assert repo.get(task_id) is None


def test_data_survives_new_connection(tmp_path: Path) -> None:
    """Simulates an app restart: data written in one connection must be
    readable from a fresh connection opened later."""
    db_path = tmp_path / "data.db"
    repo1 = make_repo(db_path)
    task_id = repo1.create(Task(title="Persisted"))
    repo1.conn.close()

    conn2 = connect(db_path)
    apply_migrations(conn2)
    repo2 = TaskRepository(conn2)
    fetched = repo2.get(task_id)
    assert fetched is not None
    assert fetched.title == "Persisted"


def test_tags_round_trip(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "data.db")
    tag_repo = TagRepository(repo.conn)
    tag_ids = tag_repo.get_or_create_many(["home", "urgent"])
    task_id = repo.create(Task(title="Tagged", tag_ids=tag_ids))
    assert sorted(repo.get(task_id).tag_ids) == sorted(tag_ids)


def test_restore_reinserts_with_original_id_and_tags(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "data.db")
    tag_repo = TagRepository(repo.conn)
    tag_ids = tag_repo.get_or_create_many(["errand"])
    task_id = repo.create(Task(title="Deleted then restored", tag_ids=tag_ids))
    deleted = repo.get(task_id)
    repo.delete(task_id)
    assert repo.get(task_id) is None

    repo.restore(deleted)
    restored = repo.get(task_id)
    assert restored.title == "Deleted then restored"
    assert restored.tag_ids == tag_ids
