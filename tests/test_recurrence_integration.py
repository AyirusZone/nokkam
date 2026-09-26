from datetime import date
from pathlib import Path

import pytest
from textual.widgets import Input

from nokkam.app import NokkamApp
from nokkam.cli import run_cli
from nokkam.config import AppConfig
from nokkam.data.db import connect
from nokkam.data.migrations import MIGRATIONS, apply_migrations
from nokkam.data.repositories.recurrence_repository import RecurrenceRepository
from nokkam.data.repositories.task_repository import TaskRepository
from nokkam.domain.models import Task
from nokkam.domain.nl_date_parser import parse_quick_text
from nokkam.domain.recurrence import RecurrenceRule, format_recurrence
from nokkam.presentation.screens.task_form import TaskFormModal
from nokkam.services.task_service import TaskService
from nokkam.services.undo import UndoStack

MON = date(2026, 7, 27)


def make_service(tmp_path: Path) -> tuple[TaskService, RecurrenceRepository]:
    conn = connect(tmp_path / "data.db")
    apply_migrations(conn)
    recurrence_repo = RecurrenceRepository(conn)
    return TaskService(TaskRepository(conn), UndoStack(), recurrence_repo), recurrence_repo


# ---- storage ----


def test_repository_round_trips_every_field(tmp_path: Path) -> None:
    _, repo = make_service(tmp_path)
    rules = [
        RecurrenceRule(rule="daily"),
        RecurrenceRule(rule="weekly", interval=2, weekdays=(0, 3), until="2026-12-31", count=8),
        RecurrenceRule(rule="monthly_nth", weekdays=(4,), nth=-1),
        RecurrenceRule(rule="yearly", interval=2),
    ]
    for rule in rules:
        assert repo.get(repo.create(rule)) == rule


def test_upgrading_a_v4_database_keeps_existing_recurrences(tmp_path: Path) -> None:
    conn = connect(tmp_path / "old.db")
    for version, sql in MIGRATIONS:
        if version <= 4:
            with conn:
                conn.executescript(sql)
                conn.execute(f"PRAGMA user_version = {version}")
    conn.execute(
        "INSERT INTO recurrence (rule, interval, until, count) VALUES ('weekly', 2, NULL, 5)"
    )
    conn.commit()

    assert apply_migrations(conn) == 5

    old = RecurrenceRepository(conn).get(1)
    assert old == RecurrenceRule(rule="weekly", interval=2, count=5)
    assert old.weekdays == () and old.nth is None
    conn.close()


# ---- completing a task spawns the right next one ----


@pytest.mark.parametrize(
    ("rule", "due", "expected_next"),
    [
        (RecurrenceRule(rule="weekly", weekdays=(0, 1, 2, 3, 4)), "2026-07-31", "2026-08-03"),
        (RecurrenceRule(rule="weekly", weekdays=(0, 2, 4)), "2026-07-27", "2026-07-29"),
        (RecurrenceRule(rule="weekly", interval=2, weekdays=(0,)), "2026-07-27", "2026-08-10"),
        (RecurrenceRule(rule="monthly_nth", weekdays=(1,), nth=1), "2026-07-07", "2026-08-04"),
        (RecurrenceRule(rule="monthly_nth", weekdays=(4,), nth=-1), "2026-07-31", "2026-08-28"),
        (RecurrenceRule(rule="yearly"), "2026-07-27", "2027-07-27"),
        (RecurrenceRule(rule="daily", interval=3), "2026-07-27", "2026-07-30"),
    ],
)
def test_completing_spawns_next_occurrence(
    tmp_path: Path, rule: RecurrenceRule, due: str, expected_next: str
) -> None:
    service, repo = make_service(tmp_path)
    task = service.add_task(Task(title="t", due_date=due, recurrence_id=repo.create(rule)))

    service.toggle_complete(task.id)

    spawned = [t for t in service.list_tasks() if t.id != task.id]
    assert [t.due_date for t in spawned] == [expected_next]
    assert spawned[0].recurrence_id == task.recurrence_id


