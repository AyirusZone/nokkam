"""Calendar screen: month grid linked to the tasks due on the selected day."""

from __future__ import annotations

import calendar as calendar_mod
from datetime import date, timedelta

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Footer, Header, ListView, Static

from cad_tui.domain.models import Task
from cad_tui.presentation.screens.help import HelpModal
from cad_tui.presentation.screens.task_form import TaskFormModal, TaskFormResult
from cad_tui.presentation.screens.task_list import TaskRow
from cad_tui.presentation.widgets.calendar_grid import CalendarGrid


class CalendarScreen(Screen):
    BINDINGS = [
        Binding("left,h", "prev_day", "Prev day", show=False),
        Binding("right,l", "next_day", "Next day", show=False),
        Binding("up,k", "prev_week", "Prev week", show=False),
        Binding("down,j", "next_week", "Next week", show=False),
        Binding("[", "prev_month", "Prev month"),
        Binding("]", "next_month", "Next month"),
        Binding("t", "jump_today", "Today"),
        Binding("a", "add_task", "Add"),
        Binding("d", "delete_task", "Delete"),
        Binding("space", "toggle_complete", "Toggle done"),
        Binding("u", "undo", "Undo"),
        Binding("escape,backspace", "back", "Back to list"),
        Binding("question_mark", "show_help", "Help"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            yield CalendarGrid(id="calendar")
            with Vertical(id="day-pane"):
                yield Static("", id="day-title", classes="accent-text")
                yield ListView(id="day-tasks")
        yield Footer()

    def on_mount(self) -> None:
        self.refresh_all()

    @property
    def calendar(self) -> CalendarGrid:
        return self.query_one("#calendar", CalendarGrid)

    @property
    def day_list(self) -> ListView:
        return self.query_one("#day-tasks", ListView)

    def refresh_all(self) -> None:
        fd = self.calendar.focus_date
        self.calendar.counts = self._month_counts(fd.year, fd.month)
        self.calendar.render_month()
        self._refresh_day_tasks()

    def _month_counts(self, year: int, month: int) -> dict[str, int]:
        counts: dict[str, int] = {}
        prefix = f"{year:04d}-{month:02d}"
        for task in self.app.task_service.list_tasks():
            if task.due_date and task.due_date.startswith(prefix):
                counts[task.due_date] = counts.get(task.due_date, 0) + 1
        return counts

    def _refresh_day_tasks(self, select_index: int | None = None) -> None:
        fd = self.calendar.focus_date
        self.query_one("#day-title", Static).update(fd.strftime("%A, %d %B %Y"))
        day_list = self.day_list
        day_list.clear()
        tasks = [t for t in self.app.task_service.list_tasks() if t.due_date == fd.isoformat()]
        for task in tasks:
            day_list.append(TaskRow(task))
        if tasks:
            index = 0 if select_index is None else max(0, min(select_index, len(tasks) - 1))
            day_list.index = index

    def _move(self, delta_days: int) -> None:
        self.calendar.focus_date = self.calendar.focus_date + timedelta(days=delta_days)
        self.refresh_all()

    def action_prev_day(self) -> None:
        self._move(-1)

    def action_next_day(self) -> None:
        self._move(1)

    def action_prev_week(self) -> None:
        self._move(-7)

    def action_next_week(self) -> None:
        self._move(7)

    def action_prev_month(self) -> None:
        fd = self.calendar.focus_date
        prev_last_day = fd.replace(day=1) - timedelta(days=1)
        self.calendar.focus_date = prev_last_day.replace(day=min(fd.day, prev_last_day.day))
        self.refresh_all()

    def action_next_month(self) -> None:
        fd = self.calendar.focus_date
        days_in_month = calendar_mod.monthrange(fd.year, fd.month)[1]
        next_month_first = fd.replace(day=days_in_month) + timedelta(days=1)
        days_in_next = calendar_mod.monthrange(next_month_first.year, next_month_first.month)[1]
        self.calendar.focus_date = next_month_first.replace(day=min(fd.day, days_in_next))
        self.refresh_all()

    def action_jump_today(self) -> None:
        self.calendar.focus_date = date.today()
        self.refresh_all()

    def action_add_task(self) -> None:
        fd = self.calendar.focus_date

        def on_result(result: TaskFormResult | None) -> None:
            if result is None:
                return
            task = Task(
                title=result.title,
                notes=result.notes,
                priority=result.priority,
                due_date=result.due_date,
                due_time=result.due_time,
                project_id=(
                    self.app.project_repo.get_or_create(result.project_name)
                    if result.project_name
                    else None
                ),
                tag_ids=self.app.tag_repo.get_or_create_many(result.tag_names),
            )
            self.app.task_service.add_task(task)
            self.refresh_all()

        self.app.push_screen(TaskFormModal(default_due_date=fd.isoformat()), on_result)

    def action_delete_task(self) -> None:
        item = self.day_list.highlighted_child
        if item is None:
            return
        index = self.day_list.index
        self.app.task_service.delete_task(item.model.id)
        self._refresh_day_tasks(select_index=index)
        fd = self.calendar.focus_date
        self.calendar.counts = self._month_counts(fd.year, fd.month)
        self.calendar.render_month()

    def action_toggle_complete(self) -> None:
        item = self.day_list.highlighted_child
        if item is None:
            return
        index = self.day_list.index
        self.app.task_service.toggle_complete(item.model.id)
        self._refresh_day_tasks(select_index=index)

    def action_undo(self) -> None:
        label = self.app.task_service.undo_last()
        self.refresh_all()
        if label:
            self.notify(f"Undid: {label}")

    def action_back(self) -> None:
        self.app.pop_screen()

    def action_show_help(self) -> None:
        self.app.push_screen(HelpModal())
