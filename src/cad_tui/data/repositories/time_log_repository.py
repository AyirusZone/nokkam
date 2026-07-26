from __future__ import annotations

import sqlite3


class TimeLogRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def start(self, task_id: int) -> int:
        with self.conn:
            cur = self.conn.execute(
                "INSERT INTO time_log (task_id, start_at) VALUES (?, datetime('now', 'localtime'))",
                (task_id,),
            )
        assert cur.lastrowid is not None  # sqlite always assigns one on INSERT
        return cur.lastrowid

    def stop(self, time_log_id: int) -> None:
        with self.conn:
            self.conn.execute(
                "UPDATE time_log SET end_at = datetime('now', 'localtime') WHERE id = ?",
                (time_log_id,),
            )

    def active_for_task(self, task_id: int) -> int | None:
        row = self.conn.execute(
            "SELECT id FROM time_log WHERE task_id = ? AND end_at IS NULL", (task_id,)
        ).fetchone()
        return row["id"] if row else None

    def total_minutes_for_task(self, task_id: int) -> int:
        row = self.conn.execute(
            """SELECT COALESCE(SUM(
                   (julianday(COALESCE(end_at, datetime('now', 'localtime')))
                    - julianday(start_at)) * 24 * 60
               ), 0) AS minutes
               FROM time_log WHERE task_id = ?""",
            (task_id,),
        ).fetchone()
        return int(row["minutes"])
