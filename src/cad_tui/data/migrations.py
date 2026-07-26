"""Versioned schema migrations, applied via PRAGMA user_version.

apply_migrations() is idempotent: re-running it on an up-to-date database
is a no-op because each migration only runs if its version is still ahead
of the current user_version.
"""

from __future__ import annotations

import sqlite3

MIGRATIONS: list[tuple[int, str]] = [
    (
        1,
        """
        CREATE TABLE project (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            color TEXT NOT NULL DEFAULT '#8E8E93',
            archived INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE tag (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            color TEXT NOT NULL DEFAULT '#8E8E93'
        );

        CREATE TABLE recurrence (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rule TEXT NOT NULL,       -- daily | weekly | monthly | custom
            interval INTEGER NOT NULL DEFAULT 1,
            until TEXT,               -- ISO date, nullable
            count INTEGER             -- nullable, max occurrences
        );

        CREATE TABLE task (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            notes TEXT,
            project_id INTEGER REFERENCES project(id) ON DELETE SET NULL,
            priority INTEGER NOT NULL DEFAULT 2,   -- 1=high 2=med 3=low
            status TEXT NOT NULL DEFAULT 'open',   -- open | done
            due_date TEXT,                         -- ISO date, nullable
            due_time TEXT,                         -- HH:MM, nullable
            estimate_min INTEGER,
            actual_min INTEGER,
            parent_task_id INTEGER REFERENCES task(id) ON DELETE CASCADE,
            recurrence_id INTEGER REFERENCES recurrence(id) ON DELETE SET NULL,
            reschedule_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            completed_at TEXT
        );

        CREATE TABLE task_tag (
            task_id INTEGER NOT NULL REFERENCES task(id) ON DELETE CASCADE,
            tag_id INTEGER NOT NULL REFERENCES tag(id) ON DELETE CASCADE,
            PRIMARY KEY (task_id, tag_id)
        );

        CREATE TABLE calendar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            color TEXT NOT NULL DEFAULT '#0A84FF',
            source TEXT NOT NULL DEFAULT 'local'   -- local | ics-import
        );

        CREATE TABLE event (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            start_at TEXT NOT NULL,
            end_at TEXT,
            all_day INTEGER NOT NULL DEFAULT 0,
            calendar_id INTEGER REFERENCES calendar(id) ON DELETE SET NULL,
            recurrence_id INTEGER REFERENCES recurrence(id) ON DELETE SET NULL,
            location TEXT,
            notes TEXT
        );

        CREATE TABLE time_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER NOT NULL REFERENCES task(id) ON DELETE CASCADE,
            start_at TEXT NOT NULL,
            end_at TEXT
        );

        CREATE TABLE reminder (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_type TEXT NOT NULL,   -- task | event
            owner_id INTEGER NOT NULL,
            remind_at TEXT NOT NULL,
            sent INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE usage_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            target_id INTEGER,
            ts TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        );

        CREATE INDEX idx_task_due_date ON task(due_date);
        CREATE INDEX idx_task_status ON task(status);
        CREATE INDEX idx_event_start_at ON event(start_at);
        CREATE INDEX idx_usage_log_action ON usage_log(action, ts);
        """,
    ),
    (
        2,
        """
        CREATE TABLE task_dependency (
            task_id INTEGER NOT NULL REFERENCES task(id) ON DELETE CASCADE,
            blocked_by_task_id INTEGER NOT NULL REFERENCES task(id) ON DELETE CASCADE,
            PRIMARY KEY (task_id, blocked_by_task_id)
        );
        """,
    ),
    (
        3,
        """
        ALTER TABLE task ADD COLUMN private INTEGER NOT NULL DEFAULT 0;

        -- One row per configured .ics source (see AppConfig.ics_sources).
        -- `uid` is the ICS UID:PROP value, used to upsert on refresh instead
        -- of accumulating duplicates; NULL is only possible for a
        -- hypothetical future local (non-imported) event.
        ALTER TABLE event ADD COLUMN uid TEXT;
        CREATE UNIQUE INDEX idx_event_calendar_uid ON event(calendar_id, uid);
        """,
    ),
]


def apply_migrations(conn: sqlite3.Connection) -> int:
    """Apply any pending migrations. Returns the resulting schema version."""
    current_version = conn.execute("PRAGMA user_version").fetchone()[0]

    for version, sql in MIGRATIONS:
        if version <= current_version:
            continue
        with conn:
            conn.executescript(sql)
            conn.execute(f"PRAGMA user_version = {version}")
        current_version = version

    return current_version
