"""Generic Command-pattern undo stack. Each destructive TaskService call
pushes a closure that reverses it; undo() pops and runs the most recent one."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass
class _Command:
    label: str
    undo_fn: Callable[[], None]


class UndoStack:
    def __init__(self, max_size: int = 20) -> None:
        self._stack: list[_Command] = []
        self._max_size = max_size

    def push(self, label: str, undo_fn: Callable[[], None]) -> None:
        self._stack.append(_Command(label, undo_fn))
        if len(self._stack) > self._max_size:
            self._stack.pop(0)

    def undo(self) -> str | None:
        if not self._stack:
            return None
        command = self._stack.pop()
        command.undo_fn()
        return command.label

    def can_undo(self) -> bool:
        return bool(self._stack)
