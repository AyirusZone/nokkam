from pathlib import Path

from nokkam.data.db import connect
from nokkam.data.migrations import apply_migrations
from nokkam.data.repositories.task_repository import TaskRepository
from nokkam.data.repositories.time_log_repository import TimeLogRepository
from nokkam.domain.models import Task
from nokkam.services.time_tracking_service import TimeTrackingService


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


def test_toggle_pause_pauses_and_resumes(tmp_path: Path) -> None:
    service, task_repo = make_service(tmp_path / "data.db")
    task_id = task_repo.create(Task(title="Focus work"))
    service.toggle(task_id)

    paused = service.toggle_pause()
    assert paused is True
    assert service.is_paused is True
    assert service.active_task_id == task_id  # still active, just paused
    assert service.repo.active_for_task(task_id) is None  # segment closed

    resumed = service.toggle_pause()
    assert resumed is False
    assert service.is_paused is False
    assert service.repo.active_for_task(task_id) is not None  # new segment open


def test_toggle_pause_is_noop_when_nothing_active(tmp_path: Path) -> None:
    service, _task_repo = make_service(tmp_path / "data.db")
    assert service.toggle_pause() is None
    assert service.is_paused is False


def test_toggle_stops_timer_even_while_paused(tmp_path: Path) -> None:
    service, task_repo = make_service(tmp_path / "data.db")
    task_id = task_repo.create(Task(title="Focus work"))
    service.toggle(task_id)
    service.toggle_pause()

    running = service.toggle(task_id)
    assert running is False
    assert service.active_task_id is None
    assert service.is_paused is False


def test_start_at_uses_local_date_not_utc(tmp_path: Path) -> None:
    """Same UTC-vs-local class of bug as task.completed_at — see
    test_task_repository.test_completed_at_uses_local_date_not_utc."""
    from datetime import date

    service, task_repo = make_service(tmp_path / "data.db")
    task_id = task_repo.create(Task(title="Focus work"))
    service.toggle(task_id)

    conn = service.repo.conn
    row = conn.execute("SELECT start_at FROM time_log WHERE task_id = ?", (task_id,)).fetchone()
    assert row["start_at"][:10] == date.today().isoformat()
