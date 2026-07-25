"""Fuzzy task search for Textual's built-in command palette (jump to a task)."""

from __future__ import annotations

import functools

from textual.command import DiscoveryHit, Hit, Hits, Provider


class TaskSearchProvider(Provider):
    async def search(self, query: str) -> Hits:
        matcher = self.matcher(query)
        for task in self.app.task_service.list_tasks():
            score = matcher.match(task.title)
            if score > 0:
                yield Hit(
                    score,
                    matcher.highlight(task.title),
                    functools.partial(self.app.jump_to_task, task.id),
                    help=task.due_date or ("done" if task.status == "done" else None),
                )

    async def discover(self) -> Hits:
        for task in self.app.task_service.list_tasks()[:20]:
            yield DiscoveryHit(
                task.title,
                functools.partial(self.app.jump_to_task, task.id),
                help=task.due_date or None,
            )
