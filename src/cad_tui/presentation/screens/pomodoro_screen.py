"""25/5 focus timer. Self-contained — doesn't touch the task time log."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.timer import Timer
from textual.widgets import Static

if TYPE_CHECKING:
    from cad_tui.app import CadTuiApp

WORK_SECONDS = 25 * 60
BREAK_SECONDS = 5 * 60


class PomodoroScreen(ModalScreen[None]):
    app: CadTuiApp

    BINDINGS = [
        Binding("space", "toggle_pause", "Pause/Resume"),
        Binding("r", "reset", "Reset"),
        Binding("escape", "close", "Close"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.remaining = WORK_SECONDS
        self.on_break = False
        self.paused = False
        self._timer: Timer | None = None

    def compose(self) -> ComposeResult:
        with Vertical(classes="panel", id="pomodoro-panel"):
            yield Static("", id="pomodoro-display")

    def on_mount(self) -> None:
        self._timer = self.set_interval(1, self._tick)
        self._refresh_display()

    def _tick(self) -> None:
        if self.paused:
            return
        self.remaining -= 1
        if self.remaining <= 0:
            self._complete_session()
        self._refresh_display()

    def _complete_session(self) -> None:
        self.on_break = not self.on_break
        self.remaining = BREAK_SECONDS if self.on_break else WORK_SECONDS
        label = "Break time!" if self.on_break else "Back to work!"
        self.app.notify(label, title="Pomodoro")
        self.app.notify_desktop(label, title="Pomodoro")

    def _refresh_display(self) -> None:
        minutes, seconds = divmod(max(self.remaining, 0), 60)
        phase = "Break" if self.on_break else "Focus"
        state = "Paused" if self.paused else "Running"
        # The countdown is the one thing worth reading at a glance — give it
        # more visual weight than the surrounding labels: bold, accented
        # while running (dimmed once paused), and letter-spaced to read
        # larger than plain "MM:SS" would in a terminal's fixed line height.
        time_color = "$foreground 50%" if self.paused else "$accent"
        big_time = " ".join(f"{minutes:02d}:{seconds:02d}")
        self.query_one("#pomodoro-display", Static).update(
            f"[bold $accent]{phase}[/]\n\n"
            f"[bold {time_color}]{big_time}[/]\n\n"
            f"[dim]{state} — space pause/resume, r reset, esc close[/]"
        )

    def action_toggle_pause(self) -> None:
        self.paused = not self.paused
        self._refresh_display()

    def action_reset(self) -> None:
        self.remaining = BREAK_SECONDS if self.on_break else WORK_SECONDS
        self.paused = False
        self._refresh_display()

    def action_close(self) -> None:
        if self._timer is not None:
            self._timer.stop()
        self.dismiss(None)
