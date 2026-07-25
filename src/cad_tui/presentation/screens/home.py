"""Phase-1 placeholder screen — proves the scaffold boots and themes correctly."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Center, Middle
from textual.screen import Screen
from textual.widgets import Footer, Header, Static


class HomeScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header()
        with Middle():
            with Center():
                yield Static(
                    "cad-tui\n"
                    "[dim]Phase 1 scaffold — task/calendar UI lands in later phases.[/]\n"
                    "[dim]ctrl+t[/] toggle theme   [dim]q[/] quit",
                    classes="panel",
                )
        yield Footer()
