"""Time tracked per project and per day, for the time report chart."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from nokkam.data.repositories.project_repository import ProjectRepository
from nokkam.data.repositories.time_log_repository import TimeLogRepository
from nokkam.services.project_summary_service import NO_PROJECT_COLOR, NO_PROJECT_NAME
from nokkam.services.task_service import TaskService

DAILY_WINDOW = 30  # the by-day chart never shows more than this many days


@dataclass
class ProjectTime:
    name: str
    color: str
    minutes: int


@dataclass
class TimeReport:
    days: int | None  # None = all time
    projects: list[ProjectTime]  # most time first, only those with time
    daily: list[tuple[date, int]]  # oldest to newest, every day in the window
    total_minutes: int
    average_per_day: int


def compute_time_report(
    task_service: TaskService,
    project_repo: ProjectRepository,
    time_log_repo: TimeLogRepository,
    days: int | None,
    today: date | None = None,
) -> TimeReport:
    """`days` is the window ending today (7, 30, ...) or None for all time.
    The by-day chart covers the same window, capped at DAILY_WINDOW days."""
    today = today or date.today()
    since = (today - timedelta(days=days - 1)).isoformat() if days else None
    rows = time_log_repo.minutes_by_task_and_day(since)

    project_of_task = {t.id: t.project_id for t in task_service.list_tasks()}
    known = {p.id: p for p in project_repo.list()}
    by_project: dict[int | None, float] = {}
    by_day: dict[str, float] = {}
    for task_id, day, minutes in rows:
        project_id = project_of_task.get(task_id)
        key = project_id if project_id in known else None
        by_project[key] = by_project.get(key, 0.0) + minutes
        by_day[day] = by_day.get(day, 0.0) + minutes

    projects = [
        ProjectTime(
            name=known[key].name if key is not None else NO_PROJECT_NAME,
            color=known[key].color if key is not None else NO_PROJECT_COLOR,
            minutes=round(minutes),
        )
        for key, minutes in by_project.items()
    ]
    projects = sorted((p for p in projects if p.minutes > 0), key=lambda p: (-p.minutes, p.name))

    window = min(days, DAILY_WINDOW) if days else DAILY_WINDOW
    daily = [
        (day, round(by_day.get(day.isoformat(), 0.0)))
        for day in (today - timedelta(days=offset) for offset in range(window - 1, -1, -1))
    ]

    total = sum(p.minutes for p in projects)
    if days:
        span = days
    elif by_day:
        span = (today - date.fromisoformat(min(by_day))).days + 1
    else:
        span = 1
    return TimeReport(
        days=days,
        projects=projects,
        daily=daily,
        total_minutes=total,
        average_per_day=round(total / max(span, 1)),
    )
