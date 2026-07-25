from datetime import date, timedelta
from pathlib import Path

from cad_tui.data.db import connect
from cad_tui.data.migrations import apply_migrations
from cad_tui.data.repositories.task_repository import TaskRepository
from cad_tui.domain.models import Task
from cad_tui.services.stats_service import compute_stats
from cad_tui.services.task_service import TaskService
from cad_tui.services.undo import UndoStack


def make_service(db_path: Path) -> TaskService:
    conn = connect(db_path)
    apply_migrations(conn)
    return TaskService(TaskRepository(conn), UndoStack())


def test_compute_stats_counts_and_rate(tmp_path: Path) -> None:
    service = make_service(tmp_path / "data.db")
    t1 = service.add_task(Task(title="A"))
    t2 = service.add_task(Task(title="B"))
    service.add_task(Task(title="C"))
    service.toggle_complete(t1.id)
    service.toggle_complete(t2.id)

    stats = compute_stats(service)
    assert stats.total == 3
    assert stats.done == 2
    assert stats.open == 1
    assert stats.completion_rate == 2 / 3


def test_compute_stats_overdue_counts_open_past_due(tmp_path: Path) -> None:
    service = make_service(tmp_path / "data.db")
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    service.add_task(Task(title="Late", due_date=yesterday))
    service.add_task(Task(title="OK"))

    stats = compute_stats(service)
    assert stats.overdue == 1


def test_compute_stats_streak_counts_today_as_one(tmp_path: Path) -> None:
    service = make_service(tmp_path / "data.db")
    t1 = service.add_task(Task(title="A"))
    service.toggle_complete(t1.id)

    stats = compute_stats(service)
    assert stats.streak_days == 1


def test_compute_stats_empty_db(tmp_path: Path) -> None:
    service = make_service(tmp_path / "data.db")
    stats = compute_stats(service)
    assert stats.total == 0
    assert stats.completion_rate == 0.0
    assert stats.streak_days == 0
