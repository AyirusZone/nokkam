from __future__ import annotations

import sqlite3

from nokkam.domain.recurrence import RecurrenceRule


class RecurrenceRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def create(self, rule: RecurrenceRule) -> int:
        with self.conn:
            cur = self.conn.execute(
                "INSERT INTO recurrence (rule, interval, until, count) VALUES (?, ?, ?, ?)",
                (rule.rule, rule.interval, rule.until, rule.count),
            )
        assert cur.lastrowid is not None  # sqlite always assigns one on INSERT
        return cur.lastrowid

    def get(self, recurrence_id: int) -> RecurrenceRule | None:
        row = self.conn.execute(
            "SELECT * FROM recurrence WHERE id = ?", (recurrence_id,)
        ).fetchone()
        if row is None:
            return None
        return RecurrenceRule(
            rule=row["rule"], interval=row["interval"], until=row["until"], count=row["count"]
        )
