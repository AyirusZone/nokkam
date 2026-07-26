"""Shared task-row list item, used by HomeScreen and AgendaScreen."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.widgets import ListItem, Static

from cad_tui.domain.models import Priority, Status, Task

if TYPE_CHECKING:
    from cad_tui.app import CadTuiApp

# Keyed by plain int (not Priority) since Task.priority is a plain int field;
# Priority is an IntEnum so the values still compare equal at runtime.
PRIORITY_CLASS: dict[int, str] = {
    Priority.HIGH: "priority-high",
    Priority.MEDIUM: "priority-medium",
    Priority.LOW: "priority-low",
}


class TaskRow(ListItem):
    app: CadTuiApp

    def __init__(self, task: Task, depth: int = 0) -> None:
        super().__init__(classes=PRIORITY_CLASS.get(task.priority, "priority-medium"))
        self.model = task
        self.depth = depth

    def compose(self) -> ComposeResult:
        assert self.model.id is not None  # rows are only ever built from persisted tasks
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
