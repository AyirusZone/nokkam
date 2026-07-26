"""Shared task-row list item, used by HomeScreen and AgendaScreen."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.widgets import ListItem, Static

from nokkam.domain.icons import icon_for_title
from nokkam.domain.models import Priority, Status, Task

if TYPE_CHECKING:
    from nokkam.app import NokkamApp

# Keyed by plain int (not Priority) since Task.priority is a plain int field;
# Priority is an IntEnum so the values still compare equal at runtime.
PRIORITY_CLASS: dict[int, str] = {
    Priority.HIGH: "priority-high",
    Priority.MEDIUM: "priority-medium",
    Priority.LOW: "priority-low",
}


class TaskRow(ListItem):
    app: NokkamApp

    def __init__(self, task: Task, depth: int = 0, show_project: bool = True) -> None:
        super().__init__(classes=PRIORITY_CLASS.get(task.priority, "priority-medium"))
        self.model = task
        self.depth = depth
        self.show_project = show_project

    def compose(self) -> ComposeResult:
        assert self.model.id is not None  # rows are only ever built from persisted tasks
        done = self.model.status == Status.DONE
        indent = "  " * self.depth
        check = "[$success]✓[/] " if done else "  "
        recurring = " [$secondary]↻[/]" if self.model.recurrence_id else ""
        timing = ""
        if self.app.time_tracking.active_task_id == self.model.id:
            timing = (
                " [$foreground 50%]⏸[/]" if self.app.time_tracking.is_paused else " [$accent]⏱[/]"
            )
        blocked = (
            " [$warning]⛔[/]"
            if not done and self.app.task_service.is_blocked(self.model.id)
            else ""
        )
        due = ""
        if self.model.due_date:
            due = f"   [dim]{self.model.due_date} {self.model.due_time or ''}[/]".rstrip()
        project_dot = ""
        if self.show_project and self.model.project_id is not None:
            project = self.app.project_repo.get(self.model.project_id)
            if project is not None:
                project_dot = f"[{project.color}]●[/] "
        # A private task's title never renders — no icon either, since an
        # auto-picked icon (e.g. ✈ for "flight") would leak what the hidden
        # title is about.
        if self.model.private:
            icon_part = ""
            title = "•••••"
        else:
            icon = icon_for_title(self.model.title, self.app.config.icons)
            icon_part = f"{icon} " if icon else ""
            title = self.model.title
        if done:
            title = f"[dim strike]{title}[/]"
        yield Static(
            f"{indent}{check}{project_dot}{icon_part}{title}{recurring}{timing}{blocked}{due}"
        )
