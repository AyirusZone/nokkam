"""Filter query language for saved filters, e.g. ``project:Work tag:urgent due:week``.

Tokens are whitespace-separated (use quotes for values containing spaces):

  project:NAME    tag:NAME    priority:high|med|low
  due:today|tomorrow|overdue|week|none|YYYY-MM-DD
  status:open|done|all        (default: open)
  anything else               words that must all appear in the title

Repeating project/tag/priority ORs the values; different keys AND together.
"""

from __future__ import annotations

import shlex
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, timedelta

from nokkam.domain.models import Priority, Status, Task

_PRIORITY_ALIASES = {
    "high": Priority.HIGH,
    "h": Priority.HIGH,
    "1": Priority.HIGH,
    "med": Priority.MEDIUM,
    "medium": Priority.MEDIUM,
    "m": Priority.MEDIUM,
    "2": Priority.MEDIUM,
    "low": Priority.LOW,
    "l": Priority.LOW,
    "3": Priority.LOW,
}
_DUE_KEYWORDS = {"today", "tomorrow", "overdue", "week", "none"}
_STATUSES = {Status.OPEN, Status.DONE, "all"}
_KEYS = {"project", "tag", "priority", "due", "status"}


class QueryError(ValueError):
    """The filter text couldn't be understood; the message is user-facing."""


@dataclass(frozen=True)
class TaskQuery:
    projects: frozenset[str] = frozenset()
    tags: frozenset[str] = frozenset()
    priorities: frozenset[int] = frozenset()
    due: str | None = None
    status: str = Status.OPEN
    words: tuple[str, ...] = ()

    def matches(
        self,
        task: Task,
        *,
        project_name: str | None,
        tag_names: Iterable[str],
        today: date,
    ) -> bool:
        if self.status != "all" and task.status != self.status:
            return False
        if self.projects and (project_name or "").lower() not in self.projects:
            return False
        if self.tags and not self.tags & {n.lower() for n in tag_names}:
            return False
        if self.priorities and task.priority not in self.priorities:
            return False
        if self.due is not None and not self._due_matches(task, today):
            return False
        title = task.title.lower()
        return all(word in title for word in self.words)

    def _due_matches(self, task: Task, today: date) -> bool:
        due = task.due_date
        if self.due == "none":
            return due is None
        if due is None:
            return False
        if self.due == "today":
            return due == today.isoformat()
        if self.due == "tomorrow":
            return due == (today + timedelta(days=1)).isoformat()
        if self.due == "overdue":
            return due < today.isoformat() and task.status == Status.OPEN
        if self.due == "week":
            return today.isoformat() <= due <= (today + timedelta(days=7)).isoformat()
        return due == self.due


def parse_query(text: str) -> TaskQuery:
    try:
        tokens = shlex.split(text)
    except ValueError as exc:  # unbalanced quote
        raise QueryError(f"Unbalanced quote in filter: {exc}") from exc
    if not tokens:
        raise QueryError("Filter is empty")

    projects: set[str] = set()
    tags: set[str] = set()
    priorities: set[int] = set()
    due: str | None = None
    status: str = Status.OPEN
    words: list[str] = []

    for token in tokens:
        key, sep, value = token.partition(":")
        key = key.lower()
        if not sep:
            words.append(token.lower())
            continue
        if key not in _KEYS:
            raise QueryError(f"Unknown filter '{key}:' (use {', '.join(sorted(_KEYS))})")
        value = value.strip()
        if not value:
            raise QueryError(f"'{key}:' needs a value")
        if key == "project":
            projects.add(value.lower())
        elif key == "tag":
            tags.add(value.lower())
        elif key == "priority":
            priority = _PRIORITY_ALIASES.get(value.lower())
            if priority is None:
                raise QueryError(f"Unknown priority '{value}' (use high, med or low)")
            priorities.add(priority)
        elif key == "due":
            due = _parse_due(value)
        else:
            status = value.lower()
            if status not in _STATUSES:
                raise QueryError(f"Unknown status '{value}' (use open, done or all)")

    return TaskQuery(
        projects=frozenset(projects),
        tags=frozenset(tags),
        priorities=frozenset(priorities),
        due=due,
        status=status,
        words=tuple(words),
    )


def _parse_due(value: str) -> str:
    lowered = value.lower()
    if lowered in _DUE_KEYWORDS:
        return lowered
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError:
        raise QueryError(
            f"Unknown due '{value}' (use today, tomorrow, overdue, week, none or YYYY-MM-DD)"
        ) from None
