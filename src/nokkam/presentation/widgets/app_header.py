"""Minimal header: wordmark + view name + live clock on the left, per-screen
context (or the active task timer, when one is running) on the right."""

from __future__ import annotations

from contextlib import suppress
from datetime import datetime

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.css.query import NoMatches
from textual.timer import Timer
from textual.widgets import Static

WORDMARK = "nokkam"


class AppHeader(Horizontal):
    def __init__(self, subtitle: str = "", meta: str = "") -> None:
        super().__init__()
        self._subtitle = subtitle
        self._meta = meta
        self._timer_text: str | None = None
        self._clock: Timer | None = None

    def compose(self) -> ComposeResult:
        yield Static(self._render_left(), id="app-header-title")
        yield Static(self._render_right(), id="app-header-meta")

    def on_mount(self) -> None:
        self._clock = self.set_interval(1, self._tick_clock)

    def on_unmount(self) -> None:
        if self._clock is not None:
            self._clock.stop()

    @property
    def meta(self) -> str:
        return self._meta

    @property
    def timer_text(self) -> str | None:
        return self._timer_text

    @property
    def subtitle(self) -> str:
        return self._subtitle

    def _tick_clock(self) -> None:
        self._update_title()

    def _update_title(self) -> None:
        # Between a screen swap and this widget's on_unmount firing, the
        # header can briefly report is_mounted=True with its children
        # already gone — harmless to skip a single refresh in that window.
        with suppress(NoMatches):
            self.query_one("#app-header-title", Static).update(self._render_left())

    def _update_meta(self) -> None:
        with suppress(NoMatches):
            self.query_one("#app-header-meta", Static).update(self._render_right())

    def _render_left(self) -> str:
        sep = "  [dim]/[/]  " if self._subtitle else ""
        now = datetime.now().strftime("%a %d %b %Y  %H:%M:%S")
        return f"[bold $accent]{WORDMARK}[/]{sep}[dim]{self._subtitle}[/]   [dim]{now}[/]"

    def _render_right(self) -> str:
        # The timer label already carries its own markup (color differs
        # between running and paused), so it's rendered as-is here.
        if self._timer_text is not None:
            return self._timer_text
        return self._meta

    def set_subtitle(self, subtitle: str) -> None:
        self._subtitle = subtitle
        if self.is_mounted:
            self._update_title()

    def set_meta(self, meta: str) -> None:
        self._meta = meta
        if self.is_mounted:
            self._update_meta()

    def set_timer_text(self, text: str | None) -> None:
        """Overrides the right-hand meta with a running task timer's elapsed
        time; pass None to fall back to the screen's normal meta text."""
        self._timer_text = text
        if self.is_mounted:
            self._update_meta()
