"""Rolling agenda: open tasks due within the next 14 days, chronological."""

from __future__ import annotations

from datetime import date, timedelta

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Header, ListView, Static

from cad_tui.domain.models import Status
from cad_tui.presentation.screens.help import HelpModal
from cad_tui.presentation.screens.task_list import TaskRow

AGENDA_DAYS = 14


class AgendaScreen(Screen):
    BINDINGS = [
        Binding("space", "toggle_complete", "Toggle done"),
        Binding("d", "delete_task", "Delete"),
        Binding("u", "undo", "Undo"),
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
        Binding("escape,backspace", "back", "Back"),
        Binding("question_mark", "show_help", "Help"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(f"Agenda — next {AGENDA_DAYS} days", classes="accent-text", id="agenda-title")
        yield ListView(id="agenda-list")
        yield Footer()

    def on_mount(self) -> None:
        self.refresh_agenda()

    @property
    def list_view(self) -> ListView:
        return self.query_one("#agenda-list", ListView)

    def refresh_agenda(self, select_index: int | None = None) -> None:
        list_view = self.list_view
        list_view.clear()
        today_iso = date.today().isoformat()
        horizon_iso = (date.today() + timedelta(days=AGENDA_DAYS)).isoformat()
        tasks = [
            t
            for t in self.app.task_service.list_tasks(status=Status.OPEN)
            if t.due_date and today_iso <= t.due_date <= horizon_iso
        ]
        tasks.sort(key=lambda t: (t.due_date, t.due_time or "", t.priority))
        for task in tasks:
            list_view.append(TaskRow(task))
        if tasks:
            index = 0 if select_index is None else max(0, min(select_index, len(tasks) - 1))
            list_view.index = index

    @property
    def selected_task(self):
        child = self.list_view.highlighted_child
        return child.model if child is not None else None

    def action_cursor_down(self) -> None:
        self.list_view.action_cursor_down()

    def action_cursor_up(self) -> None:
        self.list_view.action_cursor_up()

    def action_toggle_complete(self) -> None:
        task = self.selected_task
        if task is None:
            return
        index = self.list_view.index
        self.app.task_service.toggle_complete(task.id)
        self.refresh_agenda(select_index=index)

    def action_delete_task(self) -> None:
        task = self.selected_task
        if task is None:
            return
        index = self.list_view.index
        self.app.task_service.delete_task(task.id)
        self.refresh_agenda(select_index=index)

    def action_undo(self) -> None:
        label = self.app.task_service.undo_last()
        self.refresh_agenda()
        if label:
            self.notify(f"Undid: {label}")

    def action_back(self) -> None:
        self.app.pop_screen()

    def action_show_help(self) -> None:
        self.app.push_screen(HelpModal())
