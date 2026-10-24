"""TOML-backed app configuration with sane defaults.

Config lives at ~/.nokkam/config.toml; a missing file just means defaults.
A malformed file or a bad value never stops the app from starting — it is
reported in `AppConfig.warnings` (shown as notifications) and the default
is used instead.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from nokkam.domain.models import Priority

DEFAULT_ACCENT = "#FF6B4A"  # signature warm vermillion — see presentation/theme.py

PRIORITY_NAMES = {"high": Priority.HIGH, "medium": Priority.MEDIUM, "low": Priority.LOW}
FIRST_WEEKDAYS = {"monday": 0, "sunday": 6}
KNOWN_KEYS = {
    "theme",
    "accent",
    "db_path",
    "icons",
    "ics_sources",
    "keys",
    "default_priority",
    "first_weekday",
    "start_filter",
}


def default_app_dir() -> Path:
    return Path.home() / ".nokkam"


@dataclass
class AppConfig:
    theme: str = "nokkam-dark"
    accent: str = DEFAULT_ACCENT
    db_path: Path = field(default_factory=lambda: default_app_dir() / "data.db")
    app_dir: Path = field(default_factory=default_app_dir)
    # Keyword -> icon overrides, merged over the built-in defaults (see
    # domain/icons.py). e.g. icons = { flight = "✈", standup = "🗣" }
    icons: dict[str, str] = field(default_factory=dict)
    # Local paths or URLs to read-only .ics calendars (iCloud/Google Calendar
    # exports or share links). Empty by default — no network access unless
    # you opt in here.
    ics_sources: list[str] = field(default_factory=list)
    # Binding id -> key(s), overriding the defaults, e.g. [keys] add_task = "n"
    # (comma-separate to bind several). Unknown ids and conflicting keys are
    # reported at startup — see presentation/keymap.py.
    keys: dict[str, str] = field(default_factory=dict)
    # Priority a new task starts with (a Priority value).
    default_priority: int = Priority.MEDIUM
    # Which weekday the calendar's week starts on, as Python's weekday()
    # number: 0 = Monday, 6 = Sunday.
    first_weekday: int = 0
    # A smart list (today / overdue / week) or saved-filter name applied on launch.
    start_filter: str | None = None
    # Problems found while loading (bad TOML, wrong types, unknown keys).
    warnings: list[str] = field(default_factory=list, compare=False)


def load_config(config_path: Path | None = None) -> AppConfig:
    path = config_path or (default_app_dir() / "config.toml")
    if not path.exists():
        return AppConfig()

    try:
        with path.open("rb") as f:
            raw = tomllib.load(f)
    except (tomllib.TOMLDecodeError, OSError, UnicodeDecodeError) as exc:
        return AppConfig(warnings=[f"Could not read {path}: {exc} — using defaults"])

    app_dir = default_app_dir()
    config = AppConfig(app_dir=app_dir)
    warnings = config.warnings

    for key in sorted(set(raw) - KNOWN_KEYS):
        warnings.append(f"Unknown config option '{key}' (ignored)")

    def get(name: str, kind: type, describe: str) -> Any:
        """The value for `name` if it has type `kind`, else None (+ a warning)."""
        if name not in raw:
            return None
        value = raw[name]
        if isinstance(value, kind):
            return value
        warnings.append(f"Config option '{name}' must be {describe} (ignored)")
        return None

    if (theme := get("theme", str, "a string")) is not None:
        config.theme = theme
    if (accent := get("accent", str, "a hex color string")) is not None:
        config.accent = accent
    if (db_path := get("db_path", str, "a path string")) is not None:
        config.db_path = Path(db_path).expanduser()
    else:
        config.db_path = app_dir / "data.db"
    if (icons := get("icons", dict, "a table of keyword = icon")) is not None:
        config.icons = {str(k): str(v) for k, v in icons.items()}
    if (sources := get("ics_sources", list, "a list of paths or URLs")) is not None:
        config.ics_sources = [str(s) for s in sources]
    if (keys := get("keys", dict, "a table of binding = key")) is not None:
        for binding_id, key in keys.items():
            if isinstance(key, str) and key.strip():
                config.keys[binding_id] = key.strip()
            else:
                warnings.append(f'[keys] {binding_id} must be a key name like "n" (ignored)')
    if (priority := get("default_priority", str, "high, medium or low")) is not None:
        if priority.lower() in PRIORITY_NAMES:
            config.default_priority = PRIORITY_NAMES[priority.lower()]
        else:
            warnings.append(f"default_priority '{priority}' must be high, medium or low (ignored)")
    if (weekday := get("first_weekday", str, "monday or sunday")) is not None:
        if weekday.lower() in FIRST_WEEKDAYS:
            config.first_weekday = FIRST_WEEKDAYS[weekday.lower()]
        else:
            warnings.append(f"first_weekday '{weekday}' must be monday or sunday (ignored)")
    if (start_filter := get("start_filter", str, "a smart list or saved filter name")) is not None:
        config.start_filter = start_filter.strip() or None

    return config
