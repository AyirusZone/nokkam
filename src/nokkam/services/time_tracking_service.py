"""One active timer at a time (Toggl-style): starting a new one stops
whatever was running first. A running timer can also be paused/resumed
without fully stopping it — pausing closes the current log segment (so
its duration is already banked) and resuming opens a fresh one for the
same task, so total_minutes always reflects real logged time."""

from __future__ import annotations

from nokkam.data.repositories.time_log_repository import TimeLogRepository


class TimeTrackingService:
    def __init__(self, repo: TimeLogRepository) -> None:
        self.repo = repo
        self._active_task_id: int | None = None
        self._active_log_id: int | None = None
        self._paused = False

    @property
    def active_task_id(self) -> int | None:
        return self._active_task_id

    @property
    def is_paused(self) -> bool:
        return self._paused

    def toggle(self, task_id: int) -> bool:
        """Start/stop the timer for task_id. Returns True if now running."""
        if self._active_task_id == task_id and (self._active_log_id is not None or self._paused):
            if self._active_log_id is not None:
                self.repo.stop(self._active_log_id)
            self._active_task_id = None
            self._active_log_id = None
            self._paused = False
            return False

        if self._active_log_id is not None:
            self.repo.stop(self._active_log_id)

        self._active_log_id = self.repo.start(task_id)
        self._active_task_id = task_id
        self._paused = False
        return True

    def toggle_pause(self) -> bool | None:
        """Pause/resume the current timer in place. Returns True if now
        paused, False if now running again, None if no timer is active."""
        if self._active_task_id is None:
            return None
        if self._paused:
            self._active_log_id = self.repo.start(self._active_task_id)
            self._paused = False
            return False
        if self._active_log_id is not None:
            self.repo.stop(self._active_log_id)
            self._active_log_id = None
        self._paused = True
        return True

    def total_minutes(self, task_id: int) -> int:
        return self.repo.total_minutes_for_task(task_id)
