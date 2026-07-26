from datetime import date, timedelta
from pathlib import Path

from cad_tui.app import CadTuiApp
from cad_tui.config import AppConfig
from cad_tui.domain.models import Task
from cad_tui.presentation.screens.task_list import TaskRow
from cad_tui.presentation.widgets.app_header import AppHeader


def make_app(tmp_path: Path) -> CadTuiApp:
    return CadTuiApp(config=AppConfig(db_path=tmp_path / "data.db"))


async def test_smart_list_today(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        today = date.today()
        app.task_service.add_task(Task(title="Today task", due_date=today.isoformat()))
        app.task_service.add_task(
            Task(title="Later task", due_date=(today + timedelta(days=5)).isoformat())
        )
        app.screen.set_smart_filter("today")
        await pilot.pause()

        titles = [i.model.title for i in app.screen.all_list.children]
        assert titles == ["Today task"]
        assert app.screen.query_one(AppHeader).meta == "Today"


async def test_smart_list_overdue(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        yesterday = date.today() - timedelta(days=1)
        tomorrow = date.today() + timedelta(days=1)
        app.task_service.add_task(Task(title="Late task", due_date=yesterday.isoformat()))
        app.task_service.add_task(Task(title="Future task", due_date=tomorrow.isoformat()))
        app.screen.set_smart_filter("overdue")
        await pilot.pause()

        titles = [i.model.title for i in app.screen.all_list.children]
        assert titles == ["Late task"]


async def test_smart_list_week(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        today = date.today()
        app.task_service.add_task(
            Task(title="In range", due_date=(today + timedelta(days=3)).isoformat())
        )
        app.task_service.add_task(
            Task(title="Out of range", due_date=(today + timedelta(days=10)).isoformat())
        )
        app.screen.set_smart_filter("week")
        await pilot.pause()

        titles = [i.model.title for i in app.screen.all_list.children]
        assert titles == ["In range"]


async def test_smart_list_excludes_done_tasks(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        today = date.today()
        t = app.task_service.add_task(Task(title="Done today", due_date=today.isoformat()))
        app.task_service.toggle_complete(t.id)
        app.screen.set_smart_filter("today")
        await pilot.pause()

        assert len(app.screen.all_list.children) == 0


async def test_clearing_smart_filter_restores_full_tree(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        app.task_service.add_task(Task(title="Task A"))
        app.screen.set_smart_filter("today")
        await pilot.pause()
        app.screen.set_smart_filter(None)
        await pilot.pause()

        titles = [i.model.title for i in app.screen.all_list.children if isinstance(i, TaskRow)]
        assert titles == ["Task A"]
        # no smart filter active -> header meta falls back to the calendar's month
        assert app.screen.query_one(AppHeader).meta == date.today().strftime("%B %Y")
