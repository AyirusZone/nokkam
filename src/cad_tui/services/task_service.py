"""Orchestrates TaskRepository mutations and records their inverse on the
undo stack. UI code should go through this, never the repository directly."""

from __future__ import annotations

from cad_tui.data.repositories.task_repository import TaskRepository
from cad_tui.domain.models import Status, Task
from cad_tui.services.undo import UndoStack


class TaskService:
    def __init__(self, repo: TaskRepository, undo_stack: UndoStack) -> None:
        self.repo = repo
        self.undo = undo_stack

    def list_tasks(self, **filters) -> list[Task]:
        return self.repo.list(**filters)

    def add_task(self, task: Task) -> Task:
        task_id = self.repo.create(task)
        self.undo.push(f"add '{task.title}'", lambda: self.repo.delete(task_id))
        return self.repo.get(task_id)

    def update_task(self, task_id: int, **fields) -> Task:
        previous = self.repo.get(task_id)
        self.repo.update(task_id, **fields)

        def _undo() -> None:
            restore = {k: getattr(previous, k) for k in fields}
            self.repo.update(task_id, **restore)

        self.undo.push(f"edit '{previous.title}'", _undo)
        return self.repo.get(task_id)

    def delete_task(self, task_id: int) -> None:
        task = self.repo.get(task_id)
        if task is None:
            return
        self.repo.delete(task_id)
        self.undo.push(f"delete '{task.title}'", lambda: self.repo.restore(task))

    def toggle_complete(self, task_id: int) -> Task:
        task = self.repo.get(task_id)
        if task is None:
            return None
        was_open = task.status == Status.OPEN
        if was_open:
            self.repo.mark_done(task_id)
        else:
            self.repo.mark_open(task_id)

        def _undo() -> None:
            if was_open:
                self.repo.mark_open(task_id)
            else:
                self.repo.mark_done(task_id)

        self.undo.push(f"toggle '{task.title}'", _undo)
        return self.repo.get(task_id)

    def undo_last(self) -> str | None:
        return self.undo.undo()
