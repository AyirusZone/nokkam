from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Header, Static

from cad_tui.services.stats_service import compute_stats

BAR_WIDTH = 24


class StatsScreen(Screen):
    BINDINGS = [Binding("escape,backspace", "back", "Back")]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("", id="stats-body", classes="panel")
        yield Footer()

    def on_mount(self) -> None:
        stats = compute_stats(self.app.task_service)
        filled = round(stats.completion_rate * BAR_WIDTH)
        bar = "█" * filled + "░" * (BAR_WIDTH - filled)
        body = (
            "[bold accent]Stats[/]\n\n"
            f"Open tasks       {stats.open}\n"
            f"Done tasks       {stats.done}\n"
            f"Overdue          {stats.overdue}\n"
            f"Completion       {bar} {stats.completion_rate:.0%}\n"
            f"Current streak   {stats.streak_days} day(s)\n"
        )
        self.query_one("#stats-body", Static).update(body)

    def action_back(self) -> None:
        self.app.pop_screen()
