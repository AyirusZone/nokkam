from pathlib import Path

from nokkam.data.db import connect
from nokkam.data.migrations import apply_migrations
from nokkam.data.repositories.task_repository import TaskRepository
from nokkam.domain.models import Task
from nokkam.services.task_service import TaskService
from nokkam.services.undo import UndoStack


def make_service(db_path: Path) -> TaskService:
    conn = connect(db_path)
    apply_migrations(conn)
    return TaskService(TaskRepository(conn), UndoStack())


def test_tree_orders_children_after_parent(tmp_path: Path) -> None:
    service = make_service(tmp_path / "data.db")
    parent = service.add_task(Task(title="Plan trip"))
    service.add_task(Task(title="Book flight", parent_task_id=parent.id))
    service.add_task(Task(title="Book hotel", parent_task_id=parent.id))
    service.add_task(Task(title="Unrelated"))

    tree = service.list_tasks_tree()
    titles_depths = [(t.title, d) for t, d in tree]

    parent_index = titles_depths.index(("Plan trip", 0))
    assert titles_depths[parent_index + 1][1] == 1
    assert titles_depths[parent_index + 2][1] == 1
    child_titles = {titles_depths[parent_index + 1][0], titles_depths[parent_index + 2][0]}
    assert child_titles == {"Book flight", "Book hotel"}
    assert ("Unrelated", 0) in titles_depths


def test_grandchildren_get_depth_two(tmp_path: Path) -> None:
    service = make_service(tmp_path / "data.db")
    a = service.add_task(Task(title="A"))
    b = service.add_task(Task(title="B", parent_task_id=a.id))
    service.add_task(Task(title="C", parent_task_id=b.id))

    tree = service.list_tasks_tree()
    depths = {t.title: d for t, d in tree}
    assert depths["A"] == 0
    assert depths["B"] == 1
    assert depths["C"] == 2
