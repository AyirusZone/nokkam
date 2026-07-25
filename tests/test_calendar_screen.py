from datetime import date, timedelta
from pathlib import Path

from cad_tui.app import CadTuiApp
from cad_tui.config import AppConfig
from cad_tui.domain.models import Task
from cad_tui.presentation.screens.calendar_screen import CalendarScreen
from cad_tui.presentation.screens.task_list import TaskListScreen
from cad_tui.presentation.widgets.calendar_grid import DayCell


def make_app(tmp_path: Path) -> CadTuiApp:
    return CadTuiApp(config=AppConfig(db_path=tmp_path / "data.db"))


async def test_task_due_today_shows_on_correct_day_cell(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        today = date.today()
        app.task_service.add_task(Task(title="Due today", due_date=today.isoformat()))

        await app.push_screen(CalendarScreen())
        await pilot.pause()

        screen = app.screen
        assert isinstance(screen, CalendarScreen)

        day_cells = list(screen.query(DayCell))
        matching = [c for c in day_cells if c.day == today]
        assert len(matching) == 1
        assert matching[0].count == 1
        assert "today" in matching[0].classes

        other_cells_same_month = [
            c for c in day_cells if c.day != today and c.day.month == today.month
        ]
        assert all(c.count == 0 for c in other_cells_same_month)


async def test_day_pane_lists_only_tasks_for_selected_day(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        today = date.today()
        tomorrow = today + timedelta(days=1)
        app.task_service.add_task(Task(title="Today's task", due_date=today.isoformat()))
        app.task_service.add_task(Task(title="Tomorrow's task", due_date=tomorrow.isoformat()))

        await app.push_screen(CalendarScreen())
        await pilot.pause()
        screen = app.screen

        titles = [item.model.title for item in screen.day_list.children]
        assert titles == ["Today's task"]


async def test_next_day_updates_day_pane_and_selection(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        today = date.today()
        tomorrow = today + timedelta(days=1)
        app.task_service.add_task(Task(title="Tomorrow's task", due_date=tomorrow.isoformat()))

        await app.push_screen(CalendarScreen())
        await pilot.pause()
        screen = app.screen
        screen.action_next_day()
        await pilot.pause()

        assert screen.calendar.focus_date == tomorrow
        titles = [item.model.title for item in screen.day_list.children]
        assert titles == ["Tomorrow's task"]


async def test_jump_today_returns_to_current_date(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        today = date.today()
        await app.push_screen(CalendarScreen())
        await pilot.pause()
        screen = app.screen

        screen.action_next_month()
        await pilot.pause()
        assert screen.calendar.focus_date != today

        screen.action_jump_today()
        await pilot.pause()
        assert screen.calendar.focus_date == today


async def test_open_calendar_from_task_list_and_back(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        await pilot.press("c")
        await pilot.pause()
        assert isinstance(app.screen, CalendarScreen)

        await pilot.press("escape")
        await pilot.pause()
        assert isinstance(app.screen, TaskListScreen)


async def test_add_task_from_calendar_prefills_selected_day(tmp_path: Path) -> None:
    from textual.widgets import Input

    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        today = date.today()
        await app.push_screen(CalendarScreen())
        await pilot.pause()
        screen = app.screen
        screen.action_next_day()
        await pilot.pause()
        expected_due = screen.calendar.focus_date

        await pilot.press("a")
        await pilot.pause()
        due_input = app.screen.query_one("#due_date", Input)
        assert due_input.value == expected_due.isoformat()

        title_input = app.screen.query_one("#title", Input)
        title_input.value = "Prefilled task"
        await pilot.click("#save")
        await pilot.pause()

        tasks = app.task_service.list_tasks()
        assert len(tasks) == 1
        assert tasks[0].due_date == expected_due.isoformat()
