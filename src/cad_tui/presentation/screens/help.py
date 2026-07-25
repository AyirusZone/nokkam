from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Static

HELP_TEXT = """\
[bold accent]cad-tui — keybindings[/]

  a          add task
  e          edit selected task
  d          delete selected task
  space      toggle complete
  j / down   move down
  k / up     move up
  u          undo last action
  ctrl+t     toggle theme
  ?          this help
  q          quit
  esc        close this dialog
"""


class HelpModal(ModalScreen[None]):
    BINDINGS = [("escape", "close_help", "Close"), ("question_mark", "close_help", "Close")]

    def compose(self) -> ComposeResult:
        with Vertical(classes="panel", id="help-panel"):
            yield Static(HELP_TEXT)

    def action_close_help(self) -> None:
        self.dismiss(None)
