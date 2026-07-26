from __future__ import annotations

from datetime import date, timedelta
from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Static

from nokkam.presentation.widgets.app_header import AppHeader
from nokkam.services.stats_service import (
    HEATMAP_WEEKDAY_LABELS,
    HEATMAP_WEEKS,
    build_heatmap_lines,
    compute_stats,
    daily_completion_counts,
)

if TYPE_CHECKING:
    from nokkam.app import NokkamApp

BAR_WIDTH = 24


class StatsScreen(Screen):
    app: NokkamApp

    BINDINGS = [Binding("escape,backspace", "back", "Back")]

    def compose(self) -> ComposeResult:
        yield AppHeader(subtitle="stats")
        yield Static("", id="stats-body", classes="panel")
        yield Footer()

    def on_mount(self) -> None:
        stats = compute_stats(self.app.task_service)
        filled = round(stats.completion_rate * BAR_WIDTH)
        bar = "█" * filled + "░" * (BAR_WIDTH - filled)

        since = date.today() - timedelta(weeks=HEATMAP_WEEKS)
        counts = daily_completion_counts(self.app.task_service, since)
        heatmap_lines = build_heatmap_lines(counts, weeks=HEATMAP_WEEKS)
        heatmap_block = "\n".join(
            f"{label}  {line}"
            for label, line in zip(HEATMAP_WEEKDAY_LABELS, heatmap_lines, strict=True)
        )

        body = (
            f"[dim]open tasks[/]       {stats.open}\n"
            f"[dim]done tasks[/]       {stats.done}\n"
            f"[dim]overdue[/]          {stats.overdue}\n"
            f"[dim]completion[/]       {bar} {stats.completion_rate:.0%}\n"
            f"[dim]current streak[/]   {stats.streak_days} day(s)\n\n"
            f"[dim]last {HEATMAP_WEEKS} weeks[/]\n"
            f"{heatmap_block}\n"
        )
        self.query_one("#stats-body", Static).update(body)

    def action_back(self) -> None:
        self.app.pop_screen()
