"""Fuzzy task search for Textual's built-in command palette (jump to a task)."""

from __future__ import annotations

import functools
from typing import TYPE_CHECKING

from textual.command import DiscoveryHit, Hit, Hits, Provider

if TYPE_CHECKING:
    from cad_tui.app import CadTuiApp


class TaskSearchProvider(Provider):
    app: CadTuiApp

    async def search(self, query: str) -> Hits:
        matcher = self.matcher(query)
        for task in self.app.task_service.list_tasks():
            if task.id is None:
                continue
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
            if task.id is None:
                continue
            yield DiscoveryHit(
                task.title,
                functools.partial(self.app.jump_to_task, task.id),
                help=task.due_date or None,
            )
