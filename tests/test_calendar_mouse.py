from datetime import date
from pathlib import Path

from cad_tui.app import CadTuiApp
from cad_tui.config import AppConfig
from cad_tui.presentation.screens.calendar_screen import CalendarScreen
from cad_tui.presentation.widgets.calendar_grid import DayCell


def make_app(tmp_path: Path) -> CadTuiApp:
    return CadTuiApp(config=AppConfig(db_path=tmp_path / "data.db"))


async def test_clicking_day_cell_selects_it(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        await app.push_screen(CalendarScreen())
        await pilot.pause()
        screen = app.screen
        assert isinstance(screen, CalendarScreen)

        today = date.today()
        candidates = [c for c in screen.query(DayCell) if c.day.month == today.month and c.day != today]
        assert candidates
        target_cell = candidates[0]

        target_cell.post_message(DayCell.Selected(target_cell.day))
        await pilot.pause()

        assert screen.calendar.focus_date == target_cell.day


async def test_clicking_other_month_cell_switches_month(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        await app.push_screen(CalendarScreen())
        await pilot.pause()
        screen = app.screen

        other_month_cells = [c for c in screen.query(DayCell) if "other-month" in c.classes]
        assert other_month_cells
        cell = other_month_cells[0]

        cell.post_message(DayCell.Selected(cell.day))
        await pilot.pause()

        assert screen.calendar.focus_date == cell.day
        assert screen.calendar.focus_date.month == cell.day.month


async def test_click_event_posts_selected_message(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        await app.push_screen(CalendarScreen())
        await pilot.pause()
        screen = app.screen

        today = date.today()
        today_cell = next(c for c in screen.query(DayCell) if c.day == today)
        other_cell = next(
            c for c in screen.query(DayCell) if c.day.month == today.month and c.day != today
        )
        assert "selected" in today_cell.classes

        await pilot.click(other_cell)
        await pilot.pause()

        assert screen.calendar.focus_date == other_cell.day
