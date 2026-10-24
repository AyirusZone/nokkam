"""Recurrence math and text parsing — pure functions, no persistence.

Rule kinds: daily | weekly | monthly | monthly_nth | yearly.
  - weekly with `weekdays` repeats on those days ("every mon,wed,fri");
    without, it repeats every 7*interval days from the due date.
  - monthly_nth is "the nth weekday of the month" ("every first tue",
    "every last fri"); `weekdays` holds that one day, `nth` is 1-4 or -1 (last).
Text form (see parse_recurrence / format_recurrence): "every 2 weeks on
mon,thu until 2026-12-31 for 10 times".
"""

from __future__ import annotations

import calendar
import re
from dataclasses import dataclass
from datetime import date, timedelta

WEEKDAY_ALIASES = {
    "monday": 0,
    "mon": 0,
    "tuesday": 1,
    "tues": 1,
    "tue": 1,
    "wednesday": 2,
    "weds": 2,
    "wed": 2,
    "thursday": 3,
    "thurs": 3,
    "thur": 3,
    "thu": 3,
    "friday": 4,
    "fri": 4,
    "saturday": 5,
    "sat": 5,
    "sunday": 6,
    "sun": 6,
}
WEEKDAY_SHORT = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
ORDINALS = {
    "first": 1,
    "1st": 1,
    "second": 2,
    "2nd": 2,
    "third": 3,
    "3rd": 3,
    "fourth": 4,
    "4th": 4,
    "last": -1,
}
ORDINAL_NAMES = {1: "first", 2: "second", 3: "third", 4: "fourth", -1: "last"}
_WEEKDAYS_MON_FRI = (0, 1, 2, 3, 4)
_WEEKEND = (5, 6)
_UNITS = {
    "day": "daily",
    "days": "daily",
    "daily": "daily",
    "week": "weekly",
    "weeks": "weekly",
    "weekly": "weekly",
    "month": "monthly",
    "months": "monthly",
    "monthly": "monthly",
    "year": "yearly",
    "years": "yearly",
    "yearly": "yearly",
    "annually": "yearly",
}
# One-word spellings people type: "everyday" -> "every day".
_GLUED = {
    "everyday": ["every", "day"],
    "everyweek": ["every", "week"],
    "everymonth": ["every", "month"],
    "everyyear": ["every", "year"],
    "everyweekday": ["every", "weekday"],
    "everyweekdays": ["every", "weekdays"],
    "everyweekend": ["every", "weekend"],
    "everyweekends": ["every", "weekends"],
}
_ADVERBS = {"daily", "weekly", "monthly", "yearly", "annually"}
_NO_RECURRENCE = {"", "none", "never", "no", "off"}
_EXAMPLES = (
    "try: every day, every 2 weeks, every weekday, every mon,wed,fri, "
    "every first tue, every month until 2026-12-31, every day for 10 times"
)


class RecurrenceError(ValueError):
    """The recurrence text couldn't be understood; the message is user-facing."""


@dataclass
class RecurrenceRule:
    rule: str  # daily | weekly | monthly | monthly_nth | yearly
    interval: int = 1
    until: str | None = None  # ISO date, inclusive upper bound
    count: int | None = None  # max total occurrences
    weekdays: tuple[int, ...] = ()  # 0=Mon; see module docstring
    nth: int | None = None  # monthly_nth only: 1..4, or -1 for "last"


def next_occurrence(from_date: date, rule: RecurrenceRule) -> date | None:
    """The first occurrence strictly after `from_date`, or None once past `until`."""
    if rule.rule == "daily":
        nxt = from_date + timedelta(days=rule.interval)
    elif rule.rule == "weekly":
        nxt = _next_weekly(from_date, rule)
    elif rule.rule == "monthly":
        nxt = _add_months(from_date, rule.interval)
    elif rule.rule == "monthly_nth":
        nxt = _next_monthly_nth(from_date, rule)
    elif rule.rule == "yearly":
        nxt = _add_months(from_date, 12 * rule.interval)
    else:
        raise ValueError(f"Unknown recurrence rule: {rule.rule}")

    if rule.until is not None and nxt.isoformat() > rule.until:
        return None
    return nxt


