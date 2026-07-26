from datetime import date, timedelta
from pathlib import Path

from textual.widgets import Input, TabbedContent

from nokkam.app import NokkamApp
from nokkam.config import AppConfig
from nokkam.domain.models import Event, Task
from nokkam.presentation.screens.home_screen import EventRow, HomeScreen
from nokkam.presentation.screens.task_list import TaskRow
from nokkam.presentation.widgets.calendar_grid import DayCell


def make_app(tmp_path: Path) -> NokkamApp:
    return NokkamApp(config=AppConfig(db_path=tmp_path / "data.db"))


async def test_task_due_today_shows_on_correct_day_cell(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        today = date.today()
        app.task_service.add_task(Task(title="Due today", due_date=today.isoformat()))
        app.screen.refresh_all()
        await pilot.pause()

        day_cells = list(app.screen.query(DayCell))
        matching = [c for c in day_cells if c.day == today]
        assert len(matching) == 1
        assert len(matching[0].tasks) == 1
        assert "today" in matching[0].classes

        other_cells_same_month = [
            c for c in day_cells if c.day != today and c.day.month == today.month
        ]
        assert all(len(c.tasks) == 0 for c in other_cells_same_month)


async def test_day_pane_lists_only_tasks_for_selected_day(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        today = date.today()
        tomorrow = today + timedelta(days=1)
        app.task_service.add_task(Task(title="Today's task", due_date=today.isoformat()))
        app.task_service.add_task(Task(title="Tomorrow's task", due_date=tomorrow.isoformat()))
        app.screen.refresh_all()
        await pilot.pause()

        titles = [item.model.title for item in app.screen.day_list.children]
        assert titles == ["Today's task"]


async def test_calendar_nav_only_moves_when_calendar_focused(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        today = date.today()
        screen = app.screen
        await pilot.pause()

        # all_list has focus by default (on_mount) — nav_right should not move the calendar
        screen.action_nav_right()
        await pilot.pause()
        assert screen.calendar.focus_date == today

        screen.calendar.focus()
        await pilot.pause()
        screen.action_nav_right()
        await pilot.pause()
        assert screen.calendar.focus_date == today + timedelta(days=1)


async def test_jump_today_via_t_when_calendar_focused(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        today = date.today()
        screen = app.screen
        screen.calendar.focus()
        await pilot.pause()
        screen.action_next_month()
        await pilot.pause()
        assert screen.calendar.focus_date != today

        await pilot.press("t")
        await pilot.pause()
        assert screen.calendar.focus_date == today


async def test_t_toggles_timer_when_list_focused(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        task = app.task_service.add_task(Task(title="Focus work"))
        app.screen.refresh_all()
        await pilot.pause()
        app.screen.all_list.focus()
        await pilot.pause()

        await pilot.press("t")
        await pilot.pause()
        assert app.time_tracking.active_task_id == task.id


async def test_add_task_from_calendar_context_prefills_selected_day(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        screen = app.screen
        screen.calendar.focus()
        await pilot.pause()
        screen.action_nav_right()
        await pilot.pause()
        expected_due = screen.calendar.focus_date

        await pilot.press("a")
        await pilot.pause()
        due_input = app.screen.query_one("#due_date", Input)
        assert due_input.value == expected_due.isoformat()

        title_input = app.screen.query_one("#title", Input)
        title_input.value = "Prefilled task"
        await pilot.click("#save")
        await pilot.pause()

        tasks = app.task_service.list_tasks()
        assert len(tasks) == 1
        assert tasks[0].due_date == expected_due.isoformat()


async def test_add_task_from_all_list_context_leaves_due_date_blank(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        app.screen.all_list.focus()
        await pilot.pause()
        await pilot.press("a")
        await pilot.pause()
        due_input = app.screen.query_one("#due_date", Input)
        assert due_input.value == ""


async def test_delete_from_day_pane_removes_only_that_task(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        today = date.today()
        day_task = app.task_service.add_task(Task(title="Day task", due_date=today.isoformat()))
        other_task = app.task_service.add_task(Task(title="Other task"))
        app.screen.refresh_all()
        await pilot.pause()

        app.screen.day_list.focus()
        await pilot.pause()
        await pilot.press("d")
        await pilot.pause()

        remaining = {t.id for t in app.task_service.list_tasks()}
        assert day_task.id not in remaining
        assert other_task.id in remaining


async def test_tab_cycles_focus_across_all_panes(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        screen = app.screen
        await pilot.pause()
        seen = set()
        for _ in range(10):
            seen.add(type(screen.focused).__name__ if screen.focused is not None else None)
            await pilot.press("tab")
            await pilot.pause()
        assert "CalendarGrid" in seen
        assert "ListView" in seen


async def test_selecting_a_project_filters_all_list(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        screen = app.screen
        project_id = app.project_repo.get_or_create("Work")
        app.task_service.add_task(Task(title="Work task", project_id=project_id))
        app.task_service.add_task(Task(title="Other task"))
        screen.refresh_all()
        await pilot.pause()

        screen.projects_list.focus()
        await pilot.pause()
        await pilot.press("space")
        await pilot.pause()

        assert screen.selected_project_ids == {project_id}
        titles = [
            item.model.title for item in screen.all_list.children if isinstance(item, TaskRow)
        ]
        assert titles == ["Work task"]

        await pilot.press("space")
        await pilot.pause()
        assert screen.selected_project_ids == set()
        titles = sorted(
            item.model.title for item in screen.all_list.children if isinstance(item, TaskRow)
        )
        assert titles == ["Other task", "Work task"]


async def test_selecting_a_project_removes_unrelated_dates_from_calendar(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        screen = app.screen
        today = date.today()
        work = app.project_repo.get_or_create("Work")
        app.project_repo.get_or_create("Personal")
        app.task_service.add_task(
            Task(title="Work task", project_id=work, due_date=today.isoformat())
        )
        app.task_service.add_task(
            Task(title="Unrelated task", due_date=(today + timedelta(days=1)).isoformat())
        )
        screen.refresh_all()
        await pilot.pause()
        assert set(screen.calendar.tasks_by_date) == {
            today.isoformat(),
            (today + timedelta(days=1)).isoformat(),
        }

        screen.projects_list.focus()
        await pilot.pause()
        await pilot.press("space")
        await pilot.pause()

        # only the selected project's date remains on the calendar
        assert set(screen.calendar.tasks_by_date) == {today.isoformat()}

        await pilot.press("space")
        await pilot.pause()
        assert set(screen.calendar.tasks_by_date) == {
            today.isoformat(),
            (today + timedelta(days=1)).isoformat(),
        }


async def test_selecting_a_project_filters_todays_tasks(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        screen = app.screen
        today = date.today()
        work = app.project_repo.get_or_create("Work")
        app.project_repo.get_or_create("Personal")
        app.task_service.add_task(
            Task(title="Work task", project_id=work, due_date=today.isoformat())
        )
        app.task_service.add_task(Task(title="Unrelated task", due_date=today.isoformat()))
        screen.refresh_all()
        await pilot.pause()
        assert {i.model.title for i in screen.day_list.children} == {
            "Work task",
            "Unrelated task",
        }

        screen.projects_list.focus()
        await pilot.pause()
        await pilot.press("space")
        await pilot.pause()

        titles = [item.model.title for item in screen.day_list.children]
        assert titles == ["Work task"]


async def test_selecting_a_tag_removes_unrelated_dates_from_calendar(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        screen = app.screen
        today = date.today()
        tag_id = app.tag_repo.get_or_create("urgent")
        app.task_service.add_task(
            Task(title="Urgent task", tag_ids=[tag_id], due_date=today.isoformat())
        )
        app.task_service.add_task(
            Task(title="Unrelated task", due_date=(today + timedelta(days=1)).isoformat())
        )
        screen.refresh_all()
        await pilot.pause()

        screen.tags_list.focus()
        await pilot.pause()
        await pilot.press("space")
        await pilot.pause()

        assert set(screen.calendar.tasks_by_date) == {today.isoformat()}


async def test_selecting_a_tag_filters_all_list(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        screen = app.screen
        tag_id = app.tag_repo.get_or_create("urgent")
        app.task_service.add_task(Task(title="Urgent task", tag_ids=[tag_id]))
        app.task_service.add_task(Task(title="Other task"))
        screen.refresh_all()
        await pilot.pause()

        screen.tags_list.focus()
        await pilot.pause()
        await pilot.press("space")
        await pilot.pause()

        assert screen.selected_tag_ids == {tag_id}
        titles = [
            item.model.title for item in screen.all_list.children if isinstance(item, TaskRow)
        ]
        assert titles == ["Urgent task"]


async def test_add_project_from_projects_pane(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        screen = app.screen
        screen.projects_list.focus()
        await pilot.pause()

        await pilot.press("a")
        await pilot.pause()
        prompt_input = app.screen.query_one("#text-prompt-input", Input)
        prompt_input.value = "Personal"
        await pilot.press("enter")
        await pilot.pause()

        # the pane only lists projects attached to a task, so a freshly
        # created one stays hidden until something uses it
        assert list(screen.projects_list.children) == []

        project_id = app.project_repo.get_or_create("Personal")
        app.task_service.add_task(Task(title="Something", project_id=project_id))
        screen.refresh_all()
        await pilot.pause()

        names = [row.project.name for row in screen.projects_list.children]
        assert names == ["Personal"]


async def test_add_tag_from_tags_pane(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        screen = app.screen
        screen.tags_list.focus()
        await pilot.pause()

        await pilot.press("a")
        await pilot.pause()
        prompt_input = app.screen.query_one("#text-prompt-input", Input)
        prompt_input.value = "home"
        await pilot.press("enter")
        await pilot.pause()

        # same rule for tags: hidden until attached to a task
        assert list(screen.tags_list.children) == []

        tag_id = app.tag_repo.get_or_create("home")
        app.task_service.add_task(Task(title="Something", tag_ids=[tag_id]))
        screen.refresh_all()
        await pilot.pause()

        names = [row.tag.name for row in screen.tags_list.children]
        assert names == ["home"]


async def test_projects_and_tags_panes_only_list_attached_ones(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        screen = app.screen
        used_project = app.project_repo.get_or_create("Used")
        app.project_repo.get_or_create("Unused")
        used_tag = app.tag_repo.get_or_create("used-tag")
        app.tag_repo.get_or_create("unused-tag")
        app.task_service.add_task(
            Task(title="Attached", project_id=used_project, tag_ids=[used_tag])
        )
        screen.refresh_all()
        await pilot.pause()

        project_names = [row.project.name for row in screen.projects_list.children]
        tag_names = [row.tag.name for row in screen.tags_list.children]
        assert project_names == ["Used"]
        assert tag_names == ["used-tag"]


async def test_projects_tags_and_all_tasks_live_in_one_tabbed_pane(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        screen = app.screen
        await pilot.pause()

        tabbed = screen.query_one(TabbedContent)
        tab_ids = [pane.id for pane in tabbed.query("TabPane")]
        assert tab_ids == ["projects-tab", "tags-tab", "all-tasks-tab"]
        # each list lives inside the tabbed pane rather than a separate
        # stacked section
        assert screen.projects_list in tabbed.query("ListView")
        assert screen.tags_list in tabbed.query("ListView")
        assert screen.all_list in tabbed.query("ListView")


async def test_arrow_keys_switch_tabs_when_tab_bar_focused(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        screen = app.screen
        await pilot.pause()
        tabbed = screen.query_one(TabbedContent)
        assert tabbed.active == "all-tasks-tab"

        # Tab from calendar -> day-tasks -> the tab bar itself
        screen.calendar.focus()
        await pilot.pause()
        await pilot.press("tab", "tab")
        await pilot.pause()

        await pilot.press("left")
        await pilot.pause()
        assert tabbed.active == "tags-tab"

        await pilot.press("left")
        await pilot.pause()
        assert tabbed.active == "projects-tab"


async def test_calendar_shows_synced_ics_events(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        today = date.today()
        calendar_id = app.event_repo.get_or_create_calendar("Work calendar")
        app.event_repo.replace_events(
            calendar_id,
            [Event(title="Conference", start_at=today.isoformat(), all_day=True, uid="ev-1")],
        )
        app.screen.refresh_all()
        await pilot.pause()

        cell = next(c for c in app.screen.query(DayCell) if c.day == today)
        assert len(cell.events) == 1
        assert cell.events[0].title == "Conference"


async def test_day_pane_shows_ics_events_for_selected_day(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        today = date.today()
        calendar_id = app.event_repo.get_or_create_calendar("Work calendar")
        app.event_repo.replace_events(
            calendar_id,
            [
                Event(
                    title="Team offsite",
                    start_at=f"{today.isoformat()} 09:00",
                    all_day=False,
                    uid="ev-2",
                )
            ],
        )
        app.screen.refresh_all()
        await pilot.pause()

        event_rows = [i for i in app.screen.day_list.children if isinstance(i, EventRow)]
        assert len(event_rows) == 1
        assert event_rows[0].event.title == "Team offsite"


async def test_sync_calendars_action_calls_app_sync(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        app.ics_service.sources = ["/fake/path.ics"]
        called = False

        def fake_sync() -> None:
            nonlocal called
            called = True

        app.sync_ics = fake_sync  # type: ignore[method-assign]
        await pilot.press("R")
        await pilot.pause()
        assert called


async def test_sync_calendars_warns_when_no_sources_configured(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        assert app.ics_service.sources == []
        await pilot.press("R")
        await pilot.pause()
        # no exception, no crash — just a notify(); the app is still alive
        assert isinstance(app.screen, HomeScreen)
