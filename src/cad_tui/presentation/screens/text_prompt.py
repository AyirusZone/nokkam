"""Generic single-line text prompt — used for naming a new project or tag."""

from __future__ import annotations

from textual import on
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, Static


class TextPromptModal(ModalScreen[str | None]):
    BINDINGS = [("escape", "cancel", "Cancel")]

    def __init__(self, heading: str, placeholder: str = "") -> None:
        super().__init__()
        self._heading = heading
        self._placeholder = placeholder

    def compose(self) -> ComposeResult:
        with Vertical(classes="panel", id="text-prompt"):
            yield Static(self._heading, classes="accent-text")
            yield Input(placeholder=self._placeholder, id="text-prompt-input")

    def on_mount(self) -> None:
        self.query_one("#text-prompt-input", Input).focus()

    @on(Input.Submitted, "#text-prompt-input")
    def submit(self, event: Input.Submitted) -> None:
        value = event.value.strip()
        self.dismiss(value or None)

    def action_cancel(self) -> None:
        self.dismiss(None)
