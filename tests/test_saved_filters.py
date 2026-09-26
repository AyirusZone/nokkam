from datetime import date, timedelta
from pathlib import Path

from textual.widgets import Input

from nokkam.app import NokkamApp
from nokkam.config import AppConfig
from nokkam.data.db import connect
from nokkam.data.migrations import apply_migrations
from nokkam.data.repositories.saved_filter_repository import SavedFilterRepository
from nokkam.domain.models import Priority, Task
from nokkam.presentation.screens.task_list import TaskRow
from nokkam.presentation.widgets.app_header import AppHeader


def make_app(tmp_path: Path) -> NokkamApp:
    return NokkamApp(config=AppConfig(db_path=tmp_path / "data.db"))


def visible_titles(app: NokkamApp) -> list[str]:
    return [i.model.title for i in app.screen.all_list.children if isinstance(i, TaskRow)]


def test_repository_save_list_replace_delete(tmp_path: Path) -> None:
    conn = connect(tmp_path / "data.db")
    apply_migrations(conn)
    repo = SavedFilterRepository(conn)

    repo.save("Work week", "project:Work due:week")
    repo.save("Errands", "tag:errand")
    assert [(f.name, f.query) for f in repo.list()] == [
        ("Errands", "tag:errand"),
        ("Work week", "project:Work due:week"),
    ]

    repo.save("work WEEK", "project:Work due:today")  # same name, different case
    assert [(f.name, f.query) for f in repo.list()][1] == ("Work week", "project:Work due:today")
    assert len(repo.list()) == 2

    repo.delete("Errands")
    assert [f.name for f in repo.list()] == ["Work week"]
    conn.close()


async def test_apply_filter_narrows_task_list_and_sets_header(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        work = app.project_repo.get_or_create("Work")
        urgent = app.tag_repo.get_or_create("urgent")
        soon = (date.today() + timedelta(days=2)).isoformat()
        app.task_service.add_task(
            Task(title="Match", project_id=work, tag_ids=[urgent], due_date=soon)
        )
        app.task_service.add_task(Task(title="Wrong project", tag_ids=[urgent], due_date=soon))
        app.task_service.add_task(Task(title="No due date", project_id=work, tag_ids=[urgent]))
        app.screen.refresh_all()
        await pilot.pause()

        assert app._apply_filter("project:Work tag:urgent due:week", "Work urgent") is True
        await pilot.pause()

        assert visible_titles(app) == ["Match"]
        assert app.screen.query_one(AppHeader).meta == "Work urgent"

        app._cmd_smart_list(None)
        await pilot.pause()
        assert sorted(visible_titles(app)) == ["Match", "No due date", "Wrong project"]


async def test_bad_query_keeps_current_view_and_reports_error(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        app.task_service.add_task(Task(title="Only task", priority=Priority.LOW))
        app.screen.refresh_all()
        await pilot.pause()

        assert app._apply_filter("colour:red", "bad") is False
        await pilot.pause()

        assert app.screen.smart_filter is None
        assert visible_titles(app) == ["Only task"]
        assert any("Unknown filter" in n.message for n in app._notifications)


async def test_save_filter_flow_persists_and_appears_in_palette(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        app.task_service.add_task(Task(title="High one", priority=Priority.HIGH))
        app.task_service.add_task(Task(title="Low one", priority=Priority.LOW))
        app.screen.refresh_all()
        await pilot.pause()

        app._cmd_save_filter()
        await pilot.pause()
        app.screen.query_one("#text-prompt-input", Input).value = "Important"
        await pilot.press("enter")
        await pilot.pause()
        app.screen.query_one("#text-prompt-input", Input).value = "priority:high"
        await pilot.press("enter")
        await pilot.pause()

        assert visible_titles(app) == ["High one"]
        assert [(f.name, f.query) for f in app.saved_filter_repo.list()] == [
            ("Important", "priority:high")
        ]

        titles = [c.title for c in app.get_system_commands(app.screen)]
        assert "Filter: Important" in titles
        assert "Delete filter: Important" in titles

        app._cmd_smart_list(None)
        await pilot.pause()
        assert sorted(visible_titles(app)) == ["High one", "Low one"]

        app._apply_filter("priority:high", "Important")
        app._delete_filter("Important")
        assert app.saved_filter_repo.list() == []


async def test_invalid_query_in_save_flow_is_not_saved(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        app._cmd_save_filter()
        await pilot.pause()
        app.screen.query_one("#text-prompt-input", Input).value = "Broken"
        await pilot.press("enter")
        await pilot.pause()
        app.screen.query_one("#text-prompt-input", Input).value = "due:someday"
        await pilot.press("enter")
        await pilot.pause()

        assert app.saved_filter_repo.list() == []
