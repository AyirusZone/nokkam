from __future__ import annotations

import sqlite3


class DependencyRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def set_blocked_by(self, task_id: int, blocker_task_id: int | None) -> None:
        with self.conn:
            self.conn.execute("DELETE FROM task_dependency WHERE task_id = ?", (task_id,))
            if blocker_task_id is not None:
                self.conn.execute(
                    "INSERT INTO task_dependency (task_id, blocked_by_task_id) VALUES (?, ?)",
                    (task_id, blocker_task_id),
                )

    def get_blocker_id(self, task_id: int) -> int | None:
        row = self.conn.execute(
            "SELECT blocked_by_task_id FROM task_dependency WHERE task_id = ?", (task_id,)
        ).fetchone()
        return row["blocked_by_task_id"] if row else None

    def is_blocked(self, task_id: int) -> bool:
        row = self.conn.execute(
            """SELECT 1 FROM task_dependency td
               JOIN task blocker ON blocker.id = td.blocked_by_task_id
               WHERE td.task_id = ? AND blocker.status != 'done'""",
            (task_id,),
        ).fetchone()
        return row is not None
