from __future__ import annotations

import sqlite3

from cad_tui.domain.models import Tag


class TagRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def create(self, name: str, color: str = "#8E8E93") -> int:
        with self.conn:
            cur = self.conn.execute("INSERT INTO tag (name, color) VALUES (?, ?)", (name, color))
        assert cur.lastrowid is not None  # sqlite always assigns one on INSERT
        return cur.lastrowid

    def get_or_create(self, name: str) -> int:
        row = self.conn.execute("SELECT id FROM tag WHERE name = ?", (name,)).fetchone()
        return row["id"] if row else self.create(name)

    def get_or_create_many(self, names: list[str]) -> list[int]:
        return [self.get_or_create(n.strip()) for n in names if n.strip()]

    def get_many(self, ids: list[int]) -> list[Tag]:
        if not ids:
            return []
        placeholders = ",".join("?" for _ in ids)
        rows = self.conn.execute(f"SELECT * FROM tag WHERE id IN ({placeholders})", ids).fetchall()
        return [Tag(id=r["id"], name=r["name"], color=r["color"]) for r in rows]

    def list(self) -> list[Tag]:
        rows = self.conn.execute("SELECT * FROM tag ORDER BY name").fetchall()
        return [Tag(id=r["id"], name=r["name"], color=r["color"]) for r in rows]
