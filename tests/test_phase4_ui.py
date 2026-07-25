from datetime import date, timedelta
from pathlib import Path

from textual.widgets import Input

from cad_tui.app import CadTuiApp
from cad_tui.config import AppConfig
from cad_tui.presentation.screens.task_list import TaskListScreen


def make_app(tmp_path: Path) -> CadTuiApp:
    return CadTuiApp(config=AppConfig(db_path=tmp_path / "data.db"))


async def test_quick_add_parses_trailing_date(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        await pilot.press("A")
        await pilot.pause()
        app.screen.query_one("#quick-input", Input).value = "Buy milk tomorrow"
        await pilot.press("enter")
        await pilot.pause()

        assert isinstance(app.screen, TaskListScreen)
        tasks = app.task_service.list_tasks()
        assert len(tasks) == 1
        assert tasks[0].title == "Buy milk"
        assert tasks[0].due_date == (date.today() + timedelta(days=1)).isoformat()


async def test_add_subtask_via_ui_appears_indented(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        from cad_tui.domain.models import Task

        parent = app.task_service.add_task(Task(title="Plan trip"))
        app.screen.refresh_tasks()
        await pilot.pause()

        await pilot.press("s")
        await pilot.pause()
        app.screen.query_one("#title", Input).value = "Book flight"
        await pilot.click("#save")
        await pilot.pause()

        tree = app.task_service.list_tasks_tree()
        depths = {t.title: d for t, d in tree}
        assert depths["Plan trip"] == 0
        assert depths["Book flight"] == 1

        child = next(t for t, _ in tree if t.title == "Book flight")
        assert child.parent_task_id == parent.id


async def test_recurring_task_completion_spawns_next_visible_in_list(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        await pilot.press("a")
        await pilot.pause()
        app.screen.query_one("#title", Input).value = "Standup"
        app.screen.query_one("#due_date", Input).value = date.today().isoformat()
        from textual.widgets import Select

        app.screen.query_one("#recurrence", Select).value = "daily"
        await pilot.click("#save")
        await pilot.pause()

        assert len(app.task_service.list_tasks()) == 1

        await pilot.press("space")
        await pilot.pause()

        tasks = app.task_service.list_tasks()
        assert len(tasks) == 2
        assert any(t.recurrence_id is not None and t.status == "open" for t in tasks)
