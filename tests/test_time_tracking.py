from pathlib import Path

from cad_tui.data.db import connect
from cad_tui.data.migrations import apply_migrations
from cad_tui.data.repositories.task_repository import TaskRepository
from cad_tui.data.repositories.time_log_repository import TimeLogRepository
from cad_tui.domain.models import Task
from cad_tui.services.time_tracking_service import TimeTrackingService


def make_service(db_path: Path):
    conn = connect(db_path)
    apply_migrations(conn)
    task_repo = TaskRepository(conn)
    service = TimeTrackingService(TimeLogRepository(conn))
    return service, task_repo


def test_toggle_starts_timer(tmp_path: Path) -> None:
    service, task_repo = make_service(tmp_path / "data.db")
    task_id = task_repo.create(Task(title="Focus work"))
    running = service.toggle(task_id)
    assert running is True
    assert service.active_task_id == task_id


def test_toggle_again_stops_timer(tmp_path: Path) -> None:
    service, task_repo = make_service(tmp_path / "data.db")
    task_id = task_repo.create(Task(title="Focus work"))
    service.toggle(task_id)
    running = service.toggle(task_id)
    assert running is False
    assert service.active_task_id is None


def test_starting_new_timer_stops_previous(tmp_path: Path) -> None:
    service, task_repo = make_service(tmp_path / "data.db")
    task1 = task_repo.create(Task(title="A"))
    task2 = task_repo.create(Task(title="B"))
    service.toggle(task1)
    service.toggle(task2)
    assert service.active_task_id == task2
    assert service.repo.active_for_task(task1) is None


def test_total_minutes_non_negative(tmp_path: Path) -> None:
    service, task_repo = make_service(tmp_path / "data.db")
    task_id = task_repo.create(Task(title="Focus work"))
    service.toggle(task_id)
    service.toggle(task_id)
    assert service.total_minutes(task_id) >= 0


def test_total_minutes_zero_for_untracked_task(tmp_path: Path) -> None:
    service, task_repo = make_service(tmp_path / "data.db")
    task_id = task_repo.create(Task(title="Untouched"))
    assert service.total_minutes(task_id) == 0
