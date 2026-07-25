"""Add/edit task modal. Returns a TaskFormResult (or None on cancel) via dismiss()."""

from __future__ import annotations

from dataclasses import dataclass

from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Select, Static

from cad_tui.domain.models import Priority, Task

PRIORITY_OPTIONS = [("High", Priority.HIGH), ("Medium", Priority.MEDIUM), ("Low", Priority.LOW)]


@dataclass
class TaskFormResult:
    title: str
    notes: str | None
    priority: int
    due_date: str | None
    due_time: str | None
    project_name: str | None
    tag_names: list[str]


class TaskFormModal(ModalScreen[TaskFormResult | None]):
    BINDINGS = [("escape", "cancel", "Cancel")]

    def __init__(
        self,
        task: Task | None = None,
        project_name: str = "",
        tag_names: str = "",
    ) -> None:
        super().__init__()
        self.editing = task
        self._project_name = project_name
        self._tag_names = tag_names

    def compose(self) -> ComposeResult:
        t = self.editing
        with Vertical(classes="panel", id="task-form"):
            yield Static("Edit task" if t else "Add task", classes="accent-text")
            yield Label("Title")
            yield Input(value=t.title if t else "", id="title", placeholder="Task title")
            yield Label("Notes")
            yield Input(value=(t.notes or "") if t else "", id="notes", placeholder="Optional")
            yield Label("Priority")
            yield Select(
                PRIORITY_OPTIONS,
                value=t.priority if t else Priority.MEDIUM,
                id="priority",
                allow_blank=False,
            )
            yield Label("Due date (YYYY-MM-DD)")
            yield Input(value=(t.due_date or "") if t else "", id="due_date", placeholder="2026-08-01")
            yield Label("Due time (HH:MM)")
            yield Input(value=(t.due_time or "") if t else "", id="due_time", placeholder="14:30")
            yield Label("Project")
            yield Input(value=self._project_name, id="project", placeholder="Optional project")
            yield Label("Tags (comma separated)")
            yield Input(value=self._tag_names, id="tags", placeholder="home, urgent")
            with Horizontal():
                yield Button("Save", variant="primary", id="save")
                yield Button("Cancel", id="cancel")

    def on_mount(self) -> None:
        self.query_one("#title", Input).focus()

    @on(Button.Pressed, "#save")
    def save(self) -> None:
        title = self.query_one("#title", Input).value.strip()
        if not title:
            self.query_one("#title", Input).focus()
            return
        notes = self.query_one("#notes", Input).value.strip() or None
        priority = self.query_one("#priority", Select).value
        due_date = self.query_one("#due_date", Input).value.strip() or None
        due_time = self.query_one("#due_time", Input).value.strip() or None
        project_name = self.query_one("#project", Input).value.strip() or None
        tag_names = [t for t in self.query_one("#tags", Input).value.split(",") if t.strip()]

        self.dismiss(
            TaskFormResult(
                title=title,
                notes=notes,
                priority=priority,
                due_date=due_date,
                due_time=due_time,
                project_name=project_name,
                tag_names=tag_names,
            )
        )

    @on(Button.Pressed, "#cancel")
    def cancel_button(self) -> None:
        self.dismiss(None)

    def action_cancel(self) -> None:
        self.dismiss(None)
