from __future__ import annotations

from typing import TYPE_CHECKING

from rich.markup import escape
from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Static

from nokkam.domain.habits import LATE, ON_TIME, OVERDUE, PENDING
from nokkam.presentation.widgets.app_header import AppHeader
from nokkam.services.habit_service import HISTORY_LENGTH, Habit, compute_habits

if TYPE_CHECKING:
    from nokkam.app import NokkamApp

NAME_WIDTH = 24
RULE_WIDTH = 24

_MARKS = {
    ON_TIME: "[$success]■[/]",
    LATE: "[$warning]▲[/]",
    PENDING: "[dim]□[/]",
    OVERDUE: "[$error]✗[/]",
}
LEGEND = "[$success]■[/] on time   [$warning]▲[/] late   [dim]□[/] upcoming   [$error]✗[/] missed"
EMPTY = (
    "[dim]No habits yet — a habit is any recurring task. Add one with Repeats set to\n"
    "e.g. every day, then complete it on time to build a streak.[/]"
)


def _truncate(text: str, width: int) -> str:
    return text if len(text) <= width else text[: width - 1] + "…"


def render_habits(habits: list[Habit]) -> str:
    if not habits:
        return EMPTY
    lines = [
        f"[dim]{'habit':<{NAME_WIDTH}}{'streak':>7}{'best':>6}{'on time':>9}  "
        f"{'last ' + str(HISTORY_LENGTH):<{HISTORY_LENGTH + 2}}repeats[/]"
    ]
    for habit in habits:
        marks = "".join(_MARKS[state] for state in habit.history)
        marks += " " * (HISTORY_LENGTH - len(habit.history))
        streak = (
            f"[bold $accent]{habit.current_streak:>7}[/]"
            if habit.current_streak
            else f"[dim]{0:>7}[/]"
        )
        rate = f"{habit.on_time_rate:>8.0%}" if habit.done else f"{'—':>8}"
        row = (
            f"{escape(_truncate(habit.title, NAME_WIDTH - 1)):<{NAME_WIDTH - 1}} "
            f"{streak}{habit.best_streak:>6}{rate}  {marks}  "
            f"[dim]{escape(_truncate(habit.rule_text, RULE_WIDTH))}[/]"
        )
        lines.append(row if habit.active else f"[dim]{row}[/]")
    ended = sum(1 for h in habits if not h.active)
    lines.append("")
    lines.append(LEGEND)
    if ended:
        lines.append(f"[dim]{ended} ended (dimmed): no open occurrence left[/]")
    return "\n".join(lines)


class HabitsScreen(Screen):
    """Streaks for every recurring task."""

    app: NokkamApp

    BINDINGS = [Binding("escape,backspace", "back", "Back")]

    def compose(self) -> ComposeResult:
        yield AppHeader(subtitle="habits")
        yield Static("", id="habits-body", classes="panel")
        yield Footer()

    def on_mount(self) -> None:
        habits = compute_habits(
            self.app.task_service, self.app.recurrence_repo, self.app.project_repo
        )
        self.query_one("#habits-body", Static).update(render_habits(habits))

    def action_back(self) -> None:
        self.app.pop_screen()
