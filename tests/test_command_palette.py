from pathlib import Path

from cad_tui.app import CadTuiApp
from cad_tui.config import AppConfig
from cad_tui.domain.models import Task
from cad_tui.presentation.command_provider import TaskSearchProvider
from cad_tui.presentation.screens.agenda_screen import AgendaScreen
from cad_tui.presentation.screens.home_screen import HomeScreen
from cad_tui.presentation.widgets.calendar_grid import CalendarGrid


def make_app(tmp_path: Path) -> CadTuiApp:
    return CadTuiApp(config=AppConfig(db_path=tmp_path / "data.db"))


async def test_jump_to_task_from_nested_screen_returns_to_home(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        task = app.task_service.add_task(Task(title="Find me"))
        app.task_service.add_task(Task(title="Other"))
        app.screen.refresh_all()
        await pilot.pause()

        await app.push_screen(AgendaScreen())
        await pilot.pause()
        assert isinstance(app.screen, AgendaScreen)

        app.jump_to_task(task.id)
        await pilot.pause()

        assert isinstance(app.screen, HomeScreen)
        assert app.screen.selected_task.id == task.id


async def test_task_search_provider_matches_by_title(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        target = app.task_service.add_task(Task(title="Write quarterly report"))
        app.task_service.add_task(Task(title="Buy milk"))
        await pilot.pause()

        provider = TaskSearchProvider(app.screen)
        hits = [hit async for hit in provider.search("quarterly")]

        assert len(hits) == 1
        assert hits[0].command.func == app.jump_to_task
        assert hits[0].command.args == (target.id,)


async def test_system_commands_include_core_actions(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test():
        names = {cmd.title for cmd in app.get_system_commands(app.screen)}
        expected = {
            "Add task",
            "Quick add",
            "Undo",
            "Focus calendar",
            "Open agenda",
            "Show stats",
            "Smart list: Today",
            "Smart list: Overdue",
            "Smart list: This week",
            "Smart list: All tasks",
        }
        assert expected <= names


async def test_focus_calendar_system_command_moves_focus(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        commands = {cmd.title: cmd for cmd in app.get_system_commands(app.screen)}
        commands["Focus calendar"].callback()
        await pilot.pause()

        assert isinstance(app.screen.focused, CalendarGrid)


async def test_smart_list_system_command_applies_filter(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        commands = {cmd.title: cmd for cmd in app.get_system_commands(app.screen)}
        commands["Smart list: Overdue"].callback()
        await pilot.pause()

        assert app.screen.smart_filter == "overdue"
