from __future__ import annotations

import sqlite3

from cad_tui.domain.models import Project

# Assigned round-robin to new projects (by creation order) so distinct
# projects are visually distinguishable throughout the app — in the
# projects pane, the "All tasks" group headers, and each task row's
# project marker — without anyone having to pick a color by hand.
PROJECT_COLOR_PALETTE = [
    "#5AC8FA",  # sky blue
    "#BF5AF2",  # violet
    "#FF9F0A",  # amber
    "#30D5C8",  # teal
    "#FF6482",  # coral pink
    "#98D65A",  # lime
    "#64D2FF",  # cyan
    "#D65A9E",  # rose
]


class ProjectRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def create(self, name: str, color: str | None = None) -> int:
        if color is None:
            color = self._next_color()
        with self.conn:
            cur = self.conn.execute(
                "INSERT INTO project (name, color) VALUES (?, ?)", (name, color)
            )
        assert cur.lastrowid is not None  # sqlite always assigns one on INSERT
        return cur.lastrowid

    def _next_color(self) -> str:
        row = self.conn.execute("SELECT COUNT(*) AS c FROM project").fetchone()
        return PROJECT_COLOR_PALETTE[row["c"] % len(PROJECT_COLOR_PALETTE)]

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
