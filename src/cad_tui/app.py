"""cad-tui entrypoint. Wires config -> db -> repositories -> services -> UI."""

from __future__ import annotations

import sqlite3
import sys
import time
from collections.abc import Iterable

from textual.app import App, SystemCommand
from textual.screen import Screen

from cad_tui.config import AppConfig, load_config
from cad_tui.data.db import connect
from cad_tui.data.migrations import apply_migrations
from cad_tui.data.repositories.dependency_repository import DependencyRepository
from cad_tui.data.repositories.event_repository import EventRepository
from cad_tui.data.repositories.project_repository import ProjectRepository
from cad_tui.data.repositories.recurrence_repository import RecurrenceRepository
from cad_tui.data.repositories.reminder_repository import ReminderRepository
from cad_tui.data.repositories.tag_repository import TagRepository
from cad_tui.data.repositories.task_repository import TaskRepository
from cad_tui.data.repositories.time_log_repository import TimeLogRepository
from cad_tui.infra.notification_adapter import send_notification
from cad_tui.presentation.command_provider import TaskSearchProvider
from cad_tui.presentation.screens.home_screen import HomeScreen
from cad_tui.presentation.theme import build_themes
from cad_tui.presentation.widgets.app_header import AppHeader
from cad_tui.services.ics_service import IcsService
from cad_tui.services.reminder_service import ReminderService
from cad_tui.services.task_service import TaskService
from cad_tui.services.time_tracking_service import TimeTrackingService
from cad_tui.services.undo import UndoStack

REMINDER_CHECK_INTERVAL_SECONDS = 60
TASK_TIMER_LABEL_MAX_TITLE = 20


