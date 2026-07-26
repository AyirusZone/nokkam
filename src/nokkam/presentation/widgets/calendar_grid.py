"""A full-width month calendar: weekday columns, each day cell previewing
the tasks due that day (title, priority-colored marker, done state).

Built from nested Horizontal/Vertical containers rather than Textual's
Grid layout — Grid's row-height resolution doesn't stretch children to
fill an explicit `grid-rows` track reliably, which silently clipped
multi-line day-cell content. Plain flex containers size predictably."""

from __future__ import annotations

import calendar as calendar_mod
from datetime import date

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.widgets import Static

from nokkam.domain.icons import icon_for_title
from nokkam.domain.models import Event, Status, Task

WEEKDAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
WEEKEND_INDICES = {5, 6}
# Tasks and synced .ics events share this line budget (tasks shown first) —
# the cell is a fixed 4 lines tall (1 for the day number), so this is what
# actually fits, not an arbitrary content cap.
MAX_PREVIEW_ITEMS = 2


class DayCell(Static):
    class Selected(Message):
        def __init__(self, day: date) -> None:
            self.day = day
            super().__init__()

    def __init__(
        self,
        day: date,
        tasks: list[Task],
        project_colors: dict[int, str],
        icon_overrides: dict[str, str],
        events: list[Event] | None = None,
        classes: str = "",
    ) -> None:
        super().__init__(classes=classes)
        self.day = day
        self.tasks = tasks
        self.project_colors = project_colors
        self.icon_overrides = icon_overrides
        self.events = events or []

    def render(self) -> str:
        # Each line relies on the `.day-cell` CSS (text-wrap: nowrap;
        # text-overflow: ellipsis) to truncate long titles at the cell's
        # actual rendered width — folding onto extra lines here would push
        # later items out of the cell's fixed height instead of just
        # clipping.
        lines = [f"[b]{self.day.day:>2}[/b]"]
        item_lines = [self._task_line(t) for t in self.tasks] + [
            self._event_line(e) for e in self.events
        ]
        shown = item_lines[:MAX_PREVIEW_ITEMS]
        lines.extend(shown)
        remaining = len(item_lines) - len(shown)
        if remaining > 0:
            lines.append(f"[dim]+{remaining} more[/]")
        return "\n".join(lines)

    def _task_line(self, task: Task) -> str:
        done = task.status == Status.DONE
        dot_color = "$accent"
        if task.project_id is not None:
            dot_color = self.project_colors.get(task.project_id, "$accent")
        mark = "[$success]✓[/]" if done else f"[{dot_color}]•[/]"
        if task.private:
            shown_title = "•••••"
        else:
            icon = icon_for_title(task.title, self.icon_overrides)
            icon_part = f"{icon} " if icon else ""
            shown_title = f"{icon_part}{task.title}"
        title_markup = f"[dim strike]{shown_title}[/]" if done else shown_title
        return f"{mark} {title_markup}"

    def _event_line(self, event: Event) -> str:
        # A distinct marker/color from tasks' "•" so a synced .ics event
        # (read-only, not yours to edit) reads as a different kind of
        # thing at a glance, not just another task.
        return f"[$secondary]▸[/] {event.title}"

    def on_click(self) -> None:
        self.post_message(self.Selected(self.day))


class CalendarGrid(Vertical, can_focus=True):
    def __init__(self, id: str | None = None) -> None:
        super().__init__(id=id)
        self.focus_date: date = date.today()
        self.tasks_by_date: dict[str, list[Task]] = {}
        self.events_by_date: dict[str, list[Event]] = {}
        self.project_colors: dict[int, str] = {}
        self.icon_overrides: dict[str, str] = {}

    def compose(self) -> ComposeResult:
        with Horizontal(classes="calendar-header-row"):
            for i, label in enumerate(WEEKDAY_LABELS):
                yield Static(
                    label, classes="weekday-label" + (" weekend" if i in WEEKEND_INDICES else "")
                )
        yield Vertical(id="calendar-weeks")

    def on_mount(self) -> None:
        self.render_month()

    def render_month(self) -> None:
        weeks = self.query_one("#calendar-weeks", Vertical)
        weeks.remove_children()

        cal = calendar_mod.Calendar(firstweekday=0)
        today = date.today()
        month_dates = list(cal.itermonthdates(self.focus_date.year, self.focus_date.month))
        week_rows = [month_dates[i : i + 7] for i in range(0, len(month_dates), 7)]

        for week in week_rows:
            row = Horizontal(classes="calendar-week-row")
            weeks.mount(row)
            cells = []
            for d in week:
                classes = ["day-cell"]
                if d.weekday() in WEEKEND_INDICES:
                    classes.append("weekend")
                if d.month != self.focus_date.month:
                    classes.append("other-month")
                if d == today:
                    classes.append("today")
                if d == self.focus_date:
                    classes.append("selected")
                tasks = self.tasks_by_date.get(d.isoformat(), [])
                events = self.events_by_date.get(d.isoformat(), [])
                cells.append(
                    DayCell(
                        d,
                        tasks,
                        self.project_colors,
                        self.icon_overrides,
                        events=events,
                        classes=" ".join(classes),
                    )
                )
            row.mount(*cells)
