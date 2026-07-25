from pathlib import Path

from cad_tui.cli import run_cli
from cad_tui.config import AppConfig
from cad_tui.data.db import connect
from cad_tui.data.migrations import apply_migrations
from cad_tui.data.repositories.project_repository import ProjectRepository
from cad_tui.data.repositories.tag_repository import TagRepository
from cad_tui.data.repositories.task_repository import TaskRepository


def make_config(tmp_path: Path) -> AppConfig:
    return AppConfig(db_path=tmp_path / "data.db")


def _read_tasks(config: AppConfig):
    conn = connect(config.db_path)
    apply_migrations(conn)
    return TaskRepository(conn).list()


def test_add_creates_task_with_parsed_date(tmp_path: Path, capsys) -> None:
    config = make_config(tmp_path)
    exit_code = run_cli(["add", "Buy milk tmrw 3pm"], config)
    assert exit_code == 0

    tasks = _read_tasks(config)
    assert len(tasks) == 1
    assert tasks[0].title == "Buy milk"
    assert tasks[0].due_time == "15:00"
    assert "Added task #1" in capsys.readouterr().out


def test_add_explicit_due_overrides_parsed_date(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    run_cli(["add", "Renew license", "--due", "2026-12-01"], config)

    tasks = _read_tasks(config)
    assert tasks[0].due_date == "2026-12-01"


def test_add_with_priority_project_tags(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    run_cli(
        ["add", "Ship release", "--priority", "high", "--project", "Work", "--tags", "urgent,release"],
        config,
    )

    conn = connect(config.db_path)
    apply_migrations(conn)
    task = TaskRepository(conn).list()[0]
    assert task.priority == 1  # Priority.HIGH
    project = ProjectRepository(conn).get(task.project_id)
    assert project.name == "Work"
    tag_names = {t.name for t in TagRepository(conn).get_many(task.tag_ids)}
    assert tag_names == {"urgent", "release"}


async def test_cli_added_task_visible_in_tui(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    run_cli(["add", "From CLI"], config)

    from cad_tui.app import CadTuiApp

    app = CadTuiApp(config=config)
    async with app.run_test():
        titles = [t.title for t in app.task_service.list_tasks()]
        assert "From CLI" in titles


def test_no_command_prints_help_and_returns_nonzero(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    exit_code = run_cli([], config)
    assert exit_code == 1
