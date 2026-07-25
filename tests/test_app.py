from pathlib import Path

import pytest

from cad_tui.app import CadTuiApp
from cad_tui.config import AppConfig


def make_app(tmp_path: Path) -> CadTuiApp:
    return CadTuiApp(config=AppConfig(db_path=tmp_path / "data.db"))


async def test_app_launches_and_runs_migrations(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test():
        assert app.screen is not None
        assert app.db is not None
        tables = {
            row["name"]
            for row in app.db.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        assert "task" in tables


async def test_theme_toggle(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        start_theme = app.theme
        await pilot.press("ctrl+t")
        assert app.theme != start_theme
        await pilot.press("ctrl+t")
        assert app.theme == start_theme
