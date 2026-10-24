from __future__ import annotations

from typing import TYPE_CHECKING

from rich.markup import escape
from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Static

from nokkam.presentation.charts import column_chart, hbar
from nokkam.presentation.widgets.app_header import AppHeader
from nokkam.services.project_summary_service import compact_minutes, format_minutes
from nokkam.services.time_report_service import TimeReport, compute_time_report

if TYPE_CHECKING:
    from nokkam.app import NokkamApp

NAME_WIDTH = 18
BAR_WIDTH = 28
CHART_HEIGHT = 5
EMPTY = "[dim]No time tracked in this period. Select a task and press t to start a timer.[/]"
RANGES = {7: "last 7 days", 30: "last 30 days", 0: "all time"}


def _range_label(days: int | None) -> str:
    return RANGES[days or 0]


def render_time_report(report: TimeReport) -> str:
    header = f"[bold $accent]Time tracked[/] · {_range_label(report.days)}"
    if report.total_minutes <= 0:
        return f"{header}\n\n{EMPTY}"

    lines = [
        header
        + f"   [dim]total[/] {format_minutes(report.total_minutes)}"
        + f" · [dim]avg[/] {format_minutes(report.average_per_day)}/day",
        "",
    ]
    peak = report.projects[0].minutes
    for project in report.projects:
        share = project.minutes / report.total_minutes
        lines.append(
            f"[{project.color}]●[/] {escape(project.name[:NAME_WIDTH]):<{NAME_WIDTH}} "
            f"[{project.color}]{hbar(project.minutes, peak, BAR_WIDTH)}[/] "
            f"{format_minutes(project.minutes):>8} {share:>4.0%}"
        )

    values = [minutes for _, minutes in report.daily]
    weekly = len(values) <= 7
    col_width = 4
    peak_day, peak_minutes = max(report.daily, key=lambda item: item[1])
    lines += [
        "",
        f"[bold $accent]By day[/] · last {len(values)} days   "
        f"[dim]peak[/] {format_minutes(peak_minutes)}"
        f" [dim]on {peak_day:%a %d %b}[/]",
    ]
    chart = column_chart(
        values, CHART_HEIGHT, col_width=col_width if weekly else 1, gap=1 if weekly else 0
    )
    lines += [f"  {row}" for row in chart]
    if weekly:
        lines.append("  " + " ".join(f"{f'{day:%a}':^{col_width}}" for day, _ in report.daily))
        lines.append("  " + " ".join(f"{compact_minutes(m):^{col_width}}" for _, m in report.daily))
    else:
        first, last = f"{report.daily[0][0]:%b %d}", f"{report.daily[-1][0]:%b %d}"
        lines.append("  " + first + " " * max(len(values) - len(first) - len(last), 1) + last)
    return "\n".join(lines)


class TimeReportScreen(Screen):
    """Time tracked per project (bars) and per day (columns)."""

    app: NokkamApp

    BINDINGS = [
        Binding("1", "set_range(7)", "7 days"),
        Binding("2", "set_range(30)", "30 days"),
        Binding("3", "set_range(0)", "All time"),
        Binding("escape,backspace", "back", "Back"),
    ]

    def __init__(self, days: int | None = 7) -> None:
        super().__init__()
        self.days = days

    def compose(self) -> ComposeResult:
        yield AppHeader(subtitle="time")
        yield Static("", id="time-report-body", classes="panel")
        yield Footer()

    def on_mount(self) -> None:
        self._render_report()

    def _render_report(self) -> None:
        report = compute_time_report(
            self.app.task_service, self.app.project_repo, self.app.time_log_repo, self.days
        )
        self.query_one("#time-report-body", Static).update(render_time_report(report))

    def action_set_range(self, days: int) -> None:
        self.days = days or None
        self._render_report()

    def action_back(self) -> None:
        self.app.pop_screen()
