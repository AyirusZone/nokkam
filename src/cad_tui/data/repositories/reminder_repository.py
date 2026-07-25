from __future__ import annotations

import sqlite3


class ReminderRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def has_been_sent(self, owner_type: str, owner_id: int) -> bool:
        row = self.conn.execute(
            "SELECT 1 FROM reminder WHERE owner_type = ? AND owner_id = ? AND sent = 1",
            (owner_type, owner_id),
        ).fetchone()
        return row is not None

    def mark_sent(self, owner_type: str, owner_id: int, remind_at: str) -> None:
        with self.conn:
            self.conn.execute(
                "INSERT INTO reminder (owner_type, owner_id, remind_at, sent) VALUES (?, ?, ?, 1)",
                (owner_type, owner_id, remind_at),
            )
