from datetime import date, timedelta
from pathlib import Path

import pytest
from textual.content import Content

from nokkam.app import NokkamApp
from nokkam.config import AppConfig
from nokkam.data.db import connect
from nokkam.data.migrations import apply_migrations
from nokkam.data.repositories.time_log_repository import TimeLogRepository
from nokkam.domain.models import Task
from nokkam.presentation.charts import column_chart, hbar
from nokkam.presentation.screens.time_report_screen import (
    EMPTY,
    TimeReportScreen,
    render_time_report,
)
from nokkam.services.project_summary_service import compact_minutes
from nokkam.services.time_report_service import DAILY_WINDOW, compute_time_report

TODAY = date(2026, 7, 27)


def make_app(tmp_path: Path) -> NokkamApp:
    return NokkamApp(config=AppConfig(db_path=tmp_path / "data.db"))


def log(app: NokkamApp, task_id: int, days_ago: int, minutes: int, base: date = TODAY) -> None:
    day = base - timedelta(days=days_ago)
    end = 9 * 60 + minutes
    with app.db:
        app.db.execute(
            "INSERT INTO time_log (task_id, start_at, end_at) VALUES (?, ?, ?)",
            (task_id, f"{day} 09:00:00", f"{day} {end // 60:02d}:{end % 60:02d}:00"),
        )


def plain(markup: str) -> str:
    return Content.from_markup(markup).plain


def report(app: NokkamApp, days: int | None):
    return compute_time_report(
        app.task_service, app.project_repo, app.time_log_repo, days, today=TODAY
    )


# ---- chart helpers ----


def test_hbar_scales_and_pads() -> None:
    assert hbar(10, 10, 8) == "████████"
    assert hbar(5, 10, 8) == "████░░░░"
    assert hbar(0, 10, 8) == "░" * 8
    assert hbar(5, 0, 8) == "░" * 8
    assert len(hbar(3.3, 10, 8)) == 8


def test_hbar_uses_partial_blocks_and_never_hides_small_values() -> None:
    assert hbar(1.5, 8, 8) == "█▌░░░░░░"  # 1.5 cells = one full + a half
    assert hbar(0.001, 100, 10).startswith("▏")


def test_column_chart_shape_and_scaling() -> None:
    rows = column_chart([0, 4, 8], height=2, col_width=1, gap=1)
    # zero draws nothing; half the peak fills the bottom row; the peak fills both
    assert rows == ["    █", "  █ █"]


def test_column_chart_slivers_and_all_zero() -> None:
    (row,) = column_chart([1, 1000], height=1)
    assert row[0] == "▁" and row[1] == "█"
    assert column_chart([0, 0], height=3) == ["", "", ""]
    assert column_chart([], height=2) == ["", ""]


@pytest.mark.parametrize(
    ("minutes", "label"),
    [
        (0, ""),
        (5, "5m"),
        (59, "59m"),
        (60, "1h"),
        (90, "1.5h"),
        (125, "2.1h"),
        (599, "10h"),
        (600, "10h"),
        (1500, "25h"),
    ],
)
def test_compact_minutes(minutes: int, label: str) -> None:
    assert compact_minutes(minutes) == label
    assert len(label) <= 4


# ---- repository ----


def test_minutes_by_task_and_day(tmp_path: Path) -> None:
    conn = connect(tmp_path / "data.db")
    apply_migrations(conn)
    conn.execute("INSERT INTO task (title) VALUES ('a')")
    conn.execute("INSERT INTO task (title) VALUES ('b')")
    conn.execute(
        "INSERT INTO time_log (task_id, start_at, end_at) VALUES "
        "(1, '2026-07-01 09:00:00', '2026-07-01 10:00:00'),"
        "(1, '2026-07-01 14:00:00', '2026-07-01 14:30:00'),"
        "(1, '2026-07-02 09:00:00', '2026-07-02 09:15:00'),"
        "(2, '2026-07-01 09:00:00', '2026-07-01 09:45:00')"
    )
    repo = TimeLogRepository(conn)
    rows = {(t, d): round(m) for t, d, m in repo.minutes_by_task_and_day()}
    assert rows == {(1, "2026-07-01"): 90, (1, "2026-07-02"): 15, (2, "2026-07-01"): 45}
    since = {(t, d) for t, d, _ in repo.minutes_by_task_and_day("2026-07-02")}
    assert since == {(1, "2026-07-02")}
    conn.close()


# ---- service ----


