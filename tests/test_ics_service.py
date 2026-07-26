from pathlib import Path
from unittest.mock import patch

from cad_tui.data.db import connect
from cad_tui.data.migrations import apply_migrations
from cad_tui.data.repositories.event_repository import EventRepository
from cad_tui.infra.ics_adapter import ParsedEvent
from cad_tui.services.ics_service import IcsService

SAMPLE_ICS = """\
BEGIN:VEVENT
UID:abc-123
SUMMARY:Flight to Paris
DTSTART:20260815T140000Z
DTEND:20260815T220000Z
END:VEVENT
"""


def make_service(db_path: Path, sources: list[str]) -> IcsService:
    conn = connect(db_path)
    apply_migrations(conn)
    return IcsService(EventRepository(conn), sources)


def test_refresh_syncs_a_local_ics_file(tmp_path: Path) -> None:
    ics_path = tmp_path / "calendar.ics"
    ics_path.write_text(SAMPLE_ICS)
    service = make_service(tmp_path / "data.db", [str(ics_path)])

    synced = service.refresh()

    assert synced == 1
    events = service.events_by_date("2026-08")["2026-08-15"]
    assert len(events) == 1
    assert events[0].title == "Flight to Paris"
    assert events[0].uid == "abc-123"


def test_refresh_is_idempotent_no_duplicates(tmp_path: Path) -> None:
    ics_path = tmp_path / "calendar.ics"
    ics_path.write_text(SAMPLE_ICS)
    service = make_service(tmp_path / "data.db", [str(ics_path)])

    service.refresh()
    service.refresh()

    events = service.events_by_date("2026-08")["2026-08-15"]
    assert len(events) == 1


def test_a_bad_source_does_not_raise_or_stop_others(tmp_path: Path) -> None:
    good_path = tmp_path / "good.ics"
    good_path.write_text(SAMPLE_ICS)
    bad_path = tmp_path / "does-not-exist.ics"
    service = make_service(tmp_path / "data.db", [str(bad_path), str(good_path)])

    synced = service.refresh()

    assert synced == 1
    assert service.events_by_date("2026-08")


def test_events_by_date_empty_when_never_synced(tmp_path: Path) -> None:
    service = make_service(tmp_path / "data.db", [])
    assert service.events_by_date("2026-08") == {}


def test_refresh_replaces_stale_events_on_resync(tmp_path: Path) -> None:
    ics_path = tmp_path / "calendar.ics"
    ics_path.write_text(SAMPLE_ICS)
    service = make_service(tmp_path / "data.db", [str(ics_path)])
    service.refresh()

    ics_path.write_text(
        "BEGIN:VEVENT\nUID:new-1\nSUMMARY:Rescheduled\nDTSTART:20260901T100000Z\nEND:VEVENT\n"
    )
    service.refresh()

    assert service.events_by_date("2026-08") == {}
    events = service.events_by_date("2026-09")["2026-09-01"]
    assert events[0].title == "Rescheduled"


def test_url_source_uses_host_as_calendar_label(tmp_path: Path) -> None:
    service = make_service(tmp_path / "data.db", ["https://example.com/cal.ics"])
    with (
        patch("cad_tui.services.ics_service.fetch_ics_text", return_value=SAMPLE_ICS),
        patch(
            "cad_tui.services.ics_service.parse_ics",
            return_value=[
                ParsedEvent(
                    uid="abc-123",
                    title="Flight to Paris",
                    start_at="2026-08-15 14:00",
                    end_at="2026-08-15 22:00",
                    all_day=False,
                    location=None,
                    notes=None,
                )
            ],
        ),
    ):
        assert service.refresh() == 1
    calendars = service.repo.list_calendars()
    assert calendars[0].name == "example.com"
