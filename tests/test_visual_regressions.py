"""Guards for two real bugs the build-loop's pytest run never caught —
both only visible by inspecting actual rendered pixels/colors, not text
presence: (1) border + exact height silently zeroing out a widget's
content row, (2) bare `[accent]`-style markup tags not resolving to
theme colors (needs the `$` prefix)."""

import re
from pathlib import Path

from cad_tui.app import CadTuiApp
from cad_tui.config import AppConfig
from cad_tui.domain.models import Task
from cad_tui.presentation.widgets.app_header import AppHeader


def make_app(tmp_path: Path) -> CadTuiApp:
    return CadTuiApp(config=AppConfig(db_path=tmp_path / "data.db"))


def rendered_texts(app: CadTuiApp) -> list[str]:
    svg = app.export_screenshot()
    return re.findall(r"<text[^>]*>([^<]*)</text>", svg)


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))


def assert_close_color(actual_hex: str, expected_hex: str, tolerance: int = 3) -> None:
    """Textual's internal color pipeline can round by a unit or two —
    compare channels within a small tolerance rather than exact hex."""
    actual = _hex_to_rgb(actual_hex)
    expected = _hex_to_rgb(expected_hex)
    diffs = [abs(a - e) for a, e in zip(actual, expected, strict=True)]
    assert all(d <= tolerance for d in diffs), f"{actual_hex} too far from {expected_hex}"


async def test_app_header_has_nonzero_content_height(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        header = app.screen.query_one(AppHeader)
        assert header.content_region.height > 0


async def test_app_header_renders_wordmark_in_accent_color(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        title = app.screen.query_one("#app-header-title")
        strip = title.render_line(0)
        segments = [s for s in strip if "cad" in s.text]
        assert segments, "wordmark not found in rendered header"
        theme = app.get_theme(app.theme)
        rendered_hex = segments[0].style.color.get_truecolor().hex
        assert_close_color(rendered_hex, theme.accent)


async def test_footer_has_nonzero_content_height(tmp_path: Path) -> None:
    from textual.widgets import Footer

    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        footer = app.screen.query_one(Footer)
        assert footer.content_region.height > 0


async def test_footer_renders_keybind_hints(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        joined = " ".join(rendered_texts(app))
        assert "Add" in joined


async def test_header_and_footer_visible_in_full_render(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        joined = " ".join(rendered_texts(app))
        assert "cad" in joined
        assert "home" in joined


async def test_task_row_badge_uses_theme_color_not_default_foreground(tmp_path: Path) -> None:
    from cad_tui.domain.recurrence import RecurrenceRule
    from cad_tui.presentation.screens.task_list import TaskRow

    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        rid = app.recurrence_repo.create(RecurrenceRule(rule="daily"))
        app.task_service.add_task(Task(title="Recurring", recurrence_id=rid))
        app.screen.refresh_all()
        await pilot.pause()

        row = next(r for r in app.screen.query(TaskRow) if r.model.title == "Recurring")
        static = row.query_one("Static")
        strip = static.render_line(0)
        recurring_segments = [s for s in strip if "↻" in s.text]
        assert recurring_segments
        theme = app.get_theme(app.theme)
        rendered_hex = recurring_segments[0].style.color.get_truecolor().hex
        assert _hex_to_rgb(rendered_hex) != _hex_to_rgb(theme.foreground)
        assert_close_color(rendered_hex, theme.secondary)
