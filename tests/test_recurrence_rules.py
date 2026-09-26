from datetime import date

import pytest

from nokkam.domain.recurrence import (
    RecurrenceError,
    RecurrenceRule,
    first_occurrence,
    format_recurrence,
    next_occurrence,
    parse_recurrence,
)

# 2026-07-27 is a Monday.
MON = date(2026, 7, 27)


def rule(kind: str, **kw) -> RecurrenceRule:
    return RecurrenceRule(rule=kind, **kw)


# ---- next_occurrence ----


def test_every_n_days_and_weeks_and_years() -> None:
    assert next_occurrence(MON, rule("daily", interval=3)) == date(2026, 7, 30)
    assert next_occurrence(MON, rule("weekly", interval=2)) == date(2026, 8, 10)
    assert next_occurrence(MON, rule("yearly")) == date(2027, 7, 27)


def test_yearly_clamps_feb_29() -> None:
    assert next_occurrence(date(2028, 2, 29), rule("yearly")) == date(2029, 2, 28)
    assert next_occurrence(date(2028, 2, 29), rule("yearly", interval=4)) == date(2032, 2, 29)


def test_weekly_on_days_walks_through_the_week_then_wraps() -> None:
    r = rule("weekly", weekdays=(0, 2, 4))  # Mon, Wed, Fri
    assert next_occurrence(date(2026, 7, 27), r) == date(2026, 7, 29)  # Mon -> Wed
    assert next_occurrence(date(2026, 7, 29), r) == date(2026, 7, 31)  # Wed -> Fri
    assert next_occurrence(date(2026, 7, 31), r) == date(2026, 8, 3)  # Fri -> next Mon


def test_weekly_on_days_from_a_day_not_in_the_set() -> None:
    r = rule("weekly", weekdays=(0, 2))
    assert next_occurrence(date(2026, 7, 30), r) == date(2026, 8, 3)  # Thu -> Mon


def test_biweekly_on_days_skips_the_off_week() -> None:
    r = rule("weekly", interval=2, weekdays=(0, 3))  # every 2 weeks Mon+Thu
    assert next_occurrence(date(2026, 7, 27), r) == date(2026, 7, 30)  # Mon -> Thu same week
    assert next_occurrence(date(2026, 7, 30), r) == date(2026, 8, 10)  # Thu -> Mon two weeks on


def test_weekdays_skip_the_weekend() -> None:
    r = rule("weekly", weekdays=(0, 1, 2, 3, 4))
    assert next_occurrence(date(2026, 7, 31), r) == date(2026, 8, 3)  # Fri -> Mon
    assert next_occurrence(date(2026, 8, 1), r) == date(2026, 8, 3)  # Sat -> Mon


@pytest.mark.parametrize(
    ("start", "nth", "weekday", "expected"),
    [
        (date(2026, 7, 1), 1, 1, date(2026, 7, 7)),  # first Tue of July, from the 1st
        (date(2026, 7, 7), 1, 1, date(2026, 8, 4)),  # already on it -> next month
        (date(2026, 7, 8), 1, 1, date(2026, 8, 4)),  # past it -> next month
        (date(2026, 7, 1), 3, 4, date(2026, 7, 17)),  # third Fri
        (date(2026, 7, 1), -1, 4, date(2026, 7, 31)),  # last Fri (the 31st)
        (date(2026, 7, 31), -1, 4, date(2026, 8, 28)),  # last Fri of August
        (date(2026, 1, 20), -1, 0, date(2026, 1, 26)),  # last Mon, still ahead
        (date(2026, 12, 20), 1, 0, date(2027, 1, 4)),  # rolls over the year
    ],
)
def test_nth_weekday_of_month(start: date, nth: int, weekday: int, expected: date) -> None:
    r = rule("monthly_nth", weekdays=(weekday,), nth=nth)
    assert next_occurrence(start, r) == expected


def test_nth_weekday_every_other_month() -> None:
    r = rule("monthly_nth", interval=2, weekdays=(1,), nth=1)
    assert next_occurrence(date(2026, 7, 7), r) == date(2026, 9, 1)


def test_until_stops_every_kind() -> None:
    assert next_occurrence(MON, rule("weekly", weekdays=(2,), until="2026-07-28")) is None
    assert next_occurrence(MON, rule("weekly", weekdays=(2,), until="2026-07-29")) == date(
        2026, 7, 29
    )
    assert next_occurrence(MON, rule("yearly", until="2027-07-26")) is None


def test_unknown_rule_raises() -> None:
    with pytest.raises(ValueError, match="Unknown recurrence rule"):
        next_occurrence(MON, rule("fortnightly"))


# ---- first_occurrence ----


def test_first_occurrence_picks_the_first_matching_day_including_today() -> None:
    weekdays = rule("weekly", weekdays=(0, 1, 2, 3, 4))
    assert first_occurrence(weekdays, MON) == MON
    assert first_occurrence(weekdays, date(2026, 8, 1)) == date(2026, 8, 3)  # Sat -> Mon
    assert first_occurrence(rule("weekly", weekdays=(4,)), MON) == date(2026, 7, 31)


def test_first_occurrence_of_nth_weekday_and_plain_rules() -> None:
    first_tue = rule("monthly_nth", weekdays=(1,), nth=1)
    assert first_occurrence(first_tue, date(2026, 7, 1)) == date(2026, 7, 7)
    assert first_occurrence(first_tue, date(2026, 7, 8)) == date(2026, 8, 4)
    assert first_occurrence(rule("daily"), MON) == MON
    assert first_occurrence(rule("monthly"), MON) == MON


