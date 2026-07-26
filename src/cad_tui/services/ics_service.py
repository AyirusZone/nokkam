"""Best-effort sync of read-only calendar events from configured .ics
sources. A single source failing (offline, bad URL, malformed file) never
raises — it just leaves that source's previously-cached events in place,
consistent with how desktop notifications and reminders are best-effort
elsewhere in this app.
"""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

from cad_tui.data.repositories.event_repository import EventRepository
from cad_tui.domain.models import Event
from cad_tui.infra.ics_adapter import fetch_ics_text, parse_ics


class IcsService:
    def __init__(self, repo: EventRepository, sources: list[str]) -> None:
        self.repo = repo
        self.sources = sources

    def refresh(self) -> int:
        """Re-fetches every configured source. Returns how many synced
        without error (out of len(self.sources))."""
        synced = 0
        for source in self.sources:
            if self._sync_one(source):
                synced += 1
        return synced

    def _sync_one(self, source: str) -> bool:
        try:
            text = fetch_ics_text(source)
            parsed = parse_ics(text)
        except Exception:  # noqa: BLE001 - best-effort sync, one bad source must not stop the rest
            return False
        calendar_id = self.repo.get_or_create_calendar(_label_for(source))
        events = [
            Event(
                title=p.title,
                start_at=p.start_at,
                end_at=p.end_at,
                all_day=p.all_day,
                location=p.location,
                notes=p.notes,
                uid=p.uid,
            )
            for p in parsed
        ]
        self.repo.replace_events(calendar_id, events)
        return True

    def events_by_date(self, date_prefix: str) -> dict[str, list[Event]]:
        """All synced events whose date starts with `date_prefix` (e.g. a
        "YYYY-MM" month prefix), grouped by ISO date."""
        by_date: dict[str, list[Event]] = {}
        for event in self.repo.list_matching_prefix(date_prefix):
            by_date.setdefault(event.start_at[:10], []).append(event)
        return by_date


def _label_for(source: str) -> str:
    """A short, stable display name for a configured source — the file's
    stem for a local path, or the host for a URL."""
    if source.startswith(("http://", "https://")):
        return urlparse(source).netloc or source
    return Path(source).stem or source
