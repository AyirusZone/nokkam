from __future__ import annotations

import sqlite3

from nokkam.domain.models import SavedFilter


class SavedFilterRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def save(self, name: str, query: str) -> None:
        """Create the filter, or replace the query if the name already exists."""
        with self.conn:
            self.conn.execute(
                "INSERT INTO saved_filter (name, query) VALUES (?, ?) "
                "ON CONFLICT(name) DO UPDATE SET query = excluded.query",
                (name, query),
            )

    def list(self) -> list[SavedFilter]:
        rows = self.conn.execute("SELECT * FROM saved_filter ORDER BY name").fetchall()
        return [SavedFilter(id=r["id"], name=r["name"], query=r["query"]) for r in rows]

    def delete(self, name: str) -> None:
        with self.conn:
            self.conn.execute("DELETE FROM saved_filter WHERE name = ?", (name,))
