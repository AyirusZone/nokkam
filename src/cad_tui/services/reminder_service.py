"""Due-soon detection. Each task is surfaced at most once (dedup via the
reminder table), regardless of how often the check runs."""

from __future__ import annotations

from datetime import datetime, timedelta

from cad_tui.data.repositories.reminder_repository import ReminderRepository
from cad_tui.domain.models import Status, Task
from cad_tui.services.task_service import TaskService

DEFAULT_WINDOW_MINUTES = 15


class ReminderService:
    def __init__(self, task_service: TaskService, reminder_repo: ReminderRepository) -> None:
        self.task_service = task_service
        self.reminder_repo = reminder_repo

    def due_soon(
        self, *, window_minutes: int = DEFAULT_WINDOW_MINUTES, now: datetime | None = None
    ) -> list[Task]:
        now = now or datetime.now()
        horizon = now + timedelta(minutes=window_minutes)
        newly_due: list[Task] = []
        for task in self.task_service.list_tasks(status=Status.OPEN):
            if not task.due_date:
                continue
            try:
                due_dt = datetime.fromisoformat(f"{task.due_date}T{task.due_time or '00:00'}")
            except ValueError:
                continue
            if now <= due_dt <= horizon and not self.reminder_repo.has_been_sent("task", task.id):
                newly_due.append(task)
                self.reminder_repo.mark_sent("task", task.id, due_dt.isoformat())
        return newly_due
