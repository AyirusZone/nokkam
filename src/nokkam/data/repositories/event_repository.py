"""SQLite-backed storage for read-only .ics-synced calendar events.

Events are never edited from within nokkam — each refresh replaces a
calendar's entire event set wholesale, which keeps sync trivially
idempotent (no per-event UID diffing needed) since the source of truth is
always the external .ics feed, never local state.
"""

from __future__ import annotations

import sqlite3

from nokkam.domain.models import CalendarSource, Event


class EventRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def get_or_create_calendar(self, name: str, color: str = "#0A84FF") -> int:
        row = self.conn.execute("SELECT id FROM calendar WHERE name = ?", (name,)).fetchone()
        if row is not None:
            return row["id"]
        with self.conn:
            cur = self.conn.execute(
                "INSERT INTO calendar (name, color, source) VALUES (?, ?, 'ics-import')",
                (name, color),
            )
        assert cur.lastrowid is not None  # sqlite always assigns one on INSERT
        return cur.lastrowid

    def replace_events(self, calendar_id: int, events: list[Event]) -> None:
        """Replaces every event currently stored for `calendar_id`."""
        with self.conn:
            self.conn.execute("DELETE FROM event WHERE calendar_id = ?", (calendar_id,))
            if events:
                self.conn.executemany(
                    """INSERT INTO event
                       (title, start_at, end_at, all_day, calendar_id, location, notes, uid)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    [
                        (
                            e.title,
                            e.start_at,
                            e.end_at,
                            int(e.all_day),
                            calendar_id,
                            e.location,
                            e.notes,
                            e.uid,
                        )
                        for e in events
                    ],
                )

    def list_matching_prefix(self, date_prefix: str) -> list[Event]:
        """All events whose `start_at` begins with `date_prefix` (e.g. a
        "YYYY-MM" month or "YYYY-MM-DD" exact day), earliest first."""
        rows = self.conn.execute(
            "SELECT * FROM event WHERE start_at LIKE ? ORDER BY start_at",
            (f"{date_prefix}%",),
        ).fetchall()
        return [self._row_to_event(r) for r in rows]

    def list_calendars(self) -> list[CalendarSource]:
        rows = self.conn.execute(
            "SELECT * FROM calendar WHERE source = 'ics-import' ORDER BY name"
        ).fetchall()
        return [
            CalendarSource(id=r["id"], name=r["name"], color=r["color"], source=r["source"])
            for r in rows
        ]

    def _row_to_event(self, row: sqlite3.Row) -> Event:
        return Event(
            id=row["id"],
            title=row["title"],
            start_at=row["start_at"],
            end_at=row["end_at"],
            all_day=bool(row["all_day"]),
            calendar_id=row["calendar_id"],
            location=row["location"],
            notes=row["notes"],
            uid=row["uid"],
        )
