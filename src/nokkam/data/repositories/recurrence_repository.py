from __future__ import annotations

import sqlite3

from nokkam.domain.recurrence import RecurrenceRule


class RecurrenceRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def create(self, rule: RecurrenceRule) -> int:
        with self.conn:
            cur = self.conn.execute(
                "INSERT INTO recurrence (rule, interval, until, count, weekdays, nth) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    rule.rule,
                    rule.interval,
                    rule.until,
                    rule.count,
                    ",".join(str(d) for d in rule.weekdays) or None,
                    rule.nth,
                ),
            )
        assert cur.lastrowid is not None  # sqlite always assigns one on INSERT
        return cur.lastrowid

    def update(self, recurrence_id: int, rule: RecurrenceRule) -> None:
        """Change a series' rule in place, so every task already in the series
        (and its habit history) stays attached to it."""
        with self.conn:
            self.conn.execute(
                "UPDATE recurrence SET rule = ?, interval = ?, until = ?, count = ?, "
                "weekdays = ?, nth = ? WHERE id = ?",
                (
                    rule.rule,
                    rule.interval,
                    rule.until,
                    rule.count,
                    ",".join(str(d) for d in rule.weekdays) or None,
                    rule.nth,
                    recurrence_id,
                ),
            )

    def get(self, recurrence_id: int) -> RecurrenceRule | None:
        row = self.conn.execute(
            "SELECT * FROM recurrence WHERE id = ?", (recurrence_id,)
        ).fetchone()
        if row is None:
            return None
        return RecurrenceRule(
            rule=row["rule"],
            interval=row["interval"],
            until=row["until"],
            count=row["count"],
            weekdays=tuple(int(d) for d in row["weekdays"].split(",")) if row["weekdays"] else (),
            nth=row["nth"],
        )
