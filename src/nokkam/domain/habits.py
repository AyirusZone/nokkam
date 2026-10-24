"""Habit streaks over a recurring series — pure functions, no persistence.

A habit is every task sharing one recurrence. An occurrence counts toward the
streak only if it was completed on or before its due date; completing it late,
or letting an open occurrence go overdue, breaks the streak.
"""

from __future__ import annotations

from dataclasses import dataclass

ON_TIME = "on_time"
LATE = "late"
PENDING = "pending"
OVERDUE = "overdue"


@dataclass(frozen=True)
class Occurrence:
    due_date: str | None  # ISO date
    done: bool
    completed_on: str | None = None  # ISO date it was ticked off


def classify(occurrence: Occurrence, today: str) -> str:
    """on_time / late for a completed occurrence; pending / overdue for an open one."""
    if occurrence.done:
        due, completed = occurrence.due_date, occurrence.completed_on
        if due is None or completed is None or completed <= due:
            return ON_TIME
        return LATE
    if occurrence.due_date is not None and occurrence.due_date < today:
        return OVERDUE
    return PENDING


def compute_streaks(occurrences: list[Occurrence], today: str) -> tuple[int, int]:
    """(current, best) streak in occurrences, oldest to newest by due date.

    An open occurrence that isn't due yet neither counts nor breaks the run;
    one that is overdue breaks it."""
    run = best = 0
    for occurrence in sort_occurrences(occurrences):
        state = classify(occurrence, today)
        if state == ON_TIME:
            run += 1
            best = max(best, run)
        elif state in (LATE, OVERDUE):
            run = 0
    return run, best


def sort_occurrences(occurrences: list[Occurrence]) -> list[Occurrence]:
    return sorted(occurrences, key=lambda o: (o.due_date or "", o.completed_on or ""))
