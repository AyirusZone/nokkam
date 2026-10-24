"""Turns recurring task series into habit rows (streaks, history) for the UI."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from nokkam.data.repositories.project_repository import ProjectRepository
from nokkam.data.repositories.recurrence_repository import RecurrenceRepository
from nokkam.domain.habits import (
    ON_TIME,
    Occurrence,
    classify,
    compute_streaks,
    sort_occurrences,
)
from nokkam.domain.models import Status, Task
from nokkam.domain.recurrence import format_recurrence
from nokkam.services.task_service import TaskService

HISTORY_LENGTH = 10


@dataclass
class Habit:
    recurrence_id: int
    title: str
    project_name: str | None
    rule_text: str
    current_streak: int
    best_streak: int
    done: int
    on_time: int
    total: int
    active: bool  # has an open occurrence left; False once the series has ended
    history: list[str] = field(default_factory=list)  # last HISTORY_LENGTH states, oldest first

    @property
    def on_time_rate(self) -> float:
        return self.on_time / self.done if self.done else 0.0


def compute_habits(
    task_service: TaskService,
    recurrence_repo: RecurrenceRepository,
    project_repo: ProjectRepository,
    today: date | None = None,
) -> list[Habit]:
    """One row per recurring series: active ones first, best current streak first."""
    today_iso = (today or date.today()).isoformat()
    series: dict[int, list[Task]] = {}
    for task in task_service.list_tasks():
        if task.recurrence_id is not None:
            series.setdefault(task.recurrence_id, []).append(task)

    project_names = {p.id: p.name for p in project_repo.list()}
    habits: list[Habit] = []
    for recurrence_id, tasks in series.items():
        rule = recurrence_repo.get(recurrence_id)
        if rule is None:
            continue
        occurrences = [
            Occurrence(
                due_date=t.due_date,
                done=t.status == Status.DONE,
                completed_on=t.completed_at[:10] if t.completed_at else None,
            )
            for t in tasks
        ]
        current, best = compute_streaks(occurrences, today_iso)
        ordered = sort_occurrences(occurrences)
        states = [classify(o, today_iso) for o in ordered]
        latest = max(tasks, key=lambda t: (t.due_date or "", t.id or 0))
        done = sum(1 for o in occurrences if o.done)
        habits.append(
            Habit(
                recurrence_id=recurrence_id,
                title=latest.title,
                project_name=project_names.get(latest.project_id),
                rule_text=format_recurrence(rule),
                current_streak=current,
                best_streak=best,
                done=done,
                on_time=sum(
                    1 for s, o in zip(states, ordered, strict=True) if o.done and s == ON_TIME
                ),
                total=len(occurrences),
                active=any(not o.done for o in occurrences),
                history=states[-HISTORY_LENGTH:],
            )
        )
    habits.sort(key=lambda h: (not h.active, -h.current_streak, h.title.lower()))
    return habits
