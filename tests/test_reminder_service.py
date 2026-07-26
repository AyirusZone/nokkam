from datetime import datetime, timedelta
from pathlib import Path

from nokkam.data.db import connect
from nokkam.data.migrations import apply_migrations
from nokkam.data.repositories.reminder_repository import ReminderRepository
from nokkam.data.repositories.task_repository import TaskRepository
from nokkam.domain.models import Task
from nokkam.services.reminder_service import ReminderService
from nokkam.services.task_service import TaskService
from nokkam.services.undo import UndoStack


def make_services(db_path: Path) -> tuple[TaskService, ReminderService]:
    conn = connect(db_path)
    apply_migrations(conn)
    task_service = TaskService(TaskRepository(conn), UndoStack())
    reminder_service = ReminderService(task_service, ReminderRepository(conn))
    return task_service, reminder_service


def test_task_due_in_10_minutes_is_flagged(tmp_path: Path) -> None:
    task_service, reminder_service = make_services(tmp_path / "data.db")
    now = datetime(2026, 7, 25, 9, 0)
    due = now + timedelta(minutes=10)
    task_service.add_task(
        Task(title="Standup", due_date=due.date().isoformat(), due_time=due.strftime("%H:%M"))
    )

    due_tasks = reminder_service.due_soon(now=now)
    assert [t.title for t in due_tasks] == ["Standup"]


def test_task_due_in_30_minutes_not_flagged_within_default_window(tmp_path: Path) -> None:
    task_service, reminder_service = make_services(tmp_path / "data.db")
    now = datetime(2026, 7, 25, 9, 0)
    due = now + timedelta(minutes=30)
    task_service.add_task(
        Task(title="Later", due_date=due.date().isoformat(), due_time=due.strftime("%H:%M"))
    )

    assert reminder_service.due_soon(now=now) == []


def test_same_task_not_flagged_twice(tmp_path: Path) -> None:
    task_service, reminder_service = make_services(tmp_path / "data.db")
    now = datetime(2026, 7, 25, 9, 0)
    due = now + timedelta(minutes=5)
    task_service.add_task(
        Task(title="Standup", due_date=due.date().isoformat(), due_time=due.strftime("%H:%M"))
    )

    first = reminder_service.due_soon(now=now)
    second = reminder_service.due_soon(now=now)
    assert len(first) == 1
    assert second == []


def test_task_without_due_date_never_flagged(tmp_path: Path) -> None:
    task_service, reminder_service = make_services(tmp_path / "data.db")
    task_service.add_task(Task(title="No date"))
    assert reminder_service.due_soon(now=datetime(2026, 7, 25, 9, 0)) == []


def test_past_due_task_not_flagged(tmp_path: Path) -> None:
    task_service, reminder_service = make_services(tmp_path / "data.db")
    now = datetime(2026, 7, 25, 9, 0)
    past = now - timedelta(minutes=5)
    task_service.add_task(
        Task(title="Overdue", due_date=past.date().isoformat(), due_time=past.strftime("%H:%M"))
    )
    assert reminder_service.due_soon(now=now) == []


def test_done_task_not_flagged(tmp_path: Path) -> None:
    task_service, reminder_service = make_services(tmp_path / "data.db")
    now = datetime(2026, 7, 25, 9, 0)
    due = now + timedelta(minutes=5)
    task = task_service.add_task(
        Task(title="Standup", due_date=due.date().isoformat(), due_time=due.strftime("%H:%M"))
    )
    task_service.toggle_complete(task.id)
    assert reminder_service.due_soon(now=now) == []