def first_occurrence(rule: RecurrenceRule, on_or_after: date) -> date:
    """The first date on/after `on_or_after` that fits the rule's pattern —
    used to pick a due date for a new recurring task that has none."""
    if rule.rule == "weekly" and rule.weekdays:
        for offset in range(7):
            candidate = on_or_after + timedelta(days=offset)
            if candidate.weekday() in rule.weekdays:
                return candidate
    if rule.rule == "monthly_nth" and rule.weekdays and rule.nth:
        this_month = _nth_weekday(on_or_after.year, on_or_after.month, rule.weekdays[0], rule.nth)
        if this_month >= on_or_after:
            return this_month
        following = _add_months(on_or_after.replace(day=1), 1)
        return _nth_weekday(following.year, following.month, rule.weekdays[0], rule.nth)
    return on_or_after


def _next_weekly(from_date: date, rule: RecurrenceRule) -> date:
    if not rule.weekdays:
        return from_date + timedelta(weeks=rule.interval)
    days = sorted(set(rule.weekdays))
    week_start = from_date - timedelta(days=from_date.weekday())
    for day in days:
        if day > from_date.weekday():
            return week_start + timedelta(days=day)
    return week_start + timedelta(weeks=rule.interval, days=days[0])


def _next_monthly_nth(from_date: date, rule: RecurrenceRule) -> date:
    if not rule.weekdays or rule.nth is None:
        raise ValueError("monthly_nth rules need a weekday and an nth")
    weekday = rule.weekdays[0]
    this_month = _nth_weekday(from_date.year, from_date.month, weekday, rule.nth)
    if this_month > from_date:
        return this_month
    target = _add_months(from_date.replace(day=1), rule.interval)
    return _nth_weekday(target.year, target.month, weekday, rule.nth)


def _nth_weekday(year: int, month: int, weekday: int, nth: int) -> date:
    """The nth (1-4) or last (-1) `weekday` of the month."""
    if nth > 0:
        first = date(year, month, 1)
        return date(year, month, 1 + (weekday - first.weekday()) % 7 + 7 * (nth - 1))
    last_day = calendar.monthrange(year, month)[1]
    last = date(year, month, last_day)
    return date(year, month, last_day - (last.weekday() - weekday) % 7)


def _add_months(d: date, months: int) -> date:
    month_index = d.month - 1 + months
    year = d.year + month_index // 12
    month = month_index % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


# ---- text <-> rule ----


def parse_recurrence(text: str) -> RecurrenceRule | None:
    """Parses e.g. "every 2 weeks on mon,thu until 2026-12-31". Returns None
    for empty / "none"; raises RecurrenceError for anything unrecognised."""
    body = text.strip().lower()
    if body in _NO_RECURRENCE:
        return None

    until: str | None = None
    if match := re.search(r"\buntil\s+(\S+)", body):
        try:
            until = date.fromisoformat(match.group(1)).isoformat()
        except ValueError:
            raise RecurrenceError(
                f"'until' needs a date like 2026-12-31, not '{match.group(1)}'"
            ) from None
        body = body[: match.start()] + body[match.end() :]

    count: int | None = None
    if match := re.search(r"\b(?:for\s+)?(\d+)\s+times?\b|\bx(\d+)\b", body):
        count = int(match.group(1) or match.group(2))
        if count < 1:
            raise RecurrenceError("The number of times must be at least 1")
        body = body[: match.start()] + body[match.end() :]

    body = re.sub(r"\b(every|each)-", r"\1 ", body)
    tokens = re.sub(r",|\band\b", " ", body).split()
    tokens = [part for token in tokens for part in _GLUED.get(token, [token])]
    tokens = [_singular_day(token) for token in tokens]
    if tokens and tokens[0] in ("every", "each", "repeat", "repeats"):
        tokens = tokens[1:]
    if not tokens:
        raise RecurrenceError(f"Repeats needs a pattern — {_EXAMPLES}")

    rule = _parse_pattern(tokens)
    rule.until = until
    rule.count = count
    return rule


def _singular_day(token: str) -> str:
    """ "mondays" -> "monday" ("every mondays" / "fridays" read naturally)."""
    if token not in WEEKDAY_ALIASES and token.endswith("s") and token[:-1] in WEEKDAY_ALIASES:
        return token[:-1]
    return token


