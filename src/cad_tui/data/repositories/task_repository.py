"""SQLite-backed CRUD for Task, including a restore() used to undo deletes."""

from __future__ import annotations

import sqlite3

from cad_tui.domain.models import Task

_COLUMNS = (
    "title", "notes", "project_id", "priority", "status", "due_date",
    "due_time", "estimate_min", "actual_min", "parent_task_id",
    "recurrence_id",
)


class TaskRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def create(self, task: Task) -> int:
        with self.conn:
            cur = self.conn.execute(
                f"INSERT INTO task ({', '.join(_COLUMNS)}) "
                f"VALUES ({', '.join('?' for _ in _COLUMNS)})",
                tuple(getattr(task, c) for c in _COLUMNS),
            )
            task_id = cur.lastrowid
            self._set_tags(task_id, task.tag_ids)
        return task_id

    def get(self, task_id: int) -> Task | None:
        row = self.conn.execute("SELECT * FROM task WHERE id = ?", (task_id,)).fetchone()
        return self._row_to_task(row) if row is not None else None

    def list(self, *, status: str | None = None, project_id: int | None = None) -> list[Task]:
        query = "SELECT * FROM task WHERE 1=1"
        params: list = []
        if status is not None:
            query += " AND status = ?"
            params.append(status)
        if project_id is not None:
            query += " AND project_id = ?"
            params.append(project_id)
        query += " ORDER BY status ASC, priority ASC, (due_date IS NULL), due_date ASC, id ASC"
        rows = self.conn.execute(query, params).fetchall()
        return [self._row_to_task(r) for r in rows]

    def update(self, task_id: int, **fields) -> None:
        tag_ids = fields.pop("tag_ids", None)
        with self.conn:
            if fields:
                set_clause = ", ".join(f"{k} = ?" for k in fields)
                self.conn.execute(
                    f"UPDATE task SET {set_clause}, updated_at = datetime('now') WHERE id = ?",
                    (*fields.values(), task_id),
                )
            if tag_ids is not None:
                self._set_tags(task_id, tag_ids)

    def mark_done(self, task_id: int) -> None:
        with self.conn:
            self.conn.execute(
                "UPDATE task SET status = 'done', completed_at = datetime('now'), "
                "updated_at = datetime('now') WHERE id = ?",
                (task_id,),
            )

    def mark_open(self, task_id: int) -> None:
        with self.conn:
            self.conn.execute(
                "UPDATE task SET status = 'open', completed_at = NULL, "
                "updated_at = datetime('now') WHERE id = ?",
                (task_id,),
            )

    def delete(self, task_id: int) -> None:
        with self.conn:
            self.conn.execute("DELETE FROM task WHERE id = ?", (task_id,))

    def restore(self, task: Task) -> int:
        """Re-insert a previously deleted task with its original id and tags (undo)."""
        with self.conn:
            self.conn.execute(
                """INSERT INTO task
                   (id, title, notes, project_id, priority, status, due_date, due_time,
                    estimate_min, actual_min, parent_task_id, recurrence_id,
                    reschedule_count, created_at, updated_at, completed_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    task.id, task.title, task.notes, task.project_id, task.priority,
                    task.status, task.due_date, task.due_time, task.estimate_min,
                    task.actual_min, task.parent_task_id, task.recurrence_id,
                    task.reschedule_count, task.created_at, task.updated_at,
                    task.completed_at,
                ),
            )
            self._set_tags(task.id, task.tag_ids)
        return task.id

    def _set_tags(self, task_id: int, tag_ids: list[int]) -> None:
        self.conn.execute("DELETE FROM task_tag WHERE task_id = ?", (task_id,))
        if tag_ids:
            self.conn.executemany(
                "INSERT INTO task_tag (task_id, tag_id) VALUES (?, ?)",
                [(task_id, tid) for tid in tag_ids],
            )

    def _row_to_task(self, row: sqlite3.Row) -> Task:
        tag_ids = [
            r["tag_id"]
            for r in self.conn.execute(
                "SELECT tag_id FROM task_tag WHERE task_id = ?", (row["id"],)
            )
        ]
        return Task(
            id=row["id"],
            title=row["title"],
            notes=row["notes"],
            project_id=row["project_id"],
            priority=row["priority"],
            status=row["status"],
            due_date=row["due_date"],
            due_time=row["due_time"],
            estimate_min=row["estimate_min"],
            actual_min=row["actual_min"],
            parent_task_id=row["parent_task_id"],
            recurrence_id=row["recurrence_id"],
            reschedule_count=row["reschedule_count"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            completed_at=row["completed_at"],
            tag_ids=tag_ids,
        )
