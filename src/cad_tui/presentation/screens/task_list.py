"""Main screen: task list with add/edit/delete/toggle/undo and vim+arrow nav."""

from __future__ import annotations

from datetime import date, timedelta

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, ListItem, ListView, Static

from cad_tui.domain.models import Priority, Status, Task
from cad_tui.domain.recurrence import RecurrenceRule
from cad_tui.presentation.screens.help import HelpModal
from cad_tui.presentation.screens.quick_add import QuickAddModal
from cad_tui.presentation.screens.task_form import TaskFormModal, TaskFormResult
from cad_tui.presentation.widgets.app_header import AppHeader

PRIORITY_CLASS = {
    Priority.HIGH: "priority-high",
    Priority.MEDIUM: "priority-medium",
    Priority.LOW: "priority-low",
}


class TaskRow(ListItem):
    def __init__(self, task: Task, depth: int = 0) -> None:
        super().__init__(classes=PRIORITY_CLASS.get(task.priority, "priority-medium"))
        self.model = task
        self.depth = depth

    def compose(self) -> ComposeResult:
        done = self.model.status == Status.DONE
        indent = "  " * self.depth
        check = "[$success]✓[/] " if done else "  "
        recurring = " [$secondary]↻[/]" if self.model.recurrence_id else ""
        timing = " [$accent]⏱[/]" if self.app.time_tracking.active_task_id == self.model.id else ""
        blocked = (
            " [$warning]⛔[/]"
            if not done and self.app.task_service.is_blocked(self.model.id)
            else ""
        )
        due = ""
        if self.model.due_date:
            due = f"   [dim]{self.model.due_date} {self.model.due_time or ''}[/]".rstrip()
        title = self.model.title
        if done:
            title = f"[dim strike]{title}[/]"
        yield Static(f"{indent}{check}{title}{recurring}{timing}{blocked}{due}")


class TaskListScreen(Screen):
    BINDINGS = [
        Binding("a", "add_task", "Add"),
        Binding("e", "edit_task", "Edit"),
        Binding("d", "delete_task", "Delete"),
        Binding("space", "toggle_complete", "Toggle done"),
        Binding("u", "undo", "Undo"),
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
        Binding("c", "open_calendar", "Calendar"),
        Binding("s", "add_subtask", "Subtask"),
        Binding("A", "quick_add", "Quick add"),
        Binding("w", "open_agenda", "Agenda"),
        Binding("S", "open_stats", "Stats"),
        Binding("t", "toggle_timer", "Timer"),
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
        yield AppHeader(subtitle="tasks")
        yield ListView(id="task-list")
        yield Footer()

    def on_mount(self) -> None:
        self.refresh_tasks()

    @property
    def list_view(self) -> ListView:
        return self.query_one("#task-list", ListView)

    def set_smart_filter(self, filter_name: str | None) -> None:
        self.smart_filter = filter_name
        self.refresh_tasks()

    def refresh_tasks(self, select_index: int | None = None) -> None:
        list_view = self.list_view
        list_view.clear()
        if self.smart_filter is None:
            rows = self.app.task_service.list_tasks_tree()
        else:
            rows = [(t, 0) for t in self._smart_list_tasks()]
        for task, depth in rows:
            list_view.append(TaskRow(task, depth=depth))
        if rows:
            index = 0 if select_index is None else max(0, min(select_index, len(rows) - 1))
            list_view.index = index

        open_count = len(self.app.task_service.list_tasks(status=Status.OPEN))
        meta = self.SMART_LIST_LABELS.get(self.smart_filter, f"{open_count} open")
        self.query_one(AppHeader).set_meta(meta)

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

    def select_task_by_id(self, task_id: int) -> None:
        self.set_smart_filter(None)
        for index, item in enumerate(self.list_view.children):
            if item.model.id == task_id:
                self.list_view.index = index
                return

    @property
    def selected_task(self) -> Task | None:
        child = self.list_view.highlighted_child
        return child.model if child is not None else None

    def action_cursor_down(self) -> None:
        self.list_view.action_cursor_down()

    def action_cursor_up(self) -> None:
        self.list_view.action_cursor_up()

    def action_add_task(self) -> None:
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
            self.refresh_tasks()

        self.app.push_screen(TaskFormModal(), on_result)

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
            self.refresh_tasks()

        self.app.push_screen(TaskFormModal(parent_title=parent.title), on_result)

    def action_quick_add(self) -> None:
        def on_result(result) -> None:
            if result is None or not result.title:
                return
            task = Task(title=result.title, due_date=result.due_date, due_time=result.due_time)
            self.app.task_service.add_task(task)
            self.refresh_tasks()

        self.app.push_screen(QuickAddModal(), on_result)

    def action_edit_task(self) -> None:
        task = self.selected_task
        if task is None:
            return
        index = self.list_view.index
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
            self.refresh_tasks(select_index=index)

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
        index = self.list_view.index
        self.app.task_service.delete_task(task.id)
        self.refresh_tasks(select_index=index)

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
        index = self.list_view.index
        self.app.task_service.toggle_complete(task.id)
        self.refresh_tasks(select_index=index)

    def action_undo(self) -> None:
        label = self.app.task_service.undo_last()
        self.refresh_tasks()
        if label:
            self.notify(f"Undid: {label}")

    def action_show_help(self) -> None:
        self.app.push_screen(HelpModal())

    def action_open_calendar(self) -> None:
        from cad_tui.presentation.screens.calendar_screen import CalendarScreen

        self.app.push_screen(CalendarScreen())

    def action_open_agenda(self) -> None:
        from cad_tui.presentation.screens.agenda_screen import AgendaScreen

        self.app.push_screen(AgendaScreen())

    def action_open_stats(self) -> None:
        from cad_tui.presentation.screens.stats_screen import StatsScreen

        self.app.push_screen(StatsScreen())

    def action_toggle_timer(self) -> None:
        task = self.selected_task
        if task is None:
            return
        index = self.list_view.index
        running = self.app.time_tracking.toggle(task.id)
        self.refresh_tasks(select_index=index)
        self.notify(f"Timer {'started' if running else 'stopped'}: {task.title}")

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