# ---- parse_recurrence ----


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("daily", rule("daily")),
        ("every day", rule("daily")),
        ("Every 3 days", rule("daily", interval=3)),
        ("every other day", rule("daily", interval=2)),
        ("weekly", rule("weekly")),
        ("every 2 weeks", rule("weekly", interval=2)),
        ("every weekday", rule("weekly", weekdays=(0, 1, 2, 3, 4))),
        ("weekdays", rule("weekly", weekdays=(0, 1, 2, 3, 4))),
        ("every weekend", rule("weekly", weekdays=(5, 6))),
        ("every mon,wed,fri", rule("weekly", weekdays=(0, 2, 4))),
        ("every Monday and Thursday", rule("weekly", weekdays=(0, 3))),
        ("every fri", rule("weekly", weekdays=(4,))),
        ("every 2 weeks on mon, thu", rule("weekly", interval=2, weekdays=(0, 3))),
        ("monthly", rule("monthly")),
        ("every 3 months", rule("monthly", interval=3)),
        ("yearly", rule("yearly")),
        ("annually", rule("yearly")),
        ("every year", rule("yearly")),
        ("every first tue", rule("monthly_nth", weekdays=(1,), nth=1)),
        ("every last friday", rule("monthly_nth", weekdays=(4,), nth=-1)),
        ("2nd thursday of the month", rule("monthly_nth", weekdays=(3,), nth=2)),
        ("every day until 2026-12-31", rule("daily", until="2026-12-31")),
        ("every week for 10 times", rule("weekly", count=10)),
        ("every day x5", rule("daily", count=5)),
        ("every month 6 times until 2027-01-01", rule("monthly", until="2027-01-01", count=6)),
    ],
)
def test_parse_recurrence(text: str, expected: RecurrenceRule) -> None:
    assert parse_recurrence(text) == expected


@pytest.mark.parametrize("text", ["", "  ", "none", "Never", "off"])
def test_parse_recurrence_none_means_no_recurrence(text: str) -> None:
    assert parse_recurrence(text) is None


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("every", "needs a pattern"),
        ("blorp", "Couldn't read"),
        ("every 0 days", "at least 1"),
        ("every 2 weekdays", "Couldn't read"),
        ("every 2 weekly", "Say 'every 2"),
        ("every 2 mon", "Couldn't read"),
        ("every week on", "Name the days"),
        ("every week on someday", "not a weekday"),
        ("every week mon", "Couldn't read"),
        ("every day tomorrow", "Couldn't read"),
        ("every first", "Couldn't read"),
        ("every first tue of never", "Couldn't read"),
        ("every day until soon", "needs a date"),
        ("every day until 2026-13-45", "needs a date"),
        ("every day for 0 times", "at least 1"),
    ],
)
def test_parse_recurrence_errors_are_readable(text: str, message: str) -> None:
    with pytest.raises(RecurrenceError, match=message):
        parse_recurrence(text)


def test_error_messages_include_examples() -> None:
    with pytest.raises(RecurrenceError, match="every mon,wed,fri"):
        parse_recurrence("blorp")


# ---- format_recurrence ----


@pytest.mark.parametrize(
    ("r", "text"),
    [
        (rule("daily"), "every day"),
        (rule("daily", interval=3), "every 3 days"),
        (rule("weekly", interval=2), "every 2 weeks"),
        (rule("monthly"), "every month"),
        (rule("yearly", interval=2), "every 2 years"),
        (rule("weekly", weekdays=(0, 1, 2, 3, 4)), "every weekday"),
        (rule("weekly", weekdays=(5, 6)), "every weekend"),
        (rule("weekly", weekdays=(0, 2, 4)), "every mon,wed,fri"),
        (rule("weekly", interval=2, weekdays=(0, 3)), "every 2 weeks on mon,thu"),
        (rule("monthly_nth", weekdays=(1,), nth=1), "every first tue"),
        (rule("monthly_nth", weekdays=(4,), nth=-1), "every last fri"),
        (rule("daily", until="2026-12-31", count=4), "every day until 2026-12-31 for 4 times"),
    ],
)
def test_format_recurrence(r: RecurrenceRule, text: str) -> None:
    assert format_recurrence(r) == text


@pytest.mark.parametrize("kind", ["daily", "weekly", "monthly", "yearly"])
@pytest.mark.parametrize("interval", [1, 2, 5])
@pytest.mark.parametrize("weekdays", [(), (0,), (1, 3), (0, 1, 2, 3, 4), (5, 6), (0, 2, 4, 6)])
@pytest.mark.parametrize(
    "limits", [(None, None), ("2027-01-01", None), (None, 3), ("2027-01-01", 3)]
)
def test_format_then_parse_round_trips(
    kind: str, interval: int, weekdays: tuple[int, ...], limits: tuple[str | None, int | None]
) -> None:
    if weekdays and kind != "weekly":
        return
    original = RecurrenceRule(
        rule=kind, interval=interval, weekdays=weekdays, until=limits[0], count=limits[1]
    )
    assert parse_recurrence(format_recurrence(original)) == original


@pytest.mark.parametrize("nth", [1, 2, 3, 4, -1])
@pytest.mark.parametrize("weekday", range(7))
def test_nth_weekday_round_trips(nth: int, weekday: int) -> None:
    original = RecurrenceRule(rule="monthly_nth", weekdays=(weekday,), nth=nth)
    assert parse_recurrence(format_recurrence(original)) == original
