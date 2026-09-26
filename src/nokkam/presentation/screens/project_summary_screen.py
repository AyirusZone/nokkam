from __future__ import annotations

from typing import TYPE_CHECKING

from rich.markup import escape
from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Static

from nokkam.presentation.widgets.app_header import AppHeader
from nokkam.services.project_summary_service import (
    RECENT_DAYS,
    compute_project_summaries,
    format_minutes,
)

if TYPE_CHECKING:
    from nokkam.app import NokkamApp

BAR_WIDTH = 10
NAME_WIDTH = 20


def _truncate(name: str) -> str:
    return name if len(name) <= NAME_WIDTH else name[: NAME_WIDTH - 1] + "…"


class ProjectSummaryScreen(Screen):
    """Progress and time tracked per project."""

    app: NokkamApp

    BINDINGS = [Binding("escape,backspace", "back", "Back")]

    def compose(self) -> ComposeResult:
        yield AppHeader(subtitle="projects")
        yield Static("", id="project-summary-body", classes="panel")
        yield Footer()

    def on_mount(self) -> None:
        summaries = compute_project_summaries(
            self.app.task_service, self.app.project_repo, self.app.time_log_repo
        )
        lines = [
            f"[dim]{'project':<{NAME_WIDTH + 2}}{'done':>7}{'open':>6}{'late':>6}  "
            f"{'progress':<{BAR_WIDTH + 5}}{'time':>8}{f'{RECENT_DAYS}d':>8}[/]"
        ]
        for s in summaries:
            filled = round(s.progress * BAR_WIDTH)
            bar = "█" * filled + "░" * (BAR_WIDTH - filled)
            name = escape(_truncate(s.name))
            late = f"[bold red]{s.overdue:>6}[/]" if s.overdue else f"{'·':>6}"
            lines.append(
                f"[{s.color}]●[/] {name:<{NAME_WIDTH}}"
                f"{f'{s.done}/{s.total}':>7}{s.open:>6}{late}  "
                f"{bar} {s.progress:>4.0%}"
                f"{format_minutes(s.minutes_total):>8}{format_minutes(s.minutes_recent):>8}"
            )
        if len(lines) == 1:
            lines.append("[dim]No projects yet — press a on the Projects tab to add one.[/]")
        self.query_one("#project-summary-body", Static).update("\n".join(lines))

    def action_back(self) -> None:
        self.app.pop_screen()
