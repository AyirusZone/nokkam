from datetime import date, timedelta
from pathlib import Path

from cad_tui.data.db import connect
from cad_tui.data.migrations import apply_migrations
from cad_tui.data.repositories.task_repository import TaskRepository
from cad_tui.domain.models import Task
from cad_tui.services.stats_service import build_heatmap_lines, daily_completion_counts
from cad_tui.services.task_service import TaskService
from cad_tui.services.undo import UndoStack


def make_service(db_path: Path) -> TaskService:
    conn = connect(db_path)
    apply_migrations(conn)
    return TaskService(TaskRepository(conn), UndoStack())


def test_daily_completion_counts_groups_by_day(tmp_path: Path) -> None:
    service = make_service(tmp_path / "data.db")
    t1 = service.add_task(Task(title="A"))
    t2 = service.add_task(Task(title="B"))
    service.toggle_complete(t1.id)
    service.toggle_complete(t2.id)

    counts = daily_completion_counts(service, since=date.today() - timedelta(days=30))
    assert counts[date.today().isoformat()] == 2


def test_daily_completion_counts_excludes_before_since(tmp_path: Path) -> None:
    service = make_service(tmp_path / "data.db")
    counts = daily_completion_counts(service, since=date.today() + timedelta(days=1))
    assert counts == {}


def test_heatmap_lines_shape() -> None:
    lines = build_heatmap_lines({}, weeks=12)
    assert len(lines) == 7
    assert all(len(line) == 12 for line in lines)


def test_heatmap_marks_higher_counts_with_denser_symbol() -> None:
    today = date(2026, 7, 25)
    counts = {today.isoformat(): 10}
    lines = build_heatmap_lines(counts, weeks=1, today=today)
    combined = "".join(lines)
    assert "█" in combined


def test_heatmap_empty_day_is_blank() -> None:
    today = date(2026, 7, 25)
    lines = build_heatmap_lines({}, weeks=1, today=today)
    assert "".join(lines).strip() == ""


def test_heatmap_today_appears_in_rightmost_column() -> None:
    today = date(2026, 7, 25)
    counts = {today.isoformat(): 3}
    lines = build_heatmap_lines(counts, weeks=4, today=today)
    last_column = "".join(line[-1] for line in lines)
    assert last_column.strip() != ""
