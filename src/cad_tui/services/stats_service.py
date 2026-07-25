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
