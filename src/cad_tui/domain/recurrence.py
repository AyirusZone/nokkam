"""Recurrence math — pure functions, no persistence."""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, timedelta


@dataclass
class RecurrenceRule:
    rule: str  # daily | weekly | monthly
    interval: int = 1
    until: str | None = None  # ISO date, inclusive upper bound
    count: int | None = None  # max total occurrences


def next_occurrence(from_date: date, rule: RecurrenceRule) -> date | None:
    if rule.rule == "daily":
        nxt = from_date + timedelta(days=rule.interval)
    elif rule.rule == "weekly":
        nxt = from_date + timedelta(weeks=rule.interval)
    elif rule.rule == "monthly":
        nxt = _add_months(from_date, rule.interval)
    else:
        raise ValueError(f"Unknown recurrence rule: {rule.rule}")

    if rule.until is not None and nxt.isoformat() > rule.until:
        return None
    return nxt


def _add_months(d: date, months: int) -> date:
    month_index = d.month - 1 + months
    year = d.year + month_index // 12
    month = month_index % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)
