from pathlib import Path

from cad_tui.data.db import connect
from cad_tui.data.migrations import apply_migrations
from cad_tui.data.repositories.dependency_repository import DependencyRepository
from cad_tui.data.repositories.task_repository import TaskRepository
from cad_tui.domain.models import Task
from cad_tui.services.task_service import TaskService
from cad_tui.services.undo import UndoStack


def make_service(db_path: Path) -> TaskService:
    conn = connect(db_path)
    apply_migrations(conn)
    return TaskService(
        TaskRepository(conn), UndoStack(), dependency_repo=DependencyRepository(conn)
    )


def test_task_with_open_blocker_is_blocked(tmp_path: Path) -> None:
    service = make_service(tmp_path / "data.db")
    blocker = service.add_task(Task(title="Design"))
    blocked = service.add_task(Task(title="Build"))

    service.set_blocked_by(blocked.id, blocker.id)
    assert service.is_blocked(blocked.id) is True


def test_task_unblocked_once_blocker_completes(tmp_path: Path) -> None:
    service = make_service(tmp_path / "data.db")
    blocker = service.add_task(Task(title="Design"))
    blocked = service.add_task(Task(title="Build"))
    service.set_blocked_by(blocked.id, blocker.id)

    service.toggle_complete(blocker.id)
    assert service.is_blocked(blocked.id) is False


def test_task_without_dependency_is_not_blocked(tmp_path: Path) -> None:
    service = make_service(tmp_path / "data.db")
    task = service.add_task(Task(title="Standalone"))
    assert service.is_blocked(task.id) is False


def test_clearing_blocked_by_removes_block(tmp_path: Path) -> None:
    service = make_service(tmp_path / "data.db")
    blocker = service.add_task(Task(title="Design"))
    blocked = service.add_task(Task(title="Build"))
    service.set_blocked_by(blocked.id, blocker.id)
    assert service.is_blocked(blocked.id) is True

    service.set_blocked_by(blocked.id, None)
    assert service.is_blocked(blocked.id) is False


def test_service_without_dependency_repo_never_blocks(tmp_path: Path) -> None:
    conn = connect(tmp_path / "data.db")
    apply_migrations(conn)
    service = TaskService(TaskRepository(conn), UndoStack())  # no dependency_repo
    task = service.add_task(Task(title="Standalone"))
    assert service.is_blocked(task.id) is False
    service.set_blocked_by(task.id, 999)  # should be a no-op, not raise


async def test_toggle_complete_on_blocked_task_is_refused_via_ui(tmp_path: Path) -> None:
    from cad_tui.app import CadTuiApp
    from cad_tui.config import AppConfig

    app = CadTuiApp(config=AppConfig(db_path=tmp_path / "ui.db"))
    async with app.run_test() as pilot:
        blocker = app.task_service.add_task(Task(title="Design"))
        blocked = app.task_service.add_task(Task(title="Build"))
        app.task_service.set_blocked_by(blocked.id, blocker.id)
        app.screen.refresh_all()
        await pilot.pause()

        app.screen.select_task_by_id(blocked.id)
        await pilot.press("space")
        await pilot.pause()

        refreshed = next(t for t in app.task_service.list_tasks() if t.id == blocked.id)
        assert refreshed.status == "open"


async def test_form_saves_blocked_by_and_paired_fields(tmp_path: Path) -> None:
    from textual.widgets import Input

    from cad_tui.app import CadTuiApp
    from cad_tui.config import AppConfig

    app = CadTuiApp(config=AppConfig(db_path=tmp_path / "ui2.db"))
    async with app.run_test() as pilot:
        app.task_service.add_task(Task(title="Design"))
        app.screen.refresh_all()
        await pilot.pause()

        await pilot.press("a")
        await pilot.pause()
        app.screen.query_one("#title", Input).value = "Build"
        app.screen.query_one("#due_date", Input).value = "2026-08-01"
        app.screen.query_one("#due_time", Input).value = "09:00"
        app.screen.query_one("#blocked_by", Input).value = "Design"
        await pilot.click("#save")
        await pilot.pause()

        built = next(t for t in app.task_service.list_tasks() if t.title == "Build")
        assert built.due_date == "2026-08-01"
        assert built.due_time == "09:00"
        assert app.task_service.is_blocked(built.id) is True
