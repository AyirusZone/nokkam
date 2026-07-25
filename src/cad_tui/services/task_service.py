"""Orchestrates TaskRepository mutations and records their inverse on the
undo stack. UI code should go through this, never the repository directly."""

from __future__ import annotations

from datetime import date

from cad_tui.data.repositories.recurrence_repository import RecurrenceRepository
from cad_tui.data.repositories.task_repository import TaskRepository
from cad_tui.domain.models import Status, Task
from cad_tui.domain.recurrence import next_occurrence
from cad_tui.services.undo import UndoStack


class TaskService:
    def __init__(
        self,
        repo: TaskRepository,
        undo_stack: UndoStack,
        recurrence_repo: RecurrenceRepository | None = None,
    ) -> None:
        self.repo = repo
        self.undo = undo_stack
        self.recurrence_repo = recurrence_repo

    def list_tasks(self, **filters) -> list[Task]:
        return self.repo.list(**filters)

    def list_tasks_tree(self, **filters) -> list[tuple[Task, int]]:
        """Flat list ordered so each task is immediately followed by its
        subtasks, paired with an indent depth."""
        tasks = self.repo.list(**filters)
        by_parent: dict[int | None, list[Task]] = {}
        for t in tasks:
            by_parent.setdefault(t.parent_task_id, []).append(t)

        ordered: list[tuple[Task, int]] = []

        def walk(parent_id: int | None, depth: int) -> None:
            for t in by_parent.get(parent_id, []):
                ordered.append((t, depth))
                walk(t.id, depth + 1)

        walk(None, 0)

        # A subtask whose parent got excluded by a filter would otherwise be
        # dropped entirely — surface it at depth 0 instead of losing it.
        seen_ids = {t.id for t, _ in ordered}
        for t in tasks:
            if t.id not in seen_ids:
                ordered.append((t, 0))
        return ordered

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
        spawned_id: int | None = None
        if was_open:
            self.repo.mark_done(task_id)
            spawned_id = self._maybe_spawn_next_occurrence(task)
        else:
            self.repo.mark_open(task_id)

        def _undo() -> None:
            if was_open:
                self.repo.mark_open(task_id)
                if spawned_id is not None:
                    self.repo.delete(spawned_id)
            else:
                self.repo.mark_done(task_id)

        self.undo.push(f"toggle '{task.title}'", _undo)
        return self.repo.get(task_id)

    def _maybe_spawn_next_occurrence(self, completed_task: Task) -> int | None:
        if completed_task.recurrence_id is None or self.recurrence_repo is None:
            return None
        rule = self.recurrence_repo.get(completed_task.recurrence_id)
        if rule is None:
            return None
        if rule.count is not None:
            existing = self.repo.count_by_recurrence(completed_task.recurrence_id)
            if existing >= rule.count:
                return None

        base_date = (
            date.fromisoformat(completed_task.due_date)
            if completed_task.due_date
            else date.today()
        )
        nxt = next_occurrence(base_date, rule)
        if nxt is None:
            return None

        next_task = Task(
            title=completed_task.title,
            notes=completed_task.notes,
            project_id=completed_task.project_id,
            priority=completed_task.priority,
            due_date=nxt.isoformat(),
            due_time=completed_task.due_time,
            recurrence_id=completed_task.recurrence_id,
            tag_ids=list(completed_task.tag_ids),
        )
        return self.repo.create(next_task)

    def undo_last(self) -> str | None:
        return self.undo.undo()
