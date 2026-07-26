"""Fuzzy task search for Textual's built-in command palette (jump to a task)."""

from __future__ import annotations

import functools
from typing import TYPE_CHECKING

from textual.command import DiscoveryHit, Hit, Hits, Provider

if TYPE_CHECKING:
    from nokkam.app import NokkamApp


class TaskSearchProvider(Provider):
    app: NokkamApp

    async def search(self, query: str) -> Hits:
        matcher = self.matcher(query)
        for task in self.app.task_service.list_tasks():
            if task.id is None:
                continue
            # Still searchable by real title (you know what you're looking
            # for) — just never displayed, same as everywhere else private
            # tasks show up.
            score = matcher.match(task.title)
            if score > 0:
                label = "•••••" if task.private else matcher.highlight(task.title)
                yield Hit(
                    score,
                    label,
                    functools.partial(self.app.jump_to_task, task.id),
                    help=task.due_date or ("done" if task.status == "done" else None),
                )

    async def discover(self) -> Hits:
        for task in self.app.task_service.list_tasks()[:20]:
            if task.id is None:
                continue
            label = "•••••" if task.private else task.title
            yield DiscoveryHit(
                label,
                functools.partial(self.app.jump_to_task, task.id),
                help=task.due_date or None,
            )
