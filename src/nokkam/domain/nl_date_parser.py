"""Lightweight rule-based parser for quick-add text like
"Buy milk tmrw 3pm" or "Standup fri 9:30". No NLP dependency —
just regexes over a small vocabulary, per the build constraint of
keeping this dependency-free.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, timedelta

from nokkam.domain.recurrence import (
    ORDINALS,
    WEEKDAY_ALIASES,
    RecurrenceError,
    RecurrenceRule,
    first_occurrence,
    parse_recurrence,
)

_RELATIVE_DAYS = {"today": 0, "tomorrow": 1, "tmrw": 1, "tmw": 1}
_WEEKDAYS = WEEKDAY_ALIASES

_DAY_NAMES = "|".join(sorted(WEEKDAY_ALIASES, key=len, reverse=True))
_DAY_LIST = rf"(?:{_DAY_NAMES})(?:(?:\s*,\s*|\s+and\s+)(?:{_DAY_NAMES}))*"
# "every day", "every 2 weeks on mon,thu", "every weekday", "every fri",
# "every first tue", optionally followed by "until <date>" / "for N times".
_RECURRENCE_RE = re.compile(
    r"\bevery\s+(?:"
    rf"(?:other\s+|\d+\s+)?(?:days?|weeks?|months?|years?|weekdays?|weekends?)"
    rf"(?:\s+on\s+{_DAY_LIST})?"
    rf"|(?:{'|'.join(ORDINALS)})\s+(?:{_DAY_NAMES})(?:\s+of\s+(?:the|every)\s+month)?"
    rf"|{_DAY_LIST}"
    r")(?:\s+until\s+\d{4}-\d{2}-\d{2})?(?:\s+for\s+\d+\s+times?)?\b",
    re.IGNORECASE,
)
_ISO_DATE_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
_IN_N_RE = re.compile(r"\bin\s+(\d+)\s+(day|days|week|weeks)\b", re.IGNORECASE)
_RELATIVE_RE = re.compile(r"\b(" + "|".join(_RELATIVE_DAYS) + r")\b", re.IGNORECASE)
_WEEKDAY_RE = re.compile(
    r"\b(" + "|".join(sorted(_WEEKDAYS, key=len, reverse=True)) + r")\b", re.IGNORECASE
)
_TIME_AMPM_RE = re.compile(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b", re.IGNORECASE)
_TIME_24H_RE = re.compile(r"\b([01]?\d|2[0-3]):([0-5]\d)\b")


@dataclass
class QuickAddResult:
    title: str
    due_date: str | None
    due_time: str | None
    recurrence: RecurrenceRule | None = None


def parse_quick_text(text: str, *, today: date | None = None) -> QuickAddResult:
    today = today or date.today()
    remaining = text

    def _cut(match: re.Match) -> None:
        nonlocal remaining
        remaining = remaining[: match.start()] + remaining[match.end() :]

    recurrence: RecurrenceRule | None = None
    if match := _RECURRENCE_RE.search(remaining):
        try:
            recurrence = parse_recurrence(match.group(0))
        except RecurrenceError:
            recurrence = None
        else:
            _cut(match)

    due_date: str | None = None
    if match := _ISO_DATE_RE.search(remaining):
        due_date = match.group(1)
        _cut(match)
    elif match := _IN_N_RE.search(remaining):
        n = int(match.group(1))
        days = n * 7 if match.group(2).lower().startswith("week") else n
        due_date = (today + timedelta(days=days)).isoformat()
        _cut(match)
    elif match := _RELATIVE_RE.search(remaining):
        offset = _RELATIVE_DAYS[match.group(1).lower()]
        due_date = (today + timedelta(days=offset)).isoformat()
        _cut(match)
    elif match := _WEEKDAY_RE.search(remaining):
        target = _WEEKDAYS[match.group(1).lower()]
        delta = (target - today.weekday()) % 7
        due_date = (today + timedelta(days=delta)).isoformat()
        _cut(match)

    due_time: str | None = None
    if match := _TIME_AMPM_RE.search(remaining):
        hour = int(match.group(1)) % 12
        minute = int(match.group(2) or 0)
        if match.group(3).lower() == "pm":
            hour += 12
        due_time = f"{hour:02d}:{minute:02d}"
        _cut(match)
    elif match := _TIME_24H_RE.search(remaining):
        due_time = f"{int(match.group(1)):02d}:{match.group(2)}"
        _cut(match)

    # "Standup every weekday": no explicit date, so start at the first day the
    # pattern actually fits rather than leaving the task undated.
    if recurrence is not None and due_date is None:
        due_date = first_occurrence(recurrence, today).isoformat()

    title = re.sub(r"\s+", " ", remaining).strip()
    return QuickAddResult(title=title, due_date=due_date, due_time=due_time, recurrence=recurrence)
