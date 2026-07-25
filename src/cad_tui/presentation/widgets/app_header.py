"""Minimal header: wordmark + view name, nothing else. No clock, no boxed
chrome — Textual's stock Header reads as generic; this reads as considered."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Static

WORDMARK = "cad"


class AppHeader(Horizontal):
    def __init__(self, subtitle: str = "", meta: str = "") -> None:
        super().__init__()
        self._subtitle = subtitle
        self._meta = meta

    def compose(self) -> ComposeResult:
        yield Static(self._render_left(), id="app-header-title")
        yield Static(self._meta, id="app-header-meta")

    @property
    def meta(self) -> str:
        return self._meta

    @property
    def subtitle(self) -> str:
        return self._subtitle

    def _render_left(self) -> str:
        sep = "  [dim]/[/]  " if self._subtitle else ""
        return f"[bold $accent]{WORDMARK}[/]{sep}[dim]{self._subtitle}[/]"

    def set_subtitle(self, subtitle: str) -> None:
        self._subtitle = subtitle
        if self.is_mounted:
            self.query_one("#app-header-title", Static).update(self._render_left())

    def set_meta(self, meta: str) -> None:
        self._meta = meta
        if self.is_mounted:
            self.query_one("#app-header-meta", Static).update(meta)