class CadTuiApp(App):
    CSS_PATH = "presentation/styles/base.tcss"
    COMMANDS = App.COMMANDS | {TaskSearchProvider}
    BINDINGS = [
        ("ctrl+t", "toggle_theme", "Toggle theme"),
        ("ctrl+k", "command_palette", "Command palette"),
        ("q", "quit", "Quit"),
    ]

    def __init__(self, config: AppConfig | None = None) -> None:
        super().__init__()
        self.config = config or load_config()
        self.db: sqlite3.Connection | None = None
        self._timer_started_at: float | None = None
        self._timer_accumulated: float = 0.0

    def on_mount(self) -> None:
        for theme in build_themes(self.config.accent):
            self.register_theme(theme)
        self.theme = self.config.theme

        self.db = connect(self.config.db_path)
        apply_migrations(self.db)

        self.task_repo = TaskRepository(self.db)
        self.project_repo = ProjectRepository(self.db)
        self.tag_repo = TagRepository(self.db)
        self.recurrence_repo = RecurrenceRepository(self.db)
        self.dependency_repo = DependencyRepository(self.db)
        self.undo_stack = UndoStack()
        self.task_service = TaskService(
            self.task_repo, self.undo_stack, self.recurrence_repo, self.dependency_repo
        )
        self.time_log_repo = TimeLogRepository(self.db)
        self.time_tracking = TimeTrackingService(self.time_log_repo)
        self.reminder_repo = ReminderRepository(self.db)
        self.reminder_service = ReminderService(self.task_service, self.reminder_repo)
        self.event_repo = EventRepository(self.db)
        self.ics_service = IcsService(self.event_repo, self.config.ics_sources)

        self.push_screen(HomeScreen())

        self._check_reminders()
        self.set_interval(REMINDER_CHECK_INTERVAL_SECONDS, self._check_reminders)
        self.set_interval(1, self._tick_header_timers)
        if self.config.ics_sources:
            self.sync_ics()

    def on_unmount(self) -> None:
        if self.db is not None:
            self.db.close()

    def action_toggle_theme(self) -> None:
        self.theme = "cad-light" if self.theme == "cad-dark" else "cad-dark"

    def notify_desktop(self, message: str, title: str = "cad-tui") -> None:
        send_notification(message, title)

    def _check_reminders(self) -> None:
        for task in self.reminder_service.due_soon():
            self.notify(f"Due soon: {task.title}")
            self.notify_desktop(f"Due soon: {task.title}", title="cad-tui reminder")

    def toggle_task_timer(self, task_id: int) -> bool:
        """Start/stop the time-tracking timer for `task_id` and refresh every
        mounted header's live elapsed-time display accordingly."""
        running = self.time_tracking.toggle(task_id)
        self._timer_started_at = time.monotonic() if running else None
        self._timer_accumulated = 0.0
        self._tick_header_timers()
        return running

    def pause_resume_task_timer(self) -> bool | None:
        """Pause/resume the running timer in place. Returns True if now
        paused, False if now running again, None if no timer is active."""
        result = self.time_tracking.toggle_pause()
        if result is True:
            if self._timer_started_at is not None:
                self._timer_accumulated += time.monotonic() - self._timer_started_at
            self._timer_started_at = None
        elif result is False:
            self._timer_started_at = time.monotonic()
        self._tick_header_timers()
        return result

    def _tick_header_timers(self) -> None:
        label = self._active_timer_label()
        # App.query() doesn't reach into the screen stack — each pushed
        # screen owns its own AppHeader instance, so headers on screens
        # other than the current top one must be found by querying the
        # screens themselves.
        for screen in self.screen_stack:
            for header in screen.query(AppHeader):
                header.set_timer_text(label)

    def _active_timer_label(self) -> str | None:
        task_id = self.time_tracking.active_task_id
        if task_id is None:
            return None
        task = self.task_repo.get(task_id)
        if task is None:
            return None
        elapsed = self._timer_accumulated
        if self._timer_started_at is not None:
            elapsed += time.monotonic() - self._timer_started_at
        elapsed_int = int(elapsed)
        hours, remainder = divmod(elapsed_int, 3600)
        minutes, seconds = divmod(remainder, 60)
        elapsed_str = (
            f"{hours:02d}:{minutes:02d}:{seconds:02d}" if hours else f"{minutes:02d}:{seconds:02d}"
        )
        title = task.title
        if len(title) > TASK_TIMER_LABEL_MAX_TITLE:
            title = title[: TASK_TIMER_LABEL_MAX_TITLE - 1] + "…"
        if self._timer_started_at is None:
            return f"[bold $foreground 50%]⏸ {title} · {elapsed_str} paused[/]"
        return f"[bold $accent]⏱ {title} · {elapsed_str}[/]"

    def sync_ics(self) -> None:
        """Refreshes configured .ics sources on a background thread so a
        slow/unreachable source never freezes the UI, then updates the
        calendar once it's done."""
        self.run_worker(self._sync_ics_worker, thread=True, exclusive=True, group="ics-sync")

    def _sync_ics_worker(self) -> None:
        self.ics_service.refresh()
        self.call_from_thread(self._on_ics_synced)

    def _on_ics_synced(self) -> None:
        home = next((s for s in self.screen_stack if isinstance(s, HomeScreen)), None)
        if home is not None:
            home.refresh_all()

    def action_open_pomodoro(self) -> None:
        self._goto_home()
        from cad_tui.presentation.screens.pomodoro_screen import PomodoroScreen

        self.push_screen(PomodoroScreen())

    def get_system_commands(self, screen: Screen) -> Iterable[SystemCommand]:
        yield from super().get_system_commands(screen)
        yield SystemCommand("Add task", "Create a new task", self._cmd_add_task)
        yield SystemCommand(
            "Quick add", 'Fast capture, e.g. "Buy milk tmrw 3pm"', self._cmd_quick_add
        )
        yield SystemCommand("Undo", "Undo the last action", self._cmd_undo)
        yield SystemCommand(
            "Focus calendar", "Move focus to the calendar pane", self._cmd_focus_calendar
        )
        yield SystemCommand(
            "Open agenda", "Rolling 14-day agenda of upcoming tasks", self._cmd_open_agenda
        )
        yield SystemCommand("Show stats", "Completion rate and streak", self._cmd_open_stats)
        yield SystemCommand("Pomodoro", "Start a 25/5 focus timer", self.action_open_pomodoro)
        yield SystemCommand(
            "Smart list: Today", "Show only tasks due today", lambda: self._cmd_smart_list("today")
        )
        yield SystemCommand(
            "Smart list: Overdue",
            "Show only open tasks past their due date",
            lambda: self._cmd_smart_list("overdue"),
        )
        yield SystemCommand(
            "Smart list: This week",
            "Show only tasks due in the next 7 days",
            lambda: self._cmd_smart_list("week"),
        )
        yield SystemCommand(
            "Smart list: All tasks",
            "Clear the smart-list filter",
            lambda: self._cmd_smart_list(None),
        )

    def _goto_home(self) -> HomeScreen:
        while not isinstance(self.screen, HomeScreen):
            self.pop_screen()
        return self.screen

    def _cmd_add_task(self) -> None:
        self._goto_home().action_add_task()

    def _cmd_quick_add(self) -> None:
        self._goto_home().action_quick_add()

    def _cmd_undo(self) -> None:
        self._goto_home().action_undo()

    def _cmd_focus_calendar(self) -> None:
        self._goto_home().focus_calendar()

    def _cmd_open_agenda(self) -> None:
        self._goto_home()
        from cad_tui.presentation.screens.agenda_screen import AgendaScreen

        self.push_screen(AgendaScreen())

    def _cmd_open_stats(self) -> None:
        self._goto_home()
        from cad_tui.presentation.screens.stats_screen import StatsScreen

        self.push_screen(StatsScreen())

    def _cmd_smart_list(self, filter_name: str | None) -> None:
        self._goto_home().set_smart_filter(filter_name)

    def jump_to_task(self, task_id: int) -> None:
        self._goto_home().select_task_by_id(task_id)


def main() -> None:
    if len(sys.argv) > 1:
        from cad_tui.cli import run_cli

        sys.exit(run_cli(sys.argv[1:]))
    CadTuiApp().run()


if __name__ == "__main__":
    main()
