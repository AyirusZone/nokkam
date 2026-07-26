"""Direct unit tests for DayCell/CalendarGrid rendering. The existing
test_calendar_mouse.py only covers click/selection behavior — none of the
cell's rendered content (task lines, private masking, icons, event lines,
overflow truncation) had a test anywhere in the suite."""

from datetime import date

from nokkam.domain.models import Event, Status, Task
from nokkam.presentation.widgets.calendar_grid import MAX_PREVIEW_ITEMS, CalendarGrid, DayCell


def make_task(**kwargs) -> Task:
    defaults = dict(title="Task", status=Status.OPEN, project_id=None, private=False)
    defaults.update(kwargs)
    return Task(**defaults)


def test_render_shows_bare_day_number_with_no_items() -> None:
    cell = DayCell(date(2026, 7, 26), tasks=[], project_colors={}, icon_overrides={})
    assert cell.render() == "[b]26[/b]"


def test_render_shows_task_marker_and_title() -> None:
    cell = DayCell(
        date(2026, 7, 26),
        tasks=[make_task(title="Write report")],
        project_colors={},
        icon_overrides={},
    )
    rendered = cell.render()
    assert "Write report" in rendered
    assert "[$accent]•[/]" in rendered


def test_render_uses_project_color_for_marker() -> None:
    task = make_task(title="Ship it", project_id=1)
    cell = DayCell(
        date(2026, 7, 26), tasks=[task], project_colors={1: "#00FF00"}, icon_overrides={}
    )
    assert "[#00FF00]•[/]" in cell.render()


def test_render_masks_private_task_title_and_suppresses_icon() -> None:
    task = make_task(title="Flight to Tokyo", private=True)
    cell = DayCell(date(2026, 7, 26), tasks=[task], project_colors={}, icon_overrides={})
    rendered = cell.render()
    assert "•••••" in rendered
    assert "Flight to Tokyo" not in rendered
    assert "✈" not in rendered


def test_render_shows_icon_for_matching_keyword() -> None:
    task = make_task(title="Book flight to Tokyo")
    cell = DayCell(date(2026, 7, 26), tasks=[task], project_colors={}, icon_overrides={})
    assert "✈" in cell.render()


def test_render_marks_done_task_with_checkmark_and_strikethrough() -> None:
    task = make_task(title="Finished thing", status=Status.DONE)
    cell = DayCell(date(2026, 7, 26), tasks=[task], project_colors={}, icon_overrides={})
    rendered = cell.render()
    assert "[$success]✓[/]" in rendered
    assert "[dim strike]" in rendered


def test_render_shows_event_with_distinct_marker() -> None:
    event = Event(title="Team sync", start_at="2026-07-26 10:00")
    cell = DayCell(
        date(2026, 7, 26), tasks=[], project_colors={}, icon_overrides={}, events=[event]
    )
    rendered = cell.render()
    assert "[$secondary]▸[/] Team sync" in rendered


def test_render_truncates_overflow_across_tasks_and_events() -> None:
    tasks = [make_task(title=f"Task {i}") for i in range(3)]
    events = [Event(title="Event A", start_at="2026-07-26 09:00")]
    cell = DayCell(
        date(2026, 7, 26), tasks=tasks, project_colors={}, icon_overrides={}, events=events
    )
    rendered = cell.render()
    lines = rendered.split("\n")

    # day number + MAX_PREVIEW_ITEMS shown + one "+N more" line
    assert len(lines) == 1 + MAX_PREVIEW_ITEMS + 1
    total_items = len(tasks) + len(events)
    assert f"+{total_items - MAX_PREVIEW_ITEMS} more" in lines[-1]


async def test_render_month_assigns_today_weekend_and_other_month_classes() -> None:
    grid = CalendarGrid()
    grid.focus_date = date(2026, 7, 15)
    from textual.app import App, ComposeResult

    class Harness(App):
        def compose(self) -> ComposeResult:
            yield grid

    app = Harness()
    async with app.run_test():
        cells = list(app.query(DayCell))
        first_day = next(c for c in cells if c.day == date(2026, 7, 1))
        other_month = next(c for c in cells if c.day.month != 7)
        weekend = next(c for c in cells if c.day.weekday() in (5, 6) and c.day.month == 7)

        assert "other-month" not in first_day.classes
        assert "other-month" in other_month.classes
        assert "weekend" in weekend.classes
