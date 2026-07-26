"""HelpModal had no dedicated test anywhere in the suite."""

from pathlib import Path

from nokkam.app import NokkamApp
from nokkam.config import AppConfig
from nokkam.presentation.screens.help import HelpModal


def make_app(tmp_path: Path) -> NokkamApp:
    return NokkamApp(config=AppConfig(db_path=tmp_path / "data.db"))


async def test_help_modal_lists_current_keybindings(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        await app.push_screen(HelpModal())
        await pilot.pause()

        text = str(app.screen.query_one("Static").render())
        assert "sync configured .ics calendars" in text
        assert "pause/resume the running timer" in text


async def test_help_modal_closes_on_escape(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        await app.push_screen(HelpModal())
        await pilot.pause()
        assert isinstance(app.screen, HelpModal)

        await pilot.press("escape")
        await pilot.pause()

        assert not isinstance(app.screen, HelpModal)
