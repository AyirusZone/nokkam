"""Export/import adapters: JSON and CSV round-trip tags by name (not id,
since ids are meaningless across databases); ICS export only (VTODO)."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from nokkam.data.repositories.tag_repository import TagRepository
from nokkam.data.repositories.task_repository import TaskRepository
from nokkam.domain.models import Task

TAG_SEPARATOR = ";"


def _tag_names(task: Task, tag_repo: TagRepository | None) -> list[str]:
    if not tag_repo or not task.tag_ids:
        return []
    return [t.name for t in tag_repo.get_many(task.tag_ids)]


def export_json(tasks: list[Task], out_path: str, tag_repo: TagRepository | None = None) -> None:
    data = [
        {
            "title": t.title,
            "notes": t.notes,
            "priority": t.priority,
            "status": t.status,
            "due_date": t.due_date,
            "due_time": t.due_time,
            "tags": _tag_names(t, tag_repo),
        }
        for t in tasks
    ]
    Path(out_path).write_text(json.dumps(data, indent=2))


def import_json(
    in_path: str, task_repo: TaskRepository, tag_repo: TagRepository | None = None
) -> int:
    data = json.loads(Path(in_path).read_text())
    count = 0
    for item in data:
        tag_ids = tag_repo.get_or_create_many(item.get("tags", [])) if tag_repo else []
        task_repo.create(
            Task(
                title=item["title"],
                notes=item.get("notes"),
                priority=item.get("priority", 2),
                status=item.get("status", "open"),
                due_date=item.get("due_date"),
                due_time=item.get("due_time"),
                tag_ids=tag_ids,
            )
        )
        count += 1
    return count


CSV_FIELDS = ["title", "notes", "priority", "status", "due_date", "due_time", "tags"]


def export_csv(tasks: list[Task], out_path: str, tag_repo: TagRepository | None = None) -> None:
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for t in tasks:
            writer.writerow(
                {
                    "title": t.title,
                    "notes": t.notes or "",
                    "priority": t.priority,
                    "status": t.status,
                    "due_date": t.due_date or "",
                    "due_time": t.due_time or "",
                    "tags": TAG_SEPARATOR.join(_tag_names(t, tag_repo)),
                }
            )


def import_csv(
    in_path: str, task_repo: TaskRepository, tag_repo: TagRepository | None = None
) -> int:
    count = 0
    with open(in_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            tag_names = [n for n in (row.get("tags") or "").split(TAG_SEPARATOR) if n.strip()]
            tag_ids = tag_repo.get_or_create_many(tag_names) if tag_repo and tag_names else []
            task_repo.create(
                Task(
                    title=row["title"],
                    notes=row.get("notes") or None,
                    priority=int(row.get("priority") or 2),
                    status=row.get("status") or "open",
                    due_date=row.get("due_date") or None,
                    due_time=row.get("due_time") or None,
                    tag_ids=tag_ids,
                )
            )
            count += 1
    return count


def export_ics(tasks: list[Task], out_path: str) -> None:
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//nokkam//EN"]
    for t in tasks:
        lines.append("BEGIN:VTODO")
        lines.append(f"SUMMARY:{_ics_escape(t.title)}")
        if t.notes:
            lines.append(f"DESCRIPTION:{_ics_escape(t.notes)}")
        if t.due_date:
            due = t.due_date.replace("-", "")
            if t.due_time:
                due += "T" + t.due_time.replace(":", "") + "00"
            lines.append(f"DUE:{due}")
        lines.append(f"STATUS:{'COMPLETED' if t.status == 'done' else 'NEEDS-ACTION'}")
        lines.append("END:VTODO")
    lines.append("END:VCALENDAR")
    Path(out_path).write_text("\r\n".join(lines) + "\r\n")


def _ics_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace(",", "\\,").replace(";", "\\;").replace("\n", "\\n")