def _parse_pattern(tokens: list[str]) -> RecurrenceRule:
    if tokens[0] in ORDINALS:
        rest = tokens[2:]
        if (
            len(tokens) >= 2
            and tokens[1] in WEEKDAY_ALIASES
            and rest
            in (
                [],
                ["of", "the", "month"],
                ["of", "every", "month"],
                ["of", "month"],
            )
        ):
            return RecurrenceRule(
                rule="monthly_nth",
                weekdays=(WEEKDAY_ALIASES[tokens[1]],),
                nth=ORDINALS[tokens[0]],
            )
        raise RecurrenceError(f"Couldn't read '{' '.join(tokens)}' — {_EXAMPLES}")

    interval = 1
    explicit_interval = False
    if tokens[0] == "other":
        interval, explicit_interval, tokens = 2, True, tokens[1:]
    elif tokens[0].isdigit():
        interval, explicit_interval, tokens = int(tokens[0]), True, tokens[1:]
        if interval < 1:
            raise RecurrenceError("The interval must be at least 1")
    if not tokens:
        raise RecurrenceError(f"Repeats needs a unit like days or weeks — {_EXAMPLES}")

    unit, rest = tokens[0], tokens[1:]
    if unit in ("weekday", "weekdays") and not rest and not explicit_interval:
        return RecurrenceRule(rule="weekly", weekdays=_WEEKDAYS_MON_FRI)
    if unit in ("weekend", "weekends") and not rest and not explicit_interval:
        return RecurrenceRule(rule="weekly", weekdays=_WEEKEND)
    if unit in _UNITS:
        if explicit_interval and unit in _ADVERBS:
            raise RecurrenceError(f"Say 'every {interval} …s' (e.g. every {interval} weeks)")
        kind = _UNITS[unit]
        if kind == "weekly" and rest:
            if rest[0] != "on":
                raise RecurrenceError(f"Couldn't read '{' '.join(rest)}' — {_EXAMPLES}")
            return RecurrenceRule(rule="weekly", interval=interval, weekdays=_parse_days(rest[1:]))
        if rest:
            raise RecurrenceError(f"Couldn't read '{' '.join(rest)}' — {_EXAMPLES}")
        return RecurrenceRule(rule=kind, interval=interval)
    if unit in WEEKDAY_ALIASES and not explicit_interval:
        return RecurrenceRule(rule="weekly", weekdays=_parse_days(tokens))
    raise RecurrenceError(f"Couldn't read '{' '.join(tokens)}' — {_EXAMPLES}")


def _parse_days(tokens: list[str]) -> tuple[int, ...]:
    if not tokens:
        raise RecurrenceError("Name the days, e.g. on mon,thu")
    days: set[int] = set()
    for token in tokens:
        if token not in WEEKDAY_ALIASES:
            raise RecurrenceError(f"'{token}' is not a weekday (use mon, tue, wed, …)")
        days.add(WEEKDAY_ALIASES[token])
    return tuple(sorted(days))


def format_recurrence(rule: RecurrenceRule) -> str:
    """The canonical text for `rule`; parse_recurrence(format_recurrence(r)) == r."""
    if rule.rule == "monthly_nth" and rule.weekdays and rule.nth is not None:
        text = f"every {ORDINAL_NAMES[rule.nth]} {WEEKDAY_SHORT[rule.weekdays[0]]}"
    elif rule.rule == "weekly" and rule.weekdays:
        if rule.interval == 1 and rule.weekdays == _WEEKDAYS_MON_FRI:
            text = "every weekday"
        elif rule.interval == 1 and rule.weekdays == _WEEKEND:
            text = "every weekend"
        else:
            days = ",".join(WEEKDAY_SHORT[d] for d in rule.weekdays)
            text = (
                f"every {days}" if rule.interval == 1 else f"every {rule.interval} weeks on {days}"
            )
    else:
        unit = {"daily": "day", "weekly": "week", "monthly": "month", "yearly": "year"}[rule.rule]
        text = f"every {unit}" if rule.interval == 1 else f"every {rule.interval} {unit}s"
    if rule.until:
        text += f" until {rule.until}"
    if rule.count:
        text += f" for {rule.count} times"
    return text
