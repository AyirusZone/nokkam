"""Add/edit task modal. Returns a TaskFormResult (or None on cancel) via dismiss()."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Checkbox, Input, Label, Select, Static
from textual.widgets.select import NoSelection

from nokkam.domain.models import Priority, Task
from nokkam.domain.recurrence import RecurrenceError, RecurrenceRule, parse_recurrence
from nokkam.presentation.widgets.recurrence_presets import (
    CUSTOM,
    RECURRENCE_PRESETS,
    preset_for,
)

if TYPE_CHECKING:
    from nokkam.app import NokkamApp

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
    recurrence: RecurrenceRule | None
    blocked_by_title: str | None
    private: bool


class TaskFormModal(ModalScreen[TaskFormResult | None]):
    app: NokkamApp

    BINDINGS = [("escape", "cancel", "Cancel")]

    def __init__(
        self,
        task: Task | None = None,
        project_name: str = "",
        tag_names: str = "",
        default_due_date: str = "",
        recurrence: str = "",
        parent_title: str = "",
        blocked_by_title: str = "",
    ) -> None:
        super().__init__()
        self.editing = task
        self._project_name = project_name
        self._tag_names = tag_names
        self._default_due_date = default_due_date
        self._recurrence = recurrence
        self._parent_title = parent_title
        self._blocked_by_title = blocked_by_title

    def compose(self) -> ComposeResult:
        t = self.editing
        due_date_value = (t.due_date or "") if t else self._default_due_date
        heading = "Edit task" if t else ("Add subtask" if self._parent_title else "Add task")
        with Vertical(classes="panel", id="task-form"):
            yield Static(heading, classes="accent-text")
            if self._parent_title:
                yield Static(f"[dim]under: {self._parent_title}[/]")
            yield Label("Title")
            yield Input(value=t.title if t else "", id="title", placeholder="Task title")
            yield Label("Notes")
            yield Input(value=(t.notes or "") if t else "", id="notes", placeholder="Optional")
            yield Label("Due date (YYYY-MM-DD)  /  Due time (HH:MM)")
            with Horizontal(classes="field-row"):
                yield Input(value=due_date_value, id="due_date", placeholder="2026-08-01")
                yield Input(
                    value=(t.due_time or "") if t else "", id="due_time", placeholder="14:30"
                )
            yield Label("Priority")
            yield Select(
                PRIORITY_OPTIONS,
                value=t.priority if t else self.app.config.default_priority,
                id="priority",
                allow_blank=False,
            )
            yield Label("Repeats  (pick one, or type your own: every 2 weeks, every mon,fri)")
            with Horizontal(classes="field-row"):
                yield Select(
                    RECURRENCE_PRESETS,
                    value=preset_for(self._recurrence),
                    id="recurrence-preset",
                    allow_blank=False,
                )
                yield Input(value=self._recurrence, id="recurrence", placeholder="Custom rule")
            yield Label("Project  /  Tags (comma separated)")
            with Horizontal(classes="field-row"):
                yield Input(value=self._project_name, id="project", placeholder="Optional project")
                yield Input(value=self._tag_names, id="tags", placeholder="home, urgent")
            yield Label("Blocked by (task title)")
            yield Input(value=self._blocked_by_title, id="blocked_by", placeholder="Optional")
            yield Checkbox(
                "Private (mask title in lists)", value=t.private if t else False, id="private"
            )
            with Horizontal(classes="form-actions"):
                yield Button("Save", variant="primary", id="save")
                yield Button("Cancel", id="cancel")

    def on_mount(self) -> None:
        self.query_one("#title", Input).focus()

    @on(Select.Changed, "#recurrence-preset")
    def preset_chosen(self, event: Select.Changed) -> None:
        """Picking a preset fills the rule field; "Custom…" hands it to you."""
        rule_input = self.query_one("#recurrence", Input)
        if event.value == CUSTOM:
            rule_input.focus()
        elif isinstance(event.value, str):
            rule_input.value = event.value

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
        # allow_blank=False on the Select guarantees a real value, never NoSelection.
        assert not isinstance(priority, NoSelection)
        try:
            recurrence = parse_recurrence(self.query_one("#recurrence", Input).value)
        except RecurrenceError as exc:
            self.notify(str(exc), title="Repeats", severity="error")
            self.query_one("#recurrence", Input).focus()
            return
        blocked_by_title = self.query_one("#blocked_by", Input).value.strip() or None
        private = self.query_one("#private", Checkbox).value

        self.dismiss(
            TaskFormResult(
                title=title,
                notes=notes,
                priority=priority,
                due_date=due_date,
                due_time=due_time,
                project_name=project_name,
                tag_names=tag_names,
                recurrence=recurrence,
                blocked_by_title=blocked_by_title,
                private=private,
            )
        )

    @on(Button.Pressed, "#cancel")
    def cancel_button(self) -> None:
        self.dismiss(None)

    def action_cancel(self) -> None:
        self.dismiss(None)
