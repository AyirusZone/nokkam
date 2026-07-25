"""Main screen: task list with add/edit/delete/toggle/undo and vim+arrow nav."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Header, ListItem, ListView, Static

from cad_tui.domain.models import Priority, Status, Task
from cad_tui.presentation.screens.help import HelpModal
from cad_tui.presentation.screens.task_form import TaskFormModal, TaskFormResult

PRIORITY_ICON = {Priority.HIGH: "●", Priority.MEDIUM: "◐", Priority.LOW: "○"}


class TaskRow(ListItem):
    def __init__(self, task: Task) -> None:
        super().__init__()
        self.model = task

    def compose(self) -> ComposeResult:
        done = self.model.status == Status.DONE
        check = "x" if done else " "
        icon = PRIORITY_ICON.get(self.model.priority, "◐")
        due = ""
        if self.model.due_date:
            due = f"  [dim]{self.model.due_date} {self.model.due_time or ''}[/]".rstrip()
        title = self.model.title
        if done:
            title = f"[dim strike]{title}[/]"
        yield Static(f"[{check}] {icon}  {title}{due}")


class TaskListScreen(Screen):
    BINDINGS = [
        Binding("a", "add_task", "Add"),
        Binding("e", "edit_task", "Edit"),
        Binding("d", "delete_task", "Delete"),
        Binding("space", "toggle_complete", "Toggle done"),
        Binding("u", "undo", "Undo"),
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
        Binding("question_mark", "show_help", "Help"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield ListView(id="task-list")
        yield Footer()

    def on_mount(self) -> None:
        self.refresh_tasks()

    @property
    def list_view(self) -> ListView:
        return self.query_one("#task-list", ListView)

    def refresh_tasks(self, select_index: int | None = None) -> None:
        list_view = self.list_view
        list_view.clear()
        tasks = self.app.task_service.list_tasks()
        for task in tasks:
            list_view.append(TaskRow(task))
        if tasks:
            index = 0 if select_index is None else max(0, min(select_index, len(tasks) - 1))
            list_view.index = index

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
            )
            self.app.task_service.add_task(task)
            self.refresh_tasks()

        self.app.push_screen(TaskFormModal(), on_result)

    def action_edit_task(self) -> None:
        task = self.selected_task
        if task is None:
            return
        index = self.list_view.index
        project = self.app.project_repo.get(task.project_id) if task.project_id else None
        tags = self.app.tag_repo.get_many(task.tag_ids)

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
            )
            self.refresh_tasks(select_index=index)

        self.app.push_screen(
            TaskFormModal(
                task=task,
                project_name=project.name if project else "",
                tag_names=", ".join(t.name for t in tags),
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

    def _resolve_project(self, name: str | None) -> int | None:
        if not name:
            return None
        return self.app.project_repo.get_or_create(name)
