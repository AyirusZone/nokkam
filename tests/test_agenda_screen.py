from datetime import date, timedelta
from pathlib import Path

from nokkam.app import NokkamApp
from nokkam.config import AppConfig
from nokkam.domain.models import Task
from nokkam.presentation.screens.agenda_screen import AgendaScreen


def make_app(tmp_path: Path) -> NokkamApp:
    return NokkamApp(config=AppConfig(db_path=tmp_path / "data.db"))


async def test_agenda_lists_only_next_14_days_sorted(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        today = date.today()
        app.task_service.add_task(
            Task(title="Far future", due_date=(today + timedelta(days=20)).isoformat())
        )
        app.task_service.add_task(
            Task(title="Day 5", due_date=(today + timedelta(days=5)).isoformat())
        )
        app.task_service.add_task(Task(title="Today", due_date=today.isoformat()))
        app.task_service.add_task(Task(title="No date"))

        await app.push_screen(AgendaScreen())
        await pilot.pause()
        screen = app.screen
        assert isinstance(screen, AgendaScreen)

        titles = [i.model.title for i in screen.list_view.children]
        assert titles == ["Today", "Day 5"]


async def test_agenda_toggle_complete_then_undo(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        today = date.today()
        app.task_service.add_task(Task(title="Do it", due_date=today.isoformat()))
        await app.push_screen(AgendaScreen())
        await pilot.pause()
        screen = app.screen

        screen.action_toggle_complete()
        await pilot.pause()
        assert app.task_service.list_tasks()[0].status == "done"
        assert len(screen.list_view.children) == 0

        screen.action_undo()
        await pilot.pause()
        assert len(screen.list_view.children) == 1


async def test_agenda_back_returns_to_home(tmp_path: Path) -> None:
    from nokkam.presentation.screens.home_screen import HomeScreen

    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        await app.push_screen(AgendaScreen())
        await pilot.pause()
        app.screen.action_back()
        await pilot.pause()
        assert isinstance(app.screen, HomeScreen)
