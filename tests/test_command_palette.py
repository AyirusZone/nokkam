from pathlib import Path

from nokkam.app import NokkamApp
from nokkam.config import AppConfig
from nokkam.domain.models import Task
from nokkam.presentation.command_provider import TaskSearchProvider
from nokkam.presentation.screens.agenda_screen import AgendaScreen
from nokkam.presentation.screens.home_screen import HomeScreen
from nokkam.presentation.widgets.calendar_grid import CalendarGrid


def make_app(tmp_path: Path) -> NokkamApp:
    return NokkamApp(config=AppConfig(db_path=tmp_path / "data.db"))


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


async def test_task_search_provider_masks_private_task_title(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        app.task_service.add_task(Task(title="Surprise party planning", private=True))
        await pilot.pause()

        provider = TaskSearchProvider(app.screen)
        hits = [hit async for hit in provider.search("surprise")]

        assert len(hits) == 1
        assert hits[0].match_display == "•••••"


async def test_discover_lists_recent_tasks_masking_private_ones(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        app.task_service.add_task(Task(title="Public task"))
        app.task_service.add_task(Task(title="Secret task", private=True))
        await pilot.pause()

        provider = TaskSearchProvider(app.screen)
        hits = [hit async for hit in provider.discover()]

        assert len(hits) == 2
        by_display = {hit.display: hit for hit in hits}
        assert "Public task" in by_display
        assert "•••••" in by_display
        assert "Secret task" not in by_display
