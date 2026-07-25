"""Pure computation over tasks already loaded via TaskService — no SQL here."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from cad_tui.domain.models import Status
from cad_tui.services.task_service import TaskService


@dataclass
class Stats:
    total: int
    open: int
    done: int
    overdue: int
    completion_rate: float
    streak_days: int


def compute_stats(task_service: TaskService) -> Stats:
    all_tasks = task_service.list_tasks()
    open_tasks = [t for t in all_tasks if t.status == Status.OPEN]
    done_tasks = [t for t in all_tasks if t.status == Status.DONE]
    today_iso = date.today().isoformat()
    overdue = sum(1 for t in open_tasks if t.due_date and t.due_date < today_iso)
    total = len(all_tasks)
    rate = (len(done_tasks) / total) if total else 0.0

    completed_dates = {t.completed_at[:10] for t in done_tasks if t.completed_at}
    streak = 0
    cursor = date.today()
    while cursor.isoformat() in completed_dates:
        streak += 1
        cursor -= timedelta(days=1)

    return Stats(
        total=total,
        open=len(open_tasks),
        done=len(done_tasks),
        overdue=overdue,
        completion_rate=rate,
        streak_days=streak,
    )


def daily_completion_counts(task_service: TaskService, since: date) -> dict[str, int]:
    counts: dict[str, int] = {}
    since_iso = since.isoformat()
    for t in task_service.list_tasks(status=Status.DONE):
        if not t.completed_at:
            continue
        day = t.completed_at[:10]
        if day < since_iso:
            continue
        counts[day] = counts.get(day, 0) + 1
    return counts


_HEATMAP_DENSITY = " ░▒▓█"
HEATMAP_WEEKS = 12
HEATMAP_WEEKDAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def build_heatmap_lines(
    counts: dict[str, int], weeks: int = HEATMAP_WEEKS, today: date | None = None
) -> list[str]:
    """7 lines (Mon..Sun), each `weeks` chars wide — one rolling 7-day column
    per week, most recent on the right."""
    today = today or date.today()
    total_days = weeks * 7
    start = today - timedelta(days=total_days - 1)
    grid = [[" "] * weeks for _ in range(7)]

    cursor = start
    for day_index in range(total_days):
        week_idx = day_index // 7
        weekday = cursor.weekday()
        count = counts.get(cursor.isoformat(), 0)
        symbol = _HEATMAP_DENSITY[min(count, len(_HEATMAP_DENSITY) - 1)]
        grid[weekday][week_idx] = symbol
        cursor += timedelta(days=1)

    return ["".join(row) for row in grid]
