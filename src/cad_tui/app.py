"""cad-tui entrypoint. Phase 1: scaffold, migrations, theme toggle."""

from __future__ import annotations

import sqlite3

from textual.app import App

from cad_tui.config import AppConfig, load_config
from cad_tui.data.db import connect
from cad_tui.data.migrations import apply_migrations
from cad_tui.presentation.screens.home import HomeScreen
from cad_tui.presentation.theme import THEMES


class CadTuiApp(App):
    CSS_PATH = "presentation/styles/base.tcss"
    BINDINGS = [
        ("ctrl+t", "toggle_theme", "Toggle theme"),
        ("q", "quit", "Quit"),
    ]

    def __init__(self, config: AppConfig | None = None) -> None:
        super().__init__()
        self.config = config or load_config()
        self.db: sqlite3.Connection | None = None

    def on_mount(self) -> None:
        for theme in THEMES:
            self.register_theme(theme)
        self.theme = self.config.theme

        self.db = connect(self.config.db_path)
        apply_migrations(self.db)

        self.push_screen(HomeScreen())

    def on_unmount(self) -> None:
        if self.db is not None:
            self.db.close()

    def action_toggle_theme(self) -> None:
        self.theme = "cad-light" if self.theme == "cad-dark" else "cad-dark"


def main() -> None:
    CadTuiApp().run()


if __name__ == "__main__":
    main()
