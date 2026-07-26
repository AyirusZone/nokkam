"""cad-tui entrypoint. Wires config -> db -> repositories -> services -> UI."""

from __future__ import annotations

import sqlite3
import sys
from collections.abc import Iterable

from textual.app import App, SystemCommand
from textual.screen import Screen

from cad_tui.config import AppConfig, load_config
from cad_tui.data.db import connect
from cad_tui.data.migrations import apply_migrations
from cad_tui.data.repositories.dependency_repository import DependencyRepository
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
from cad_tui.services.reminder_service import ReminderService
from cad_tui.services.task_service import TaskService
from cad_tui.services.time_tracking_service import TimeTrackingService
from cad_tui.services.undo import UndoStack

REMINDER_CHECK_INTERVAL_SECONDS = 60


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

        self.push_screen(HomeScreen())

        self._check_reminders()
        self.set_interval(REMINDER_CHECK_INTERVAL_SECONDS, self._check_reminders)

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