async def test_report_groups_by_project_within_the_window(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test():
        work = app.project_repo.get_or_create("Work")
        home = app.project_repo.get_or_create("Home")
        a = app.task_service.add_task(Task(title="a", project_id=work))
        b = app.task_service.add_task(Task(title="b", project_id=home))
        c = app.task_service.add_task(Task(title="loose"))
        log(app, a.id, 0, 60)
        log(app, a.id, 6, 30)
        log(app, a.id, 7, 500)  # outside 7 days
        log(app, b.id, 2, 45)
        log(app, c.id, 1, 10)

        week = report(app, 7)
        assert [(p.name, p.minutes) for p in week.projects] == [
            ("Work", 90),
            ("Home", 45),
            ("No project", 10),
        ]
        assert week.total_minutes == 145
        assert week.average_per_day == round(145 / 7)
        assert next(p.name for p in report(app, 30).projects) == "Work"
        assert report(app, 30).projects[0].minutes == 590


async def test_all_time_average_spans_from_the_first_log(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test():
        task = app.task_service.add_task(Task(title="a"))
        log(app, task.id, 9, 100)  # first log 10 days ago inclusive
        assert report(app, None).average_per_day == 10
        assert report(app, None).total_minutes == 100


async def test_daily_series_is_zero_filled_and_ends_today(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test():
        task = app.task_service.add_task(Task(title="a"))
        log(app, task.id, 0, 30)
        log(app, task.id, 2, 45)

        week = report(app, 7)
        assert len(week.daily) == 7
        assert week.daily[-1] == (TODAY, 30)
        assert week.daily[0][0] == TODAY - timedelta(days=6)
        assert dict(week.daily)[TODAY - timedelta(days=2)] == 45
        assert dict(week.daily)[TODAY - timedelta(days=1)] == 0
        assert len(report(app, 30).daily) == DAILY_WINDOW
        assert len(report(app, None).daily) == DAILY_WINDOW


async def test_empty_and_orphaned_time(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test():
        empty = report(app, 7)
        assert empty.projects == [] and empty.total_minutes == 0 and empty.average_per_day == 0

        task = app.task_service.add_task(Task(title="a"))
        log(app, task.id, 0, 20)
        app.task_service.delete_task(task.id)  # time logs cascade away with the task
        assert report(app, 7).total_minutes == 0


# ---- rendering ----


async def seeded_report(app: NokkamApp, days: int | None):
    work = app.project_repo.get_or_create("Work")
    home = app.project_repo.get_or_create("Home")
    a = app.task_service.add_task(Task(title="a", project_id=work))
    b = app.task_service.add_task(Task(title="b", project_id=home))
    for ago, minutes in [(0, 200), (1, 30), (3, 90)]:
        log(app, a.id, ago, minutes)
    log(app, b.id, 2, 60)
    return report(app, days)


async def test_weekly_render_has_bars_columns_and_accurate_labels(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test():
        text = plain(render_time_report(await seeded_report(app, 7)))
        assert "last 7 days" in text
        assert "total 6h 20m" in text
        assert "Work" in text and "Home" in text
        assert "84%" in text and "16%" in text  # 320 and 60 of 380 minutes
        assert "By day · last 7 days" in text
        assert "peak 3h 20m" in text
        assert "3.3h" in text and "30m" in text  # per-day labels aren't truncated
        assert "█" in text


async def test_monthly_render_uses_a_date_axis(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test():
        text = plain(render_time_report(await seeded_report(app, 30)))
        assert "last 30 days" in text and "By day · last 30 days" in text
        assert "Jun 28" in text and "Jul 27" in text  # first and last day of the axis


async def test_all_time_render_says_the_chart_is_the_last_30_days(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test():
        text = plain(render_time_report(await seeded_report(app, None)))
        assert "all time" in text and "By day · last 30 days" in text


def test_render_empty_period() -> None:
    from nokkam.services.time_report_service import TimeReport

    text = plain(render_time_report(TimeReport(7, [], [], 0, 0)))
    assert plain(EMPTY) in text and "last 7 days" in text


async def test_render_escapes_project_names(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test():
        odd = app.project_repo.get_or_create("[red]Odd[/]")
        task = app.task_service.add_task(Task(title="a", project_id=odd))
        log(app, task.id, 0, 30)
        assert "[red]Odd" in plain(render_time_report(report(app, 7)))


# ---- the screen ----


async def test_screen_switches_ranges_with_1_2_3(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        task = app.task_service.add_task(Task(title="a"))
        today = date.today()
        log(app, task.id, 0, 30, base=today)
        log(app, task.id, 20, 60, base=today)
        await pilot.pause()

        await pilot.press("T")
        await pilot.pause()
        assert isinstance(app.screen, TimeReportScreen)
        body = lambda: str(app.screen.query_one("#time-report-body").render())  # noqa: E731
        assert "last 7 days" in body() and "total 30m" in body()

        await pilot.press("2")
        await pilot.pause()
        assert "last 30 days" in body() and "1h 30m" in body()

        await pilot.press("3")
        await pilot.pause()
        assert "all time" in body()

        await pilot.press("1")
        await pilot.pause()
        assert "last 7 days" in body()

        await pilot.press("escape")
        await pilot.pause()
        assert not isinstance(app.screen, TimeReportScreen)


async def test_screen_opens_from_palette_and_shows_empty_state(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        assert "Time report" in [c.title for c in app.get_system_commands(app.screen)]
        app._cmd_open_time_report()
        await pilot.pause()
        assert isinstance(app.screen, TimeReportScreen)
        assert "No time tracked" in str(app.screen.query_one("#time-report-body").render())
