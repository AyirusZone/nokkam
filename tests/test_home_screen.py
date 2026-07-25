from datetime import date, timedelta
from pathlib import Path

from textual.widgets import Input

from cad_tui.app import CadTuiApp
from cad_tui.config import AppConfig
from cad_tui.domain.models import Task
from cad_tui.presentation.widgets.calendar_grid import DayCell


def make_app(tmp_path: Path) -> CadTuiApp:
    return CadTuiApp(config=AppConfig(db_path=tmp_path / "data.db"))


async def test_task_due_today_shows_on_correct_day_cell(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        today = date.today()
        app.task_service.add_task(Task(title="Due today", due_date=today.isoformat()))
        app.screen.refresh_all()
        await pilot.pause()

        day_cells = list(app.screen.query(DayCell))
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
        app.screen.refresh_all()
        await pilot.pause()

        titles = [item.model.title for item in app.screen.day_list.children]
        assert titles == ["Today's task"]


async def test_calendar_nav_only_moves_when_calendar_focused(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        today = date.today()
        screen = app.screen
        await pilot.pause()

        # all_list has focus by default (on_mount) — nav_right should not move the calendar
        screen.action_nav_right()
        await pilot.pause()
        assert screen.calendar.focus_date == today

        screen.calendar.focus()
        await pilot.pause()
        screen.action_nav_right()
        await pilot.pause()
        assert screen.calendar.focus_date == today + timedelta(days=1)


async def test_jump_today_via_t_when_calendar_focused(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        today = date.today()
        screen = app.screen
        screen.calendar.focus()
        await pilot.pause()
        screen.action_next_month()
        await pilot.pause()
        assert screen.calendar.focus_date != today

        await pilot.press("t")
        await pilot.pause()
        assert screen.calendar.focus_date == today


async def test_t_toggles_timer_when_list_focused(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        task = app.task_service.add_task(Task(title="Focus work"))
        app.screen.refresh_all()
        await pilot.pause()
        app.screen.all_list.focus()
        await pilot.pause()

        await pilot.press("t")
        await pilot.pause()
        assert app.time_tracking.active_task_id == task.id


async def test_add_task_from_calendar_context_prefills_selected_day(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        screen = app.screen
        screen.calendar.focus()
        await pilot.pause()
        screen.action_nav_right()
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


async def test_add_task_from_all_list_context_leaves_due_date_blank(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        app.screen.all_list.focus()
        await pilot.pause()
        await pilot.press("a")
        await pilot.pause()
        due_input = app.screen.query_one("#due_date", Input)
        assert due_input.value == ""


async def test_delete_from_day_pane_removes_only_that_task(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        today = date.today()
        day_task = app.task_service.add_task(Task(title="Day task", due_date=today.isoformat()))
        other_task = app.task_service.add_task(Task(title="Other task"))
        app.screen.refresh_all()
        await pilot.pause()

        app.screen.day_list.focus()
        await pilot.pause()
        await pilot.press("d")
        await pilot.pause()

        remaining = {t.id for t in app.task_service.list_tasks()}
        assert day_task.id not in remaining
        assert other_task.id in remaining


async def test_tab_cycles_focus_across_three_panes(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        screen = app.screen
        await pilot.pause()
        seen = set()
        for _ in range(6):
            seen.add(type(screen.focused).__name__ if screen.focused is not None else None)
            await pilot.press("tab")
            await pilot.pause()
        assert "CalendarGrid" in seen
        assert "ListView" in seen
