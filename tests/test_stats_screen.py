"""StatsScreen (presentation) had zero coverage — only the underlying
stats_service functions were tested, never the screen that renders them."""

from pathlib import Path

from nokkam.app import NokkamApp
from nokkam.config import AppConfig
from nokkam.domain.models import Status, Task
from nokkam.presentation.screens.stats_screen import StatsScreen


def make_app(tmp_path: Path) -> NokkamApp:
    return NokkamApp(config=AppConfig(db_path=tmp_path / "data.db"))


async def test_stats_screen_renders_completion_and_streak(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        app.task_service.add_task(Task(title="Open one"))
        app.task_service.add_task(Task(title="Done one", status=Status.DONE))
        await pilot.pause()

        await app.push_screen(StatsScreen())
        await pilot.pause()

        text = str(app.screen.query_one("#stats-body").render())
        assert "open tasks" in text
        assert "done tasks" in text
        assert "completion" in text
        assert "current streak" in text


async def test_stats_screen_back_action_pops_screen(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        await app.push_screen(StatsScreen())
        await pilot.pause()
        assert isinstance(app.screen, StatsScreen)

        app.screen.action_back()
        await pilot.pause()

        assert not isinstance(app.screen, StatsScreen)
