from datetime import date, timedelta
from pathlib import Path

from nokkam.app import NokkamApp
from nokkam.config import AppConfig
from nokkam.data.db import connect
from nokkam.data.migrations import apply_migrations
from nokkam.data.repositories.time_log_repository import TimeLogRepository
from nokkam.domain.models import Status, Task
from nokkam.presentation.screens.project_summary_screen import ProjectSummaryScreen
from nokkam.services.project_summary_service import (
    compute_project_summaries,
    format_minutes,
)

TODAY = date(2026, 7, 27)


def make_app(tmp_path: Path) -> NokkamApp:
    return NokkamApp(config=AppConfig(db_path=tmp_path / "data.db"))


def log_time(app: NokkamApp, task_id: int, day: date, minutes: int) -> None:
    start = f"{day.isoformat()} 09:00:00"
    end_total = 9 * 60 + minutes
    end = f"{day.isoformat()} {end_total // 60:02d}:{end_total % 60:02d}:00"
    with app.db:
        app.db.execute(
            "INSERT INTO time_log (task_id, start_at, end_at) VALUES (?, ?, ?)",
            (task_id, start, end),
        )


def summaries(app: NokkamApp):
    return compute_project_summaries(
        app.task_service, app.project_repo, app.time_log_repo, today=TODAY
    )


async def test_counts_progress_overdue_and_no_project_row(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test():
        work = app.project_repo.get_or_create("Work")
        app.project_repo.get_or_create("Empty")
        yesterday = (TODAY - timedelta(days=1)).isoformat()
        app.task_service.add_task(Task(title="a", project_id=work, status=Status.DONE))
        app.task_service.add_task(Task(title="b", project_id=work, due_date=yesterday))
        app.task_service.add_task(Task(title="c", project_id=work))
        app.task_service.add_task(
            Task(title="old but done", project_id=work, status=Status.DONE, due_date=yesterday)
        )
        app.task_service.add_task(Task(title="loose"))

        by_name = {s.name: s for s in summaries(app)}
        assert list(by_name) == ["Empty", "Work", "No project"]
        work_row = by_name["Work"]
        assert (work_row.total, work_row.done, work_row.open, work_row.overdue) == (4, 2, 2, 1)
        assert work_row.progress == 0.5
        assert by_name["Empty"].total == 0 and by_name["Empty"].progress == 0.0
        assert by_name["No project"].total == 1


async def test_no_project_row_omitted_when_every_task_has_a_project(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test():
        work = app.project_repo.get_or_create("Work")
        app.task_service.add_task(Task(title="a", project_id=work))
        assert [s.name for s in summaries(app)] == ["Work"]


async def test_time_totals_and_recent_window(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test():
        work = app.project_repo.get_or_create("Work")
        home = app.project_repo.get_or_create("Home")
        t1 = app.task_service.add_task(Task(title="t1", project_id=work))
        t2 = app.task_service.add_task(Task(title="t2", project_id=work))
        t3 = app.task_service.add_task(Task(title="t3", project_id=home))
        loose = app.task_service.add_task(Task(title="loose"))

        log_time(app, t1.id, TODAY, 30)  # inside the window
        log_time(app, t2.id, TODAY - timedelta(days=6), 45)  # oldest day inside
        log_time(app, t2.id, TODAY - timedelta(days=7), 60)  # just outside
        log_time(app, t3.id, TODAY - timedelta(days=30), 20)
        log_time(app, loose.id, TODAY, 10)

        by_name = {s.name: s for s in summaries(app)}
        assert (by_name["Work"].minutes_total, by_name["Work"].minutes_recent) == (135, 75)
        assert (by_name["Home"].minutes_total, by_name["Home"].minutes_recent) == (20, 0)
        assert (by_name["No project"].minutes_total, by_name["No project"].minutes_recent) == (
            10,
            10,
        )


def test_minutes_by_task_since_filter(tmp_path: Path) -> None:
    conn = connect(tmp_path / "data.db")
    apply_migrations(conn)
    conn.execute("INSERT INTO task (title) VALUES ('x')")
    conn.execute(
        "INSERT INTO time_log (task_id, start_at, end_at) VALUES "
        "(1, '2026-07-01 09:00:00', '2026-07-01 10:00:00'),"
        "(1, '2026-07-20 09:00:00', '2026-07-20 09:30:00')"
    )
    repo = TimeLogRepository(conn)
    assert round(repo.minutes_by_task()[1]) == 90
    assert round(repo.minutes_by_task("2026-07-10")[1]) == 30
    assert repo.minutes_by_task("2026-08-01") == {}
    conn.close()


def test_format_minutes() -> None:
    assert format_minutes(0) == "—"
    assert format_minutes(45) == "45m"
    assert format_minutes(60) == "1h"
    assert format_minutes(150) == "2h 30m"
    assert format_minutes(65) == "1h 05m"


async def test_screen_renders_rows_and_opens_from_binding_and_palette(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        work = app.project_repo.get_or_create("Work")
        task = app.task_service.add_task(Task(title="a", project_id=work, status=Status.DONE))
        app.task_service.add_task(Task(title="b", project_id=work))
        log_time(app, task.id, date.today(), 90)
        app.screen.refresh_all()
        await pilot.pause()

        await pilot.press("O")
        await pilot.pause()
        assert isinstance(app.screen, ProjectSummaryScreen)
        text = str(app.screen.query_one("#project-summary-body").render())
        assert "Work" in text
        assert "1/2" in text
        assert "50%" in text
        assert "1h 30m" in text

        await pilot.press("escape")
        await pilot.pause()
        assert not isinstance(app.screen, ProjectSummaryScreen)

        assert "Project summary" in [c.title for c in app.get_system_commands(app.screen)]
        app._cmd_open_project_summary()
        await pilot.pause()
        assert isinstance(app.screen, ProjectSummaryScreen)


async def test_screen_handles_no_projects_and_markup_in_names(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        await app.push_screen(ProjectSummaryScreen())
        await pilot.pause()
        assert "No projects yet" in str(app.screen.query_one("#project-summary-body").render())
        app.pop_screen()

        tricky = app.project_repo.get_or_create("[bold]Odd[/] name that is far too long to fit")
        app.task_service.add_task(Task(title="a", project_id=tricky))
        await app.push_screen(ProjectSummaryScreen())
        await pilot.pause()
        text = str(app.screen.query_one("#project-summary-body").render())
        assert "[bold]Odd" in text  # shown literally, not interpreted as markup
        assert "…" in text  # truncated to the name column
