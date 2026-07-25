from pathlib import Path

from textual.widgets import Input

from cad_tui.app import CadTuiApp
from cad_tui.config import AppConfig
from cad_tui.domain.models import Task
from cad_tui.presentation.screens.task_list import TaskListScreen


def make_app(tmp_path: Path) -> CadTuiApp:
    return CadTuiApp(config=AppConfig(db_path=tmp_path / "data.db"))


async def test_app_launches_and_runs_migrations(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test():
        assert isinstance(app.screen, TaskListScreen)
        assert app.db is not None
        tables = {
            row["name"]
            for row in app.db.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        assert "task" in tables


async def test_theme_toggle(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        start_theme = app.theme
        await pilot.press("ctrl+t")
        assert app.theme != start_theme
        await pilot.press("ctrl+t")
        assert app.theme == start_theme


async def test_add_task_end_to_end_through_ui(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        await pilot.press("a")
        await pilot.pause()

        title_input = app.screen.query_one("#title", Input)
        title_input.value = "Write report"
        await pilot.click("#save")
        await pilot.pause()

        assert isinstance(app.screen, TaskListScreen)
        tasks = app.task_service.list_tasks()
        assert len(tasks) == 1
        assert tasks[0].title == "Write report"


async def test_delete_then_undo_through_ui(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        app.task_service.add_task(Task(title="Ephemeral"))
        app.screen.refresh_tasks()
        await pilot.pause()

        await pilot.press("d")
        await pilot.pause()
        assert app.task_service.list_tasks() == []

        await pilot.press("u")
        await pilot.pause()
        tasks = app.task_service.list_tasks()
        assert len(tasks) == 1
        assert tasks[0].title == "Ephemeral"
