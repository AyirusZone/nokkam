from __future__ import annotations

import sqlite3

from cad_tui.domain.models import Project


class ProjectRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def create(self, name: str, color: str = "#8E8E93") -> int:
        with self.conn:
            cur = self.conn.execute(
                "INSERT INTO project (name, color) VALUES (?, ?)", (name, color)
            )
        return cur.lastrowid

    def get(self, project_id: int) -> Project | None:
        row = self.conn.execute("SELECT * FROM project WHERE id = ?", (project_id,)).fetchone()
        return self._row_to_project(row) if row is not None else None

    def get_or_create(self, name: str) -> int:
        row = self.conn.execute("SELECT id FROM project WHERE name = ?", (name,)).fetchone()
        return row["id"] if row else self.create(name)

    def list(self) -> list[Project]:
        rows = self.conn.execute(
            "SELECT * FROM project WHERE archived = 0 ORDER BY name"
        ).fetchall()
        return [self._row_to_project(r) for r in rows]

    def _row_to_project(self, row: sqlite3.Row) -> Project:
        return Project(
            id=row["id"], name=row["name"], color=row["color"], archived=bool(row["archived"])
        )