def test_count_limits_a_weekday_rule(tmp_path: Path) -> None:
    service, repo = make_service(tmp_path)
    rule_id = repo.create(RecurrenceRule(rule="weekly", weekdays=(0, 2), count=3))
    task = service.add_task(Task(title="t", due_date="2026-07-27", recurrence_id=rule_id))

    for _ in range(5):
        open_tasks = [t for t in service.list_tasks() if t.status == "open"]
        if not open_tasks:
            break
        service.toggle_complete(open_tasks[0].id)

    assert len(service.list_tasks()) == 3
    assert task.id in [t.id for t in service.list_tasks()]


def test_until_ends_a_series_and_undo_removes_the_spawned_task(tmp_path: Path) -> None:
    service, repo = make_service(tmp_path)
    rule_id = repo.create(RecurrenceRule(rule="weekly", weekdays=(0, 2), until="2026-07-29"))
    task = service.add_task(Task(title="t", due_date="2026-07-27", recurrence_id=rule_id))

    service.toggle_complete(task.id)
    (wed,) = [t for t in service.list_tasks() if t.id != task.id]
    assert wed.due_date == "2026-07-29"

    service.undo_last()
    assert [t.id for t in service.list_tasks()] == [task.id]

    service.toggle_complete(task.id)
    (wed,) = [t for t in service.list_tasks() if t.id != task.id]
    service.toggle_complete(wed.id)  # next would be Mon 08-03, past `until`
    assert len(service.list_tasks()) == 2


# ---- quick add parsing ----


def parse(text: str):
    return parse_quick_text(text, today=MON)


def test_quick_add_weekday_pattern_with_time() -> None:
    result = parse("Standup every weekday 9:30")
    assert result.title == "Standup"
    assert result.due_time == "09:30"
    assert result.due_date == "2026-07-27"  # Monday fits, so start today
    assert format_recurrence(result.recurrence) == "every weekday"


def test_quick_add_starts_a_weekday_pattern_on_the_next_matching_day() -> None:
    result = parse_quick_text("Standup every weekday", today=date(2026, 8, 1))  # a Saturday
    assert result.due_date == "2026-08-03"


def test_quick_add_named_day_sets_the_due_date_and_the_recurrence() -> None:
    result = parse("Team sync every fri 3pm")
    assert (result.title, result.due_date, result.due_time) == ("Team sync", "2026-07-31", "15:00")
    assert result.recurrence == RecurrenceRule(rule="weekly", weekdays=(4,))


def test_quick_add_explicit_date_wins_over_first_occurrence() -> None:
    result = parse("Water plants every 2 days tmrw")
    assert result.due_date == "2026-07-28"
    assert result.recurrence == RecurrenceRule(rule="daily", interval=2)


@pytest.mark.parametrize(
    ("text", "title", "expected"),
    [
        ("Pay rent every month", "Pay rent", RecurrenceRule(rule="monthly")),
        (
            "Review every 2 weeks on mon,thu",
            "Review",
            RecurrenceRule(rule="weekly", interval=2, weekdays=(0, 3)),
        ),
        (
            "Book club every first tue",
            "Book club",
            RecurrenceRule(rule="monthly_nth", weekdays=(1,), nth=1),
        ),
        (
            "Trash every last friday of the month",
            "Trash",
            RecurrenceRule(rule="monthly_nth", weekdays=(4,), nth=-1),
        ),
        ("Renew domain every year", "Renew domain", RecurrenceRule(rule="yearly")),
        ("Stretch every day for 5 times", "Stretch", RecurrenceRule(rule="daily", count=5)),
        (
            "Report every week until 2026-12-31",
            "Report",
            RecurrenceRule(rule="weekly", until="2026-12-31"),
        ),
    ],
)
def test_quick_add_recurrence_phrases(text: str, title: str, expected: RecurrenceRule) -> None:
    result = parse(text)
    assert result.title == title
    assert result.recurrence == expected


@pytest.mark.parametrize(
    "text",
    ["Weekly report", "Every good boy deserves fudge", "Call daily", "Buy milk tmrw 3pm", "every"],
)
def test_quick_add_does_not_invent_recurrence(text: str) -> None:
    assert parse(text).recurrence is None


def test_quick_add_without_recurrence_is_unchanged() -> None:
    result = parse("Buy milk tmrw 3pm")
    assert (result.title, result.due_date, result.due_time) == ("Buy milk", "2026-07-28", "15:00")


