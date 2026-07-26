from nokkam.infra.ics_adapter import parse_ics

SAMPLE_ICS = """\
BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:event-1@example.com
SUMMARY:Team standup
DTSTART:20260726T090000Z
DTEND:20260726T093000Z
LOCATION:Zoom
END:VEVENT
BEGIN:VEVENT
UID:event-2@example.com
SUMMARY:Company holiday
DTSTART;VALUE=DATE:20260801
END:VEVENT
BEGIN:VEVENT
UID:event-3@example.com
SUMMARY:A long description that wraps across a folded continuation line b
 ecause RFC5545 folds at 75 octets
DTSTART:20260901T120000Z
DESCRIPTION:Line one\\nLine two\\, with a comma
END:VEVENT
END:VCALENDAR
"""


def test_parses_timed_event() -> None:
    events = parse_ics(SAMPLE_ICS)
    standup = next(e for e in events if e.uid == "event-1@example.com")
    assert standup.title == "Team standup"
    assert standup.start_at == "2026-07-26 09:00"
    assert standup.end_at == "2026-07-26 09:30"
    assert standup.all_day is False
    assert standup.location == "Zoom"


def test_parses_all_day_event() -> None:
    events = parse_ics(SAMPLE_ICS)
    holiday = next(e for e in events if e.uid == "event-2@example.com")
    assert holiday.title == "Company holiday"
    assert holiday.start_at == "2026-08-01"
    assert holiday.all_day is True
    assert holiday.end_at is None


def test_unfolds_continuation_lines_and_unescapes_text() -> None:
    events = parse_ics(SAMPLE_ICS)
    long_one = next(e for e in events if e.uid == "event-3@example.com")
    assert long_one.title == (
        "A long description that wraps across a folded continuation line "
        "because RFC5545 folds at 75 octets"
    )
    assert long_one.notes == "Line one\nLine two, with a comma"


def test_returns_empty_list_for_no_events() -> None:
    assert parse_ics("BEGIN:VCALENDAR\nEND:VCALENDAR\n") == []


def test_missing_uid_gets_a_synthetic_one() -> None:
    text = "BEGIN:VEVENT\nSUMMARY:No uid\nDTSTART:20260101\nEND:VEVENT\n"
    events = parse_ics(text)
    assert len(events) == 1
    assert events[0].uid == "noid-0"
