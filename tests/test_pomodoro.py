from pathlib import Path
from unittest.mock import patch

from cad_tui.app import CadTuiApp
from cad_tui.config import AppConfig
from cad_tui.domain.models import Task
from cad_tui.presentation.screens.home_screen import HomeScreen
from cad_tui.presentation.screens.pomodoro_screen import BREAK_SECONDS, PomodoroScreen


def make_app(tmp_path: Path) -> CadTuiApp:
    return CadTuiApp(config=AppConfig(db_path=tmp_path / "data.db"))


async def test_toggle_timer_via_ui(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        task = app.task_service.add_task(Task(title="Focus work"))
        app.screen.refresh_all()
        await pilot.pause()

        await pilot.press("t")
        await pilot.pause()
        assert app.time_tracking.active_task_id == task.id

        await pilot.press("t")
        await pilot.pause()
        assert app.time_tracking.active_task_id is None


async def test_starting_timer_on_second_task_stops_first(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        t1 = app.task_service.add_task(Task(title="A"))
        t2 = app.task_service.add_task(Task(title="B"))
        app.screen.refresh_all()
        await pilot.pause()

        app.time_tracking.toggle(t1.id)
        app.time_tracking.toggle(t2.id)
        assert app.time_tracking.active_task_id == t2.id
        assert app.time_tracking.repo.active_for_task(t1.id) is None


async def test_open_pomodoro_via_key(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        await pilot.press("P")
        await pilot.pause()
        assert isinstance(app.screen, PomodoroScreen)


async def test_pomodoro_pause_and_reset(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        await app.push_screen(PomodoroScreen())
        await pilot.pause()
        screen = app.screen
        assert isinstance(screen, PomodoroScreen)
        start_remaining = screen.remaining

        screen.action_toggle_pause()
        assert screen.paused is True

        screen.remaining = 5
        screen.action_reset()
        assert screen.remaining == start_remaining
        assert screen.paused is False


async def test_pomodoro_session_completion_switches_to_break(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        await app.push_screen(PomodoroScreen())
        await pilot.pause()
        screen = app.screen
        screen.remaining = 1
        with patch("cad_tui.app.send_notification") as mock_send:
            screen._tick()
        mock_send.assert_called_once()
        assert screen.on_break is True
        assert screen.remaining == BREAK_SECONDS


async def test_pomodoro_paused_does_not_tick(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        await app.push_screen(PomodoroScreen())
        await pilot.pause()
        screen = app.screen
        screen.paused = True
        remaining_before = screen.remaining
        screen._tick()
        assert screen.remaining == remaining_before


async def test_pomodoro_close_returns_to_home(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        await app.push_screen(PomodoroScreen())
        await pilot.pause()
        app.screen.action_close()
        await pilot.pause()
        assert isinstance(app.screen, HomeScreen)
