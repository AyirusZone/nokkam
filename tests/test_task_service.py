from pathlib import Path

from cad_tui.data.db import connect
from cad_tui.data.migrations import apply_migrations
from cad_tui.data.repositories.task_repository import TaskRepository
from cad_tui.domain.models import Status, Task
from cad_tui.services.task_service import TaskService
from cad_tui.services.undo import UndoStack


def make_service(db_path: Path) -> TaskService:
    conn = connect(db_path)
    apply_migrations(conn)
    return TaskService(TaskRepository(conn), UndoStack())


def test_undo_delete_restores_task(tmp_path: Path) -> None:
    service = make_service(tmp_path / "data.db")
    task = service.add_task(Task(title="Important"))
    service.delete_task(task.id)
    assert service.repo.get(task.id) is None

    label = service.undo_last()
    assert "delete" in label
    restored = service.repo.get(task.id)
    assert restored is not None
    assert restored.title == "Important"


def test_undo_edit_restores_previous_fields(tmp_path: Path) -> None:
    service = make_service(tmp_path / "data.db")
    task = service.add_task(Task(title="Draft", notes="v1"))
    service.update_task(task.id, title="Final", notes="v2")
    assert service.repo.get(task.id).title == "Final"

    service.undo_last()
    reverted = service.repo.get(task.id)
    assert reverted.title == "Draft"
    assert reverted.notes == "v1"


def test_undo_toggle_complete(tmp_path: Path) -> None:
    service = make_service(tmp_path / "data.db")
    task = service.add_task(Task(title="Task"))
    service.toggle_complete(task.id)
    assert service.repo.get(task.id).status == Status.DONE

    service.undo_last()
    assert service.repo.get(task.id).status == Status.OPEN


def test_undo_add_removes_task(tmp_path: Path) -> None:
    service = make_service(tmp_path / "data.db")
    task = service.add_task(Task(title="Oops"))
    service.undo_last()
    assert service.repo.get(task.id) is None


def test_undo_with_empty_stack_is_noop(tmp_path: Path) -> None:
    service = make_service(tmp_path / "data.db")
    assert service.undo_last() is None
