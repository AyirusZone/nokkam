"""Shared task-row list item, used by HomeScreen and AgendaScreen."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.widgets import ListItem, Static

from cad_tui.domain.models import Priority, Status, Task

PRIORITY_CLASS = {
    Priority.HIGH: "priority-high",
    Priority.MEDIUM: "priority-medium",
    Priority.LOW: "priority-low",
}


class TaskRow(ListItem):
    def __init__(self, task: Task, depth: int = 0) -> None:
        super().__init__(classes=PRIORITY_CLASS.get(task.priority, "priority-medium"))
        self.model = task
        self.depth = depth

    def compose(self) -> ComposeResult:
        done = self.model.status == Status.DONE
        indent = "  " * self.depth
        check = "[$success]✓[/] " if done else "  "
        recurring = " [$secondary]↻[/]" if self.model.recurrence_id else ""
        timing = " [$accent]⏱[/]" if self.app.time_tracking.active_task_id == self.model.id else ""
        blocked = (
            " [$warning]⛔[/]"
            if not done and self.app.task_service.is_blocked(self.model.id)
            else ""
        )
        due = ""
        if self.model.due_date:
            due = f"   [dim]{self.model.due_date} {self.model.due_time or ''}[/]".rstrip()
        title = self.model.title
        if done:
            title = f"[dim strike]{title}[/]"
        yield Static(f"{indent}{check}{title}{recurring}{timing}{blocked}{due}")
