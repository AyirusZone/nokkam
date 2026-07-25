"""A month calendar rendered as a 7-column grid of DayCell widgets."""

from __future__ import annotations

import calendar as calendar_mod
from datetime import date

from textual.app import ComposeResult
from textual.containers import Grid
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Static

WEEKDAY_LABELS = ["mo", "tu", "we", "th", "fr", "sa", "su"]


class DayCell(Static):
    class Selected(Message):
        def __init__(self, day: date) -> None:
            self.day = day
            super().__init__()

    def __init__(self, day: date, count: int, classes: str = "") -> None:
        super().__init__(classes=classes)
        self.day = day
        self.count = count

    def render(self) -> str:
        marker = "•" if self.count else " "
        return f"{self.day.day:>2}{marker}"

    def on_click(self) -> None:
        self.post_message(self.Selected(self.day))


class CalendarGrid(Widget):
    def __init__(self, id: str | None = None) -> None:
        super().__init__(id=id)
        self.focus_date: date = date.today()
        self.counts: dict[str, int] = {}

    def compose(self) -> ComposeResult:
        yield Grid(id="calendar-grid")

    def on_mount(self) -> None:
        self.render_month()

    def render_month(self) -> None:
        grid = self.query_one("#calendar-grid", Grid)
        grid.remove_children()
        grid.mount(*(Static(w, classes="weekday-label") for w in WEEKDAY_LABELS))

        cal = calendar_mod.Calendar(firstweekday=0)
        today = date.today()
        cells = []
        for d in cal.itermonthdates(self.focus_date.year, self.focus_date.month):
            classes = ["day-cell"]
            if d.month != self.focus_date.month:
                classes.append("other-month")
            if d == today:
                classes.append("today")
            if d == self.focus_date:
                classes.append("selected")
            count = self.counts.get(d.isoformat(), 0)
            cells.append(DayCell(d, count, classes=" ".join(classes)))
        grid.mount(*cells)
