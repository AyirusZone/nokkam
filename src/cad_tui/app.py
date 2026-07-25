"""cad-tui entrypoint. Wires config -> db -> repositories -> services -> UI."""

from __future__ import annotations

import sqlite3
from typing import Iterable

from textual.app import App, SystemCommand
from textual.screen import Screen

from cad_tui.config import AppConfig, load_config
from cad_tui.data.db import connect
from cad_tui.data.migrations import apply_migrations
from cad_tui.data.repositories.project_repository import ProjectRepository
from cad_tui.data.repositories.recurrence_repository import RecurrenceRepository
from cad_tui.data.repositories.tag_repository import TagRepository
from cad_tui.data.repositories.task_repository import TaskRepository
from cad_tui.presentation.command_provider import TaskSearchProvider
from cad_tui.presentation.screens.task_list import TaskListScreen
from cad_tui.presentation.theme import THEMES
from cad_tui.services.task_service import TaskService
from cad_tui.services.undo import UndoStack


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
        for theme in THEMES:
            self.register_theme(theme)
        self.theme = self.config.theme

        self.db = connect(self.config.db_path)
        apply_migrations(self.db)

        self.task_repo = TaskRepository(self.db)
        self.project_repo = ProjectRepository(self.db)
        self.tag_repo = TagRepository(self.db)
        self.recurrence_repo = RecurrenceRepository(self.db)
        self.undo_stack = UndoStack()
        self.task_service = TaskService(self.task_repo, self.undo_stack, self.recurrence_repo)

        self.push_screen(TaskListScreen())

    def on_unmount(self) -> None:
        if self.db is not None:
            self.db.close()

    def action_toggle_theme(self) -> None:
        self.theme = "cad-light" if self.theme == "cad-dark" else "cad-dark"

    def get_system_commands(self, screen: Screen) -> Iterable[SystemCommand]:
        yield from super().get_system_commands(screen)
        yield SystemCommand("Add task", "Create a new task", self._cmd_add_task)
        yield SystemCommand(
            "Quick add", "Fast capture, e.g. \"Buy milk tmrw 3pm\"", self._cmd_quick_add
        )
        yield SystemCommand("Undo", "Undo the last action", self._cmd_undo)
        yield SystemCommand("Open calendar", "Switch to the calendar view", self._cmd_open_calendar)
        yield SystemCommand(
            "Open agenda", "Rolling 14-day agenda of upcoming tasks", self._cmd_open_agenda
        )
        yield SystemCommand(
            "Show stats", "Completion rate and streak", self._cmd_open_stats
        )
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
            "Smart list: All tasks", "Clear the smart-list filter", lambda: self._cmd_smart_list(None)
        )

    def _goto_task_list(self) -> TaskListScreen:
        while not isinstance(self.screen, TaskListScreen):
            self.pop_screen()
        return self.screen

    def _cmd_add_task(self) -> None:
        self._goto_task_list().action_add_task()

    def _cmd_quick_add(self) -> None:
        self._goto_task_list().action_quick_add()

    def _cmd_undo(self) -> None:
        self._goto_task_list().action_undo()

    def _cmd_open_calendar(self) -> None:
        self._goto_task_list()
        from cad_tui.presentation.screens.calendar_screen import CalendarScreen

        self.push_screen(CalendarScreen())

    def _cmd_open_agenda(self) -> None:
        self._goto_task_list()
        from cad_tui.presentation.screens.agenda_screen import AgendaScreen

        self.push_screen(AgendaScreen())

    def _cmd_open_stats(self) -> None:
        self._goto_task_list()
        from cad_tui.presentation.screens.stats_screen import StatsScreen

        self.push_screen(StatsScreen())

    def _cmd_smart_list(self, filter_name: str | None) -> None:
        self._goto_task_list().set_smart_filter(filter_name)

    def jump_to_task(self, task_id: int) -> None:
        self._goto_task_list().select_task_by_id(task_id)


def main() -> None:
    CadTuiApp().run()


if __name__ == "__main__":
    main()
