"""One active timer at a time (Toggl-style): starting a new one stops
whatever was running first."""

from __future__ import annotations

from cad_tui.data.repositories.time_log_repository import TimeLogRepository


class TimeTrackingService:
    def __init__(self, repo: TimeLogRepository) -> None:
        self.repo = repo
        self._active_task_id: int | None = None
        self._active_log_id: int | None = None

    @property
    def active_task_id(self) -> int | None:
        return self._active_task_id

    def toggle(self, task_id: int) -> bool:
        """Start/stop the timer for task_id. Returns True if now running."""
        if self._active_task_id == task_id and self._active_log_id is not None:
            self.repo.stop(self._active_log_id)
            self._active_task_id = None
            self._active_log_id = None
            return False

        if self._active_log_id is not None:
            self.repo.stop(self._active_log_id)

        self._active_log_id = self.repo.start(task_id)
        self._active_task_id = task_id
        return True

    def total_minutes(self, task_id: int) -> int:
        return self.repo.total_minutes_for_task(task_id)
