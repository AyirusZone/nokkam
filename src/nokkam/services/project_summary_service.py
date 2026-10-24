"""Per-project progress and time-tracking rollup for the summary screen."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from nokkam.data.repositories.project_repository import ProjectRepository
from nokkam.data.repositories.time_log_repository import TimeLogRepository
from nokkam.domain.models import Status
from nokkam.services.task_service import TaskService

NO_PROJECT_NAME = "No project"
NO_PROJECT_COLOR = "#8E8E93"
RECENT_DAYS = 7


@dataclass
class ProjectSummary:
    name: str
    color: str
    total: int = 0
    done: int = 0
    overdue: int = 0
    minutes_total: int = 0
    minutes_recent: int = 0

    @property
    def open(self) -> int:
        return self.total - self.done

    @property
    def progress(self) -> float:
        return self.done / self.total if self.total else 0.0


def compute_project_summaries(
    task_service: TaskService,
    project_repo: ProjectRepository,
    time_log_repo: TimeLogRepository,
    today: date | None = None,
) -> list[ProjectSummary]:
    """One row per project (alphabetical, including empty ones) plus a
    trailing "No project" row when any task has none. Time counts the
    project's own tasks; "recent" is the last RECENT_DAYS days including today."""
    today = today or date.today()
    today_iso = today.isoformat()
    since = (today - timedelta(days=RECENT_DAYS - 1)).isoformat()
    minutes_all = time_log_repo.minutes_by_task()
    minutes_recent = time_log_repo.minutes_by_task(since)

    summaries: dict[int | None, ProjectSummary] = {
        p.id: ProjectSummary(name=p.name, color=p.color) for p in project_repo.list()
    }
    no_project = ProjectSummary(name=NO_PROJECT_NAME, color=NO_PROJECT_COLOR)
    summaries[None] = no_project
    exact_minutes: dict[int | None, list[float]] = {key: [0.0, 0.0] for key in summaries}

    for task in task_service.list_tasks():
        key = task.project_id if task.project_id in summaries else None
        summary = summaries[key]
        summary.total += 1
        if task.status == Status.DONE:
            summary.done += 1
        elif task.due_date and task.due_date < today_iso:
            summary.overdue += 1
        if task.id is not None:
            exact_minutes[key][0] += minutes_all.get(task.id, 0.0)
            exact_minutes[key][1] += minutes_recent.get(task.id, 0.0)

    for key, (total, recent) in exact_minutes.items():
        summaries[key].minutes_total = round(total)
        summaries[key].minutes_recent = round(recent)

    ordered = [s for k, s in summaries.items() if k is not None]
    if no_project.total:
        ordered.append(no_project)
    return ordered


def compact_minutes(minutes: int) -> str:
    """At most 4 characters, for chart labels: 45m, 1.5h, 2h, 12h ('' for none)."""
    if minutes <= 0:
        return ""
    if minutes < 60:
        return f"{minutes}m"
    if minutes < 600:
        hours = f"{minutes / 60:.1f}".removesuffix(".0")
        return f"{hours}h"
    return f"{round(minutes / 60)}h"


def format_minutes(minutes: int) -> str:
    if minutes <= 0:
        return "—"
    hours, mins = divmod(minutes, 60)
    if not hours:
        return f"{mins}m"
    return f"{hours}h {mins:02d}m" if mins else f"{hours}h"
