"""Single-input fast capture: parses trailing date/time out of free text."""

from __future__ import annotations

from textual import on
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, Static

from nokkam.domain.nl_date_parser import QuickAddResult, parse_quick_text


class QuickAddModal(ModalScreen[QuickAddResult | None]):
    BINDINGS = [("escape", "cancel", "Cancel")]

    def compose(self) -> ComposeResult:
        with Vertical(classes="panel", id="quick-add"):
            yield Static(
                'Quick add  [dim]e.g. "Buy milk tmrw 3pm", "Standup fri 9:30"[/]',
                classes="accent-text",
            )
            yield Input(placeholder="Task title + optional date/time", id="quick-input")

    def on_mount(self) -> None:
        self.query_one("#quick-input", Input).focus()

    @on(Input.Submitted, "#quick-input")
    def submit(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        if not text:
            self.dismiss(None)
            return
        self.dismiss(parse_quick_text(text))

    def action_cancel(self) -> None:
        self.dismiss(None)
