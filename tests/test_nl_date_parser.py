from datetime import date

from nokkam.domain.nl_date_parser import parse_quick_text

ANCHOR = date(2026, 7, 25)  # a Saturday


def test_plain_title_no_date() -> None:
    result = parse_quick_text("Buy milk", today=ANCHOR)
    assert result.title == "Buy milk"
    assert result.due_date is None
    assert result.due_time is None


def test_today() -> None:
    result = parse_quick_text("Call mom today", today=ANCHOR)
    assert result.due_date == ANCHOR.isoformat()
    assert result.title == "Call mom"


def test_tomorrow_and_tmrw() -> None:
    for word in ("tomorrow", "tmrw"):
        result = parse_quick_text(f"Buy milk {word}", today=ANCHOR)
        assert result.due_date == "2026-07-26"
        assert result.title == "Buy milk"


def test_weekday_next_occurrence() -> None:
    result = parse_quick_text("Standup fri", today=ANCHOR)
    assert result.due_date == "2026-07-31"
    assert result.title == "Standup"


def test_weekday_today_matches_today() -> None:
    result = parse_quick_text("Weekend chores sat", today=ANCHOR)
    assert result.due_date == "2026-07-25"


def test_in_n_days() -> None:
    result = parse_quick_text("Follow up in 3 days", today=ANCHOR)
    assert result.due_date == "2026-07-28"
    assert result.title == "Follow up"


def test_in_n_weeks() -> None:
    result = parse_quick_text("Review in 2 weeks", today=ANCHOR)
    assert result.due_date == "2026-08-08"


def test_iso_date_passthrough() -> None:
    result = parse_quick_text("Renew passport 2026-09-01", today=ANCHOR)
    assert result.due_date == "2026-09-01"
    assert result.title == "Renew passport"


def test_time_ampm() -> None:
    result = parse_quick_text("Dentist tmrw 3pm", today=ANCHOR)
    assert result.due_date == "2026-07-26"
    assert result.due_time == "15:00"
    assert result.title == "Dentist"


def test_time_24h() -> None:
    result = parse_quick_text("Standup fri 09:30", today=ANCHOR)
    assert result.due_time == "09:30"


def test_time_noon_12pm() -> None:
    result = parse_quick_text("Lunch today 12pm", today=ANCHOR)
    assert result.due_time == "12:00"


def test_time_12am_is_midnight() -> None:
    result = parse_quick_text("Reset tmrw 12am", today=ANCHOR)
    assert result.due_time == "00:00"
