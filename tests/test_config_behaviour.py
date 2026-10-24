"""config.toml options that change what the app does (not just what's parsed)."""

from datetime import date, timedelta
from pathlib import Path

from textual.widgets import Select, Static

from nokkam.app import NokkamApp
from nokkam.cli import run_cli
from nokkam.config import AppConfig
from nokkam.domain.models import Priority, Task
from nokkam.presentation.screens.quick_add import QuickAddModal
from nokkam.presentation.screens.task_form import TaskFormModal
from nokkam.presentation.screens.task_list import TaskRow
from nokkam.presentation.widgets.app_header import AppHeader
from nokkam.presentation.widgets.calendar_grid import DayCell


def make_app(tmp_path: Path, **config) -> NokkamApp:
    return NokkamApp(config=AppConfig(db_path=tmp_path / "data.db", **config))


def weekday_labels(app: NokkamApp) -> list[str]:
    return [str(s.render()) for s in app.screen.query(".weekday-label").results(Static)]


async def test_calendar_week_starts_on_monday_by_default(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        assert weekday_labels(app) == ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        first_row = list(app.screen.query(".calendar-week-row").first().query(DayCell))
        assert {c.day.weekday() for c in first_row[:1]} == {0}


async def test_calendar_week_can_start_on_sunday(tmp_path: Path) -> None:
    app = make_app(tmp_path, first_weekday=6)
    async with app.run_test() as pilot:
        await pilot.pause()
        assert weekday_labels(app) == ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
        for row in app.screen.query(".calendar-week-row"):
            days = [c.day for c in row.query(DayCell)]
            assert days[0].weekday() == 6
            assert [d.weekday() for d in days] == [6, 0, 1, 2, 3, 4, 5]


async def test_weekend_styling_follows_the_real_weekday_not_the_column(tmp_path: Path) -> None:
    app = make_app(tmp_path, first_weekday=6)
    async with app.run_test() as pilot:
        await pilot.pause()
        for cell in app.screen.query(DayCell):
            assert cell.has_class("weekend") == (cell.day.weekday() in (5, 6))
        weekend_labels = [
            str(s.render()) for s in app.screen.query(".weekday-label.weekend").results(Static)
        ]
        assert sorted(weekend_labels) == ["Sat", "Sun"]


async def test_new_task_form_starts_at_configured_priority(tmp_path: Path) -> None:
    app = make_app(tmp_path, default_priority=Priority.LOW)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("a")
        await pilot.pause()
        assert isinstance(app.screen, TaskFormModal)
        assert app.screen.query_one("#priority", Select).value == Priority.LOW


async def test_editing_keeps_the_tasks_own_priority(tmp_path: Path) -> None:
    app = make_app(tmp_path, default_priority=Priority.LOW)
    async with app.run_test() as pilot:
        task = app.task_service.add_task(Task(title="Urgent", priority=Priority.HIGH))
        app.screen.refresh_all()
        await pilot.pause()
        app.screen.select_task_by_id(task.id)
        await pilot.pause()
        await pilot.press("e")
        await pilot.pause()
        assert app.screen.query_one("#priority", Select).value == Priority.HIGH


async def test_quick_add_uses_configured_priority(tmp_path: Path) -> None:
    app = make_app(tmp_path, default_priority=Priority.HIGH)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("A")
        await pilot.pause()
        assert isinstance(app.screen, QuickAddModal)
        app.screen.query_one("#quick-input").value = "Call bank"
        await pilot.press("enter")
        await pilot.pause()
        assert [(t.title, t.priority) for t in app.task_service.list_tasks()] == [
            ("Call bank", Priority.HIGH)
        ]


def test_cli_add_uses_configured_priority_unless_flag_given(tmp_path: Path) -> None:
    config = AppConfig(db_path=tmp_path / "data.db", default_priority=Priority.LOW)
    assert run_cli(["add", "from config"], config=config) == 0
    assert run_cli(["add", "explicit", "--priority", "high"], config=config) == 0

    from nokkam.data.db import connect
    from nokkam.data.repositories.task_repository import TaskRepository

    conn = connect(config.db_path)
    priorities = {t.title: t.priority for t in TaskRepository(conn).list()}
    conn.close()
    assert priorities == {"from config": Priority.LOW, "explicit": Priority.HIGH}


def test_cli_prints_config_warnings_to_stderr(tmp_path: Path, capsys) -> None:
    config = AppConfig(db_path=tmp_path / "data.db", warnings=["Unknown config option 'x'"])
    run_cli(["add", "hello"], config=config)
    assert "warning: Unknown config option 'x'" in capsys.readouterr().err


async def test_start_filter_with_a_builtin_smart_list(tmp_path: Path) -> None:
    app = make_app(tmp_path, start_filter="Today")
    async with app.run_test() as pilot:
        await pilot.pause()
        assert app.screen.smart_filter == "today"
        assert app.screen.query_one(AppHeader).meta == "Today"


async def test_start_filter_with_a_saved_filter(tmp_path: Path) -> None:
    config = AppConfig(db_path=tmp_path / "data.db", start_filter="work stuff")
    # Seed a saved filter and tasks before the app under test starts.
    seeder = NokkamApp(config=AppConfig(db_path=config.db_path))
    async with seeder.run_test() as pilot:
        work = seeder.project_repo.get_or_create("Work")
        seeder.task_service.add_task(Task(title="Work task", project_id=work))
        seeder.task_service.add_task(Task(title="Other task"))
        seeder.saved_filter_repo.save("Work stuff", "project:Work")
        await pilot.pause()

    app = NokkamApp(config=config)
    async with app.run_test() as pilot:
        await pilot.pause()
        titles = [i.model.title for i in app.screen.all_list.children if isinstance(i, TaskRow)]
        assert titles == ["Work task"]
        assert app.screen.query_one(AppHeader).meta == "Work stuff"


async def test_unknown_start_filter_warns_and_shows_everything(tmp_path: Path) -> None:
    app = make_app(tmp_path, start_filter="nonsense")
    async with app.run_test() as pilot:
        app.task_service.add_task(Task(title="Visible", due_date=date.today().isoformat()))
        app.screen.refresh_all()
        await pilot.pause()
        assert app.screen.smart_filter is None
        assert any("start_filter 'nonsense'" in n.message for n in app._notifications)
        assert app.screen.query_one(AppHeader).meta == date.today().strftime("%B %Y")


async def test_no_start_filter_means_no_filter(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        app.task_service.add_task(Task(title="Later", due_date=tomorrow))
        app.screen.refresh_all()
        await pilot.pause()
        assert app.screen.smart_filter is None
