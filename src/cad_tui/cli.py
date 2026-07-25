"""Non-interactive entrypoints: quick-capture and export/import, bypassing
the Textual UI entirely. Invoked from app.main() when argv has a subcommand."""

from __future__ import annotations

import argparse

from cad_tui.config import AppConfig, load_config
from cad_tui.data.db import connect
from cad_tui.data.migrations import apply_migrations
from cad_tui.data.repositories.project_repository import ProjectRepository
from cad_tui.data.repositories.tag_repository import TagRepository
from cad_tui.data.repositories.task_repository import TaskRepository
from cad_tui.domain.models import Priority, Task
from cad_tui.domain.nl_date_parser import parse_quick_text
from cad_tui.infra.export_adapter import export_csv, export_ics, export_json, import_csv, import_json

_PRIORITY_MAP = {"high": Priority.HIGH, "medium": Priority.MEDIUM, "low": Priority.LOW}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cad-tui")
    sub = parser.add_subparsers(dest="command")

    add_p = sub.add_parser("add", help="Quick-capture a task without opening the UI")
    add_p.add_argument(
        "text", help='Task title, optionally with a trailing date/time, e.g. "Buy milk tmrw 3pm"'
    )
    add_p.add_argument("--due", help="Explicit due date (YYYY-MM-DD), overrides text parsing")
    add_p.add_argument("--priority", choices=["high", "medium", "low"], default=None)
    add_p.add_argument("--project", default=None)
    add_p.add_argument("--tags", default=None, help="Comma-separated tags")

    export_p = sub.add_parser("export", help="Export tasks to a file")
    export_p.add_argument("--format", choices=["json", "csv", "ics"], required=True)
    export_p.add_argument("--out", required=True)

    import_p = sub.add_parser("import", help="Import tasks from a file")
    import_p.add_argument("--format", choices=["json", "csv"], required=True)
    import_p.add_argument("--in", dest="infile", required=True)

    return parser


def run_cli(argv: list[str], config: AppConfig | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 1

    config = config or load_config()
    conn = connect(config.db_path)
    apply_migrations(conn)
    task_repo = TaskRepository(conn)
    project_repo = ProjectRepository(conn)
    tag_repo = TagRepository(conn)
    try:
        if args.command == "add":
            return _cmd_add(args, task_repo, project_repo, tag_repo)
        if args.command == "export":
            return _cmd_export(args, task_repo, tag_repo)
        if args.command == "import":
            return _cmd_import(args, task_repo, tag_repo)
        parser.print_help()
        return 1
    finally:
        conn.close()


def _cmd_add(args, task_repo: TaskRepository, project_repo: ProjectRepository, tag_repo: TagRepository) -> int:
    parsed = parse_quick_text(args.text)
    due_date = args.due or parsed.due_date
    task = Task(
        title=parsed.title,
        due_date=due_date,
        due_time=parsed.due_time,
        priority=_PRIORITY_MAP.get(args.priority, Priority.MEDIUM),
        project_id=project_repo.get_or_create(args.project) if args.project else None,
        tag_ids=tag_repo.get_or_create_many(args.tags.split(",")) if args.tags else [],
    )
    task_id = task_repo.create(task)
    suffix = f" (due {due_date})" if due_date else ""
    print(f"Added task #{task_id}: {parsed.title}{suffix}")
    return 0


def _cmd_export(args, task_repo: TaskRepository, tag_repo: TagRepository) -> int:
    tasks = task_repo.list()
    if args.format == "json":
        export_json(tasks, args.out, tag_repo)
    elif args.format == "csv":
        export_csv(tasks, args.out, tag_repo)
    else:
        export_ics(tasks, args.out)
    print(f"Exported {len(tasks)} task(s) to {args.out}")
    return 0


def _cmd_import(args, task_repo: TaskRepository, tag_repo: TagRepository) -> int:
    if args.format == "json":
        count = import_json(args.infile, task_repo, tag_repo)
    else:
        count = import_csv(args.infile, task_repo, tag_repo)
    print(f"Imported {count} task(s) from {args.infile}")
    return 0
