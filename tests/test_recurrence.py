from datetime import date
from pathlib import Path

from cad_tui.data.db import connect
from cad_tui.data.migrations import apply_migrations
from cad_tui.data.repositories.recurrence_repository import RecurrenceRepository
from cad_tui.data.repositories.task_repository import TaskRepository
from cad_tui.domain.models import Task
from cad_tui.domain.recurrence import RecurrenceRule, next_occurrence
from cad_tui.services.task_service import TaskService
from cad_tui.services.undo import UndoStack


def make_service(db_path: Path) -> tuple[TaskService, RecurrenceRepository]:
    conn = connect(db_path)
    apply_migrations(conn)
    recurrence_repo = RecurrenceRepository(conn)
    service = TaskService(TaskRepository(conn), UndoStack(), recurrence_repo)
    return service, recurrence_repo


def test_next_occurrence_daily() -> None:
    rule = RecurrenceRule(rule="daily", interval=1)
    assert next_occurrence(date(2026, 7, 25), rule) == date(2026, 7, 26)


def test_next_occurrence_weekly() -> None:
    rule = RecurrenceRule(rule="weekly", interval=1)
    assert next_occurrence(date(2026, 7, 25), rule) == date(2026, 8, 1)


def test_next_occurrence_monthly_clamps_short_month() -> None:
    rule = RecurrenceRule(rule="monthly", interval=1)
    assert next_occurrence(date(2026, 1, 31), rule) == date(2026, 2, 28)


def test_next_occurrence_respects_until() -> None:
    rule = RecurrenceRule(rule="daily", interval=1, until="2026-07-25")
    assert next_occurrence(date(2026, 7, 25), rule) is None


def test_completing_recurring_task_spawns_next(tmp_path: Path) -> None:
    service, recurrence_repo = make_service(tmp_path / "data.db")
    recurrence_id = recurrence_repo.create(RecurrenceRule(rule="daily", interval=1))
    task = service.add_task(
        Task(title="Water plants", due_date="2026-07-25", recurrence_id=recurrence_id)
    )

    service.toggle_complete(task.id)

    all_tasks = service.list_tasks()
    assert len(all_tasks) == 2
    original = next(t for t in all_tasks if t.id == task.id)
    assert original.status == "done"
    spawned = next(t for t in all_tasks if t.id != task.id)
    assert spawned.title == "Water plants"
    assert spawned.due_date == "2026-07-26"
    assert spawned.status == "open"
    assert spawned.recurrence_id == recurrence_id


def test_undo_completing_recurring_task_removes_spawned(tmp_path: Path) -> None:
    service, recurrence_repo = make_service(tmp_path / "data.db")
    recurrence_id = recurrence_repo.create(RecurrenceRule(rule="daily", interval=1))
    task = service.add_task(
        Task(title="Water plants", due_date="2026-07-25", recurrence_id=recurrence_id)
    )
    service.toggle_complete(task.id)
    assert len(service.list_tasks()) == 2

    service.undo_last()

    remaining = service.list_tasks()
    assert len(remaining) == 1
    assert remaining[0].status == "open"


def test_recurrence_count_cap_prevents_spawn(tmp_path: Path) -> None:
    service, recurrence_repo = make_service(tmp_path / "data.db")
    recurrence_id = recurrence_repo.create(RecurrenceRule(rule="daily", interval=1, count=1))
    task = service.add_task(
        Task(title="Once only", due_date="2026-07-25", recurrence_id=recurrence_id)
    )

    service.toggle_complete(task.id)

    assert len(service.list_tasks()) == 1
