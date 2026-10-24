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

    def minutes_by_task(self, since: str | None = None) -> dict[int, float]:
        """Logged minutes per task (running timers count up to now). With
        `since` (an ISO date), only log segments that started on or after
        that date are counted."""
        query = """SELECT task_id,
                   SUM((julianday(COALESCE(end_at, datetime('now', 'localtime')))
                        - julianday(start_at)) * 24 * 60) AS minutes
                   FROM time_log"""
        params: tuple[str, ...] = ()
        if since is not None:
            query += " WHERE start_at >= ?"
            params = (since,)
        rows = self.conn.execute(query + " GROUP BY task_id", params).fetchall()
        return {r["task_id"]: float(r["minutes"]) for r in rows}

    def minutes_by_task_and_day(self, since: str | None = None) -> list[tuple[int, str, float]]:
        """(task_id, ISO day, minutes) rows; a segment counts on the day it
        started. With `since` (an ISO date), only segments starting on or
        after it."""
        query = """SELECT task_id, date(start_at) AS day,
                   SUM((julianday(COALESCE(end_at, datetime('now', 'localtime')))
                        - julianday(start_at)) * 24 * 60) AS minutes
                   FROM time_log"""
        params: tuple[str, ...] = ()
        if since is not None:
            query += " WHERE start_at >= ?"
            params = (since,)
        rows = self.conn.execute(query + " GROUP BY task_id, day", params).fetchall()
        return [(r["task_id"], r["day"], float(r["minutes"])) for r in rows]
