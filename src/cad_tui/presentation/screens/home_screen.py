"""Home: calendar and tasks side by side (calcurse-style 3-pane).

Left: month calendar. Right-top: tasks due on the selected calendar day.
Right-bottom: the full task list. Tab cycles focus between the three
panes; add/edit/delete/toggle act on whichever pane has focus.
"""

from __future__ import annotations

import calendar as calendar_mod
from datetime import date, timedelta

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Footer, ListView, Static

from cad_tui.domain.models import Status, Task
from cad_tui.domain.recurrence import RecurrenceRule
from cad_tui.presentation.screens.help import HelpModal
from cad_tui.presentation.screens.quick_add import QuickAddModal
from cad_tui.presentation.screens.task_form import TaskFormModal, TaskFormResult
from cad_tui.presentation.screens.task_list import TaskRow
from cad_tui.presentation.widgets.app_header import AppHeader
from cad_tui.presentation.widgets.calendar_grid import CalendarGrid, DayCell


class HomeScreen(Screen):
    BINDINGS = [
        Binding("left,h", "nav_left", "Left", show=False),
        Binding("right,l", "nav_right", "Right", show=False),
        Binding("up,k", "nav_up", "Up", show=False),
        Binding("down,j", "nav_down", "Down", show=False),
        Binding("[", "prev_month", "Prev month"),
        Binding("]", "next_month", "Next month"),
        Binding("t", "context_today_or_timer", "Today/Timer"),
        Binding("a", "add_task", "Add"),
        Binding("e", "edit_task", "Edit"),
        Binding("d", "delete_task", "Delete"),
        Binding("space", "toggle_complete", "Toggle done"),
        Binding("u", "undo", "Undo"),
        Binding("s", "add_subtask", "Subtask"),
        Binding("A", "quick_add", "Quick add"),
        Binding("w", "open_agenda", "Agenda"),
        Binding("S", "open_stats", "Stats"),
        Binding("P", "open_pomodoro", "Pomodoro"),
        Binding("question_mark", "show_help", "Help"),
    ]

    SMART_LIST_LABELS = {
        "today": "Today",
        "overdue": "Overdue",
        "week": "This week",
    }

    def __init__(self) -> None:
        super().__init__()
        self.smart_filter: str | None = None

    def compose(self) -> ComposeResult:
        yield AppHeader(subtitle="home")
        with Horizontal(id="home-body"):
            yield CalendarGrid(id="calendar")
            with Vertical(id="day-pane"):
                yield Static("", id="day-title", classes="accent-text")
                yield ListView(id="day-tasks")
                yield Static("All tasks", id="all-tasks-title", classes="accent-text")
                yield ListView(id="task-list")
        yield Footer()

    def on_mount(self) -> None:
        self.refresh_all()
        self.all_list.focus()

    # ---- widget accessors ----
    @property
    def calendar(self) -> CalendarGrid:
        return self.query_one("#calendar", CalendarGrid)

    @property
    def day_list(self) -> ListView:
        return self.query_one("#day-tasks", ListView)

    @property
    def all_list(self) -> ListView:
        return self.query_one("#task-list", ListView)

    # ---- focus / context ----
    def _in_day_context(self) -> bool:
        return self.focused is self.calendar or self.focused is self.day_list

    def _active_list(self) -> ListView:
        return self.day_list if self._in_day_context() else self.all_list

    def focus_calendar(self) -> None:
        self.calendar.focus()

    # ---- calendar day selection (mouse) ----
    def on_day_cell_selected(self, message: DayCell.Selected) -> None:
        self.calendar.focus_date = message.day
        self.refresh_all()
        self.calendar.focus()

    # ---- refresh ----
    def refresh_all(self) -> None:
        fd = self.calendar.focus_date
        self.calendar.counts = self._month_counts(fd.year, fd.month)
        self.calendar.render_month()
        self._refresh_day_tasks()
        self._refresh_all_tasks()
        self._update_header_meta()

    def _update_header_meta(self) -> None:
        if self.smart_filter:
            meta = self.SMART_LIST_LABELS[self.smart_filter]
        else:
            meta = self.calendar.focus_date.strftime("%B %Y")
        self.query_one(AppHeader).set_meta(meta)

    def _month_counts(self, year: int, month: int) -> dict[str, int]:
        counts: dict[str, int] = {}
        prefix = f"{year:04d}-{month:02d}"
        for task in self.app.task_service.list_tasks():
            if task.due_date and task.due_date.startswith(prefix):
                counts[task.due_date] = counts.get(task.due_date, 0) + 1
        return counts

    def _refresh_day_tasks(self, select_index: int | None = None) -> None:
        if select_index is None:
            select_index = self.day_list.index
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

    def _refresh_all_tasks(self, select_index: int | None = None) -> None:
        if select_index is None:
            select_index = self.all_list.index
        all_list = self.all_list
        all_list.clear()
        if self.smart_filter is None:
            rows = self.app.task_service.list_tasks_tree()
        else:
            rows = [(t, 0) for t in self._smart_list_tasks()]
        for task, depth in rows:
            all_list.append(TaskRow(task, depth=depth))
        if rows:
            index = 0 if select_index is None else max(0, min(select_index, len(rows) - 1))
            all_list.index = index

    def _smart_list_tasks(self) -> list[Task]:
        today_iso = date.today().isoformat()
        open_tasks = self.app.task_service.list_tasks(status=Status.OPEN)
        if self.smart_filter == "today":
            return [t for t in open_tasks if t.due_date == today_iso]
        if self.smart_filter == "overdue":
            return [t for t in open_tasks if t.due_date and t.due_date < today_iso]
        if self.smart_filter == "week":
            week_end = (date.today() + timedelta(days=7)).isoformat()
            return [t for t in open_tasks if t.due_date and today_iso <= t.due_date <= week_end]
        return open_tasks

    def set_smart_filter(self, filter_name: str | None) -> None:
        self.smart_filter = filter_name
        self._refresh_all_tasks()
        self._update_header_meta()

    def select_task_by_id(self, task_id: int) -> None:
        self.set_smart_filter(None)
        self.all_list.focus()
        for index, item in enumerate(self.all_list.children):
            if item.model.id == task_id:
                self.all_list.index = index
                return

    @property
    def selected_task(self) -> Task | None:
        child = self._active_list().highlighted_child
        return child.model if child is not None else None

    # ---- navigation ----
    def _move_calendar(self, delta_days: int) -> None:
        self.calendar.focus_date = self.calendar.focus_date + timedelta(days=delta_days)
        self.refresh_all()

    def action_nav_left(self) -> None:
        if self.focused is self.calendar:
            self._move_calendar(-1)

    def action_nav_right(self) -> None:
        if self.focused is self.calendar:
            self._move_calendar(1)

    def action_nav_up(self) -> None:
        if self.focused is self.calendar:
            self._move_calendar(-7)
        else:
            self._active_list().action_cursor_up()

    def action_nav_down(self) -> None:
        if self.focused is self.calendar:
            self._move_calendar(7)
        else:
            self._active_list().action_cursor_down()

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

    def action_context_today_or_timer(self) -> None:
        if self.focused is self.calendar:
            self.calendar.focus_date = date.today()
            self.refresh_all()
        else:
            self.action_toggle_timer()

    # ---- task actions (context-aware) ----
    def action_add_task(self) -> None:
        default_due = self.calendar.focus_date.isoformat() if self._in_day_context() else ""

        def on_result(result: TaskFormResult | None) -> None:
            if result is None:
                return
            task = Task(
                title=result.title,
                notes=result.notes,
                priority=result.priority,
                due_date=result.due_date,
                due_time=result.due_time,
                project_id=self._resolve_project(result.project_name),
                tag_ids=self.app.tag_repo.get_or_create_many(result.tag_names),
                recurrence_id=self._resolve_recurrence(result.recurrence, None),
            )
            created = self.app.task_service.add_task(task)
            self.app.task_service.set_blocked_by(
                created.id, self._resolve_blocker(result.blocked_by_title)
            )
            self.refresh_all()

        self.app.push_screen(TaskFormModal(default_due_date=default_due), on_result)

    def action_add_subtask(self) -> None:
        parent = self.selected_task
        if parent is None:
            return

        def on_result(result: TaskFormResult | None) -> None:
            if result is None:
                return
            task = Task(
                title=result.title,
                notes=result.notes,
                priority=result.priority,
                due_date=result.due_date,
                due_time=result.due_time,
                project_id=self._resolve_project(result.project_name),
                tag_ids=self.app.tag_repo.get_or_create_many(result.tag_names),
                recurrence_id=self._resolve_recurrence(result.recurrence, None),
                parent_task_id=parent.id,
            )
            created = self.app.task_service.add_task(task)
            self.app.task_service.set_blocked_by(
                created.id, self._resolve_blocker(result.blocked_by_title)
            )
            self.refresh_all()

        self.app.push_screen(TaskFormModal(parent_title=parent.title), on_result)

    def action_quick_add(self) -> None:
        def on_result(result) -> None:
            if result is None or not result.title:
                return
            task = Task(title=result.title, due_date=result.due_date, due_time=result.due_time)
            self.app.task_service.add_task(task)
            self.refresh_all()

        self.app.push_screen(QuickAddModal(), on_result)

    def action_edit_task(self) -> None:
        task = self.selected_task
        if task is None:
            return
        project = self.app.project_repo.get(task.project_id) if task.project_id else None
        tags = self.app.tag_repo.get_many(task.tag_ids)
        recurrence_rule = (
            self.app.recurrence_repo.get(task.recurrence_id) if task.recurrence_id else None
        )
        blocker_id = self.app.dependency_repo.get_blocker_id(task.id)
        blocker = self.app.task_repo.get(blocker_id) if blocker_id else None

        def on_result(result: TaskFormResult | None) -> None:
            if result is None:
                return
            self.app.task_service.update_task(
                task.id,
                title=result.title,
                notes=result.notes,
                priority=result.priority,
                due_date=result.due_date,
                due_time=result.due_time,
                project_id=self._resolve_project(result.project_name),
                tag_ids=self.app.tag_repo.get_or_create_many(result.tag_names),
                recurrence_id=self._resolve_recurrence(result.recurrence, task.recurrence_id),
            )
            self.app.task_service.set_blocked_by(
                task.id, self._resolve_blocker(result.blocked_by_title)
            )
            self.refresh_all()

        self.app.push_screen(
            TaskFormModal(
                task=task,
                project_name=project.name if project else "",
                tag_names=", ".join(t.name for t in tags),
                recurrence=recurrence_rule.rule if recurrence_rule else "",
                blocked_by_title=blocker.title if blocker else "",
            ),
            on_result,
        )

    def action_delete_task(self) -> None:
        task = self.selected_task
        if task is None:
            return
        self.app.task_service.delete_task(task.id)
        self.refresh_all()

    def action_toggle_complete(self) -> None:
        task = self.selected_task
        if task is None:
            return
        if task.status == Status.OPEN and self.app.task_service.is_blocked(task.id):
            blocker_id = self.app.dependency_repo.get_blocker_id(task.id)
            blocker = self.app.task_repo.get(blocker_id) if blocker_id else None
            self.notify(
                f"Blocked by: {blocker.title if blocker else 'another task'}", severity="warning"
            )
            return
        self.app.task_service.toggle_complete(task.id)
        self.refresh_all()

    def action_toggle_timer(self) -> None:
        task = self.selected_task
        if task is None:
            return
        running = self.app.time_tracking.toggle(task.id)
        self.refresh_all()
        self.notify(f"Timer {'started' if running else 'stopped'}: {task.title}")

    def action_undo(self) -> None:
        label = self.app.task_service.undo_last()
        self.refresh_all()
        if label:
            self.notify(f"Undid: {label}")

    def action_show_help(self) -> None:
        self.app.push_screen(HelpModal())

    def action_open_agenda(self) -> None:
        from cad_tui.presentation.screens.agenda_screen import AgendaScreen

        self.app.push_screen(AgendaScreen())

    def action_open_stats(self) -> None:
        from cad_tui.presentation.screens.stats_screen import StatsScreen

        self.app.push_screen(StatsScreen())

    def action_open_pomodoro(self) -> None:
        self.app.action_open_pomodoro()

    def _resolve_project(self, name: str | None) -> int | None:
        if not name:
            return None
        return self.app.project_repo.get_or_create(name)

    def _resolve_recurrence(self, rule: str, existing_id: int | None) -> int | None:
        if not rule:
            return None
        if existing_id is not None:
            existing = self.app.recurrence_repo.get(existing_id)
            if existing is not None and existing.rule == rule:
                return existing_id
        return self.app.recurrence_repo.create(RecurrenceRule(rule=rule))

    def _resolve_blocker(self, title: str | None) -> int | None:
        if not title:
            return None
        needle = title.strip().lower()
        for t in self.app.task_service.list_tasks():
            if t.title.lower() == needle:
                return t.id
        return None
