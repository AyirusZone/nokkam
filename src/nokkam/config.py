"""TOML-backed app configuration with sane defaults.

Config lives at ~/.nokkam/config.toml; a missing file just means defaults.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_ACCENT = "#FF6B4A"  # signature warm vermillion — see presentation/theme.py


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


def load_config(config_path: Path | None = None) -> AppConfig:
    path = config_path or (default_app_dir() / "config.toml")
    if not path.exists():
        return AppConfig()

    with path.open("rb") as f:
        raw = tomllib.load(f)

    app_dir = default_app_dir()
    return AppConfig(
        theme=raw.get("theme", "nokkam-dark"),
        accent=raw.get("accent", DEFAULT_ACCENT),
        db_path=Path(raw["db_path"]).expanduser() if "db_path" in raw else app_dir / "data.db",
        app_dir=app_dir,
        icons=raw.get("icons", {}),
        ics_sources=raw.get("ics_sources", []),
    )
