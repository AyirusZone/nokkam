from pathlib import Path
from unittest.mock import patch

from nokkam.app import NokkamApp
from nokkam.config import AppConfig
from nokkam.domain.models import Task
from nokkam.presentation.screens.home_screen import HomeScreen
from nokkam.presentation.screens.pomodoro_screen import BREAK_SECONDS, PomodoroScreen
from nokkam.presentation.widgets.app_header import AppHeader


def make_app(tmp_path: Path) -> NokkamApp:
    return NokkamApp(config=AppConfig(db_path=tmp_path / "data.db"))


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


async def test_running_timer_shows_in_header_and_clears_on_stop(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        app.task_service.add_task(Task(title="Focus work"))
        app.screen.refresh_all()
        await pilot.pause()
        header = app.screen.query_one(AppHeader)
        original_meta = header.meta

        await pilot.press("t")
        await pilot.pause()
        assert header.timer_text is not None
        assert "Focus work" in header.timer_text
        assert "⏱" in header.timer_text
        # the underlying screen meta (month/smart-filter label) is untouched
        # by the timer override — only what's rendered changes
        assert header.meta == original_meta

        await pilot.press("t")
        await pilot.pause()
        assert header.timer_text is None


async def test_pause_resume_and_stop_via_ui(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        task = app.task_service.add_task(Task(title="Focus work"))
        app.screen.refresh_all()
        await pilot.pause()
        header = app.screen.query_one(AppHeader)

        await pilot.press("t")
        await pilot.pause()
        assert app.time_tracking.active_task_id == task.id
        assert app.time_tracking.is_paused is False

        await pilot.press("p")
        await pilot.pause()
        assert app.time_tracking.is_paused is True
        assert app.time_tracking.active_task_id == task.id  # still active, just paused
        assert "⏸" in (header.timer_text or "")
        assert "paused" in (header.timer_text or "")

        await pilot.press("p")
        await pilot.pause()
        assert app.time_tracking.is_paused is False
        assert app.time_tracking.active_task_id == task.id
        assert "⏱" in (header.timer_text or "")

        # 't' still fully stops the timer, pause/resume cycles notwithstanding
        await pilot.press("t")
        await pilot.pause()
        assert app.time_tracking.active_task_id is None
        assert app.time_tracking.is_paused is False
        assert header.timer_text is None


async def test_pause_is_noop_with_no_active_timer(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("p")
        await pilot.pause()
        assert app.time_tracking.active_task_id is None
        assert app.time_tracking.is_paused is False


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
        with patch("nokkam.app.send_notification") as mock_send:
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
