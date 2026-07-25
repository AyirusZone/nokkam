"""TOML-backed app configuration with sane defaults.

Config lives at ~/.cad-tui/config.toml; a missing file just means defaults.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path


def default_app_dir() -> Path:
    return Path.home() / ".cad-tui"


@dataclass
class AppConfig:
    theme: str = "cad-dark"
    accent: str = "#0A84FF"  # Apple system blue as the single accent seed
    db_path: Path = field(default_factory=lambda: default_app_dir() / "data.db")
    app_dir: Path = field(default_factory=default_app_dir)


def load_config(config_path: Path | None = None) -> AppConfig:
    path = config_path or (default_app_dir() / "config.toml")
    if not path.exists():
        return AppConfig()

    with path.open("rb") as f:
        raw = tomllib.load(f)

    app_dir = default_app_dir()
    return AppConfig(
        theme=raw.get("theme", "cad-dark"),
        accent=raw.get("accent", "#0A84FF"),
        db_path=Path(raw["db_path"]).expanduser() if "db_path" in raw else app_dir / "data.db",
        app_dir=app_dir,
    )