# ---- CLI ----


def test_cli_add_creates_a_recurring_task(tmp_path: Path, capsys) -> None:
    config = AppConfig(db_path=tmp_path / "data.db")
    assert run_cli(["add", "Water plants every 2 days"], config=config) == 0
    assert "↻ every 2 days" in capsys.readouterr().out

    conn = connect(config.db_path)
    (task,) = TaskRepository(conn).list()
    rule = RecurrenceRepository(conn).get(task.recurrence_id)
    conn.close()
    assert task.title == "Water plants"
    assert rule == RecurrenceRule(rule="daily", interval=2)


# ---- the form and quick-add dialog ----


def make_app(tmp_path: Path) -> NokkamApp:
    return NokkamApp(config=AppConfig(db_path=tmp_path / "data.db"))


async def fill_and_save(app: NokkamApp, pilot, title: str, repeats: str) -> None:
    await pilot.press("a")
    await pilot.pause()
    assert isinstance(app.screen, TaskFormModal)
    app.screen.query_one("#title", Input).value = title
    app.screen.query_one("#recurrence", Input).value = repeats
    await pilot.click("#save")
    await pilot.pause()


async def test_form_saves_a_rich_recurrence(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        await fill_and_save(app, pilot, "Gym", "every mon,wed,fri until 2026-12-31")

        (task,) = app.task_service.list_tasks()
        assert app.recurrence_repo.get(task.recurrence_id) == RecurrenceRule(
            rule="weekly", weekdays=(0, 2, 4), until="2026-12-31"
        )


async def test_form_rejects_bad_repeats_and_stays_open(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        await fill_and_save(app, pilot, "Gym", "every blorp")

        assert isinstance(app.screen, TaskFormModal)  # still open, nothing lost
        assert app.task_service.list_tasks() == []
        assert any(
            n.severity == "error" and "Couldn't read" in n.message for n in app._notifications
        )
        assert app.screen.query_one("#title", Input).value == "Gym"


async def test_blank_repeats_means_no_recurrence(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        await fill_and_save(app, pilot, "One-off", "")
        (task,) = app.task_service.list_tasks()
        assert task.recurrence_id is None


async def test_edit_form_shows_the_rule_as_text_and_keeps_it_when_unchanged(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        await fill_and_save(app, pilot, "Book club", "every first tue")
        (task,) = app.task_service.list_tasks()

        app.screen.select_task_by_id(task.id)
        await pilot.pause()
        await pilot.press("e")
        await pilot.pause()
        assert app.screen.query_one("#recurrence", Input).value == "every first tue"

        await pilot.click("#save")
        await pilot.pause()
        (after,) = app.task_service.list_tasks()
        assert after.recurrence_id == task.recurrence_id  # same row, not a duplicate


async def test_editing_the_rule_creates_a_new_one_and_clearing_removes_it(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        await fill_and_save(app, pilot, "Gym", "every day")
        (task,) = app.task_service.list_tasks()

        app.screen.select_task_by_id(task.id)
        await pilot.pause()
        await pilot.press("e")
        await pilot.pause()
        app.screen.query_one("#recurrence", Input).value = "every weekday"
        await pilot.click("#save")
        await pilot.pause()
        (changed,) = app.task_service.list_tasks()
        assert changed.recurrence_id != task.recurrence_id
        assert app.recurrence_repo.get(changed.recurrence_id).weekdays == (0, 1, 2, 3, 4)

        await pilot.press("e")
        await pilot.pause()
        app.screen.query_one("#recurrence", Input).value = "none"
        await pilot.click("#save")
        await pilot.pause()
        (cleared,) = app.task_service.list_tasks()
        assert cleared.recurrence_id is None


async def test_quick_add_dialog_creates_a_recurring_task(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("A")
        await pilot.pause()
        app.screen.query_one("#quick-input", Input).value = "Standup every weekday 9:30"
        await pilot.press("enter")
        await pilot.pause()

        (task,) = app.task_service.list_tasks()
        assert (task.title, task.due_time) == ("Standup", "09:30")
        assert task.due_date is not None
        assert app.recurrence_repo.get(task.recurrence_id).weekdays == (0, 1, 2, 3, 4)
