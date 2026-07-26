"""Domain entities. Plain dataclasses — no persistence logic here."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum


class Priority(IntEnum):
    HIGH = 1
    MEDIUM = 2
    LOW = 3


class Status:
    OPEN = "open"
    DONE = "done"


@dataclass
class Task:
    title: str
    id: int | None = None
    notes: str | None = None
    project_id: int | None = None
    priority: int = Priority.MEDIUM
    status: str = Status.OPEN
    due_date: str | None = None
    due_time: str | None = None
    estimate_min: int | None = None
    actual_min: int | None = None
    parent_task_id: int | None = None
    recurrence_id: int | None = None
    reschedule_count: int = 0
    created_at: str | None = None
    updated_at: str | None = None
    completed_at: str | None = None
    tag_ids: list[int] = field(default_factory=list)
    private: bool = False


@dataclass
class Project:
    name: str
    id: int | None = None
    color: str = "#8E8E93"
    archived: bool = False


@dataclass
class Tag:
    name: str
    id: int | None = None
    color: str = "#8E8E93"


@dataclass
class CalendarSource:
    """One configured read-only .ics feed (see AppConfig.ics_sources)."""

    name: str
    id: int | None = None
    color: str = "#0A84FF"
    source: str = "ics-import"


@dataclass
class Event:
    """A read-only calendar event synced in from an .ics source — never
    created or edited from within nokkam itself."""

    title: str
    start_at: str
    id: int | None = None
    end_at: str | None = None
    all_day: bool = False
    calendar_id: int | None = None
    location: str | None = None
    notes: str | None = None
    uid: str | None = None
