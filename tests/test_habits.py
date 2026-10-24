from datetime import date, timedelta
from pathlib import Path

import pytest
from textual.content import Content

from nokkam.app import NokkamApp
from nokkam.config import AppConfig
from nokkam.domain.habits import (
    LATE,
    ON_TIME,
    OVERDUE,
    PENDING,
    Occurrence,
    classify,
    compute_streaks,
)
from nokkam.domain.models import Task
from nokkam.domain.recurrence import RecurrenceRule
from nokkam.presentation.screens.habits_screen import EMPTY, HabitsScreen, render_habits
from nokkam.services.habit_service import HISTORY_LENGTH, compute_habits

TODAY = date(2026, 7, 27)
T = TODAY.isoformat()


def occ(due: str | None, done: bool = True, completed: str | None = None) -> Occurrence:
    return Occurrence(due_date=due, done=done, completed_on=completed if done else None)


# ---- classify ----


@pytest.mark.parametrize(
    ("occurrence", "state"),
    [
        (occ("2026-07-20", completed="2026-07-20"), ON_TIME),
        (occ("2026-07-20", completed="2026-07-18"), ON_TIME),  # early is fine
        (occ("2026-07-20", completed="2026-07-21"), LATE),
        (occ(None, completed="2026-07-21"), ON_TIME),  # no due date: nothing to be late for
        (occ("2026-07-20", completed=None), ON_TIME),  # imported: no completion date
        (occ("2026-07-27", done=False), PENDING),  # due today is not yet missed
        (occ("2026-08-01", done=False), PENDING),
        (occ("2026-07-26", done=False), OVERDUE),
        (occ(None, done=False), PENDING),
    ],
)
def test_classify(occurrence: Occurrence, state: str) -> None:
    assert classify(occurrence, T) == state


# ---- streaks ----


def test_no_occurrences_means_no_streak() -> None:
    assert compute_streaks([], T) == (0, 0)


def test_streak_counts_consecutive_on_time_completions() -> None:
    days = [f"2026-07-{d:02d}" for d in (23, 24, 25, 26)]
    history = [occ(d, completed=d) for d in days] + [occ(T, done=False)]
    assert compute_streaks(history, T) == (4, 4)


def test_a_late_completion_resets_the_current_streak_but_not_the_best() -> None:
    history = [
        occ("2026-07-20", completed="2026-07-20"),
        occ("2026-07-21", completed="2026-07-21"),
        occ("2026-07-22", completed="2026-07-22"),
        occ("2026-07-23", completed="2026-07-25"),  # late
        occ("2026-07-24", completed="2026-07-24"),
        occ("2026-07-25", completed="2026-07-25"),
    ]
    assert compute_streaks(history, T) == (2, 3)


def test_an_overdue_open_occurrence_breaks_the_streak() -> None:
    history = [occ("2026-07-24", completed="2026-07-24"), occ("2026-07-25", completed="2026-07-25")]
    assert compute_streaks([*history, occ("2026-07-26", done=False)], T) == (0, 2)


def test_an_upcoming_open_occurrence_neither_counts_nor_breaks() -> None:
    history = [occ("2026-07-25", completed="2026-07-25"), occ("2026-07-26", completed="2026-07-26")]
    assert compute_streaks([*history, occ(T, done=False)], T) == (2, 2)


def test_order_is_by_due_date_not_input_order() -> None:
    history = [
        occ("2026-07-26", completed="2026-07-26"),
        occ("2026-07-24", completed="2026-07-24"),
        occ("2026-07-25", completed="2026-07-25"),
    ]
    assert compute_streaks(history, T) == (3, 3)


# ---- service ----


def make_app(tmp_path: Path) -> NokkamApp:
    return NokkamApp(config=AppConfig(db_path=tmp_path / "data.db"))


def seed(app: NokkamApp, title: str, rule: RecurrenceRule, history, project_id=None) -> int:
    """history: (due ISO, completed ISO or None) oldest first."""
    rid = app.recurrence_repo.create(rule)
    for due, completed in history:
        task = app.task_service.add_task(
            Task(title=title, due_date=due, recurrence_id=rid, project_id=project_id)
        )
        if completed:
            with app.db:
                app.db.execute(
                    "UPDATE task SET status='done', completed_at=? WHERE id=?",
                    (f"{completed} 20:00:00", task.id),
                )
    return rid


def habits(app: NokkamApp):
    return compute_habits(app.task_service, app.recurrence_repo, app.project_repo, today=TODAY)


async def test_service_builds_a_habit_per_series(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test():
        work = app.project_repo.get_or_create("Work")
        seed(
            app,
            "Gym",
            RecurrenceRule(rule="daily"),
            [("2026-07-25", "2026-07-25"), ("2026-07-26", "2026-07-27"), (T, None)],
            project_id=work,
        )
        app.task_service.add_task(Task(title="Not a habit"))

        (gym,) = habits(app)
        assert (gym.title, gym.project_name, gym.rule_text) == ("Gym", "Work", "every day")
        assert (gym.total, gym.done, gym.on_time) == (3, 2, 1)
        assert gym.on_time_rate == 0.5
        assert (gym.current_streak, gym.best_streak) == (0, 1)  # the 26th was ticked late
        assert gym.history == [ON_TIME, LATE, PENDING]
        assert gym.active


async def test_history_keeps_only_the_last_ten(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test():
        days = [(TODAY - timedelta(days=n)).isoformat() for n in range(14, 0, -1)]
        seed(app, "Daily", RecurrenceRule(rule="daily"), [(d, d) for d in days])
        (habit,) = habits(app)
        assert len(habit.history) == HISTORY_LENGTH
        assert habit.total == 14 and habit.current_streak == 14


async def test_ended_series_sort_last_and_active_by_streak(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test():
        d = [(TODAY - timedelta(days=n)).isoformat() for n in (3, 2, 1)]
        seed(app, "Ended", RecurrenceRule(rule="daily"), [(x, x) for x in d])  # no open one
        seed(app, "Short", RecurrenceRule(rule="daily"), [(d[2], d[2]), (T, None)])
        seed(app, "Long", RecurrenceRule(rule="daily"), [(x, x) for x in d] + [(T, None)])

        assert [(h.title, h.active) for h in habits(app)] == [
            ("Long", True),
            ("Short", True),
            ("Ended", False),
        ]


async def test_latest_title_wins_when_a_habit_is_renamed(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test():
        rid = seed(app, "Old name", RecurrenceRule(rule="daily"), [("2026-07-26", "2026-07-26")])
        app.task_service.add_task(Task(title="New name", due_date=T, recurrence_id=rid))
        (habit,) = habits(app)
        assert habit.title == "New name"


async def test_real_completions_build_a_streak_and_survive_a_rule_edit(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        rid = app.recurrence_repo.create(RecurrenceRule(rule="daily"))
        task = app.task_service.add_task(
            Task(title="Stretch", due_date=date.today().isoformat(), recurrence_id=rid)
        )
        for _ in range(3):  # each completion (today, so on time) spawns the next
            open_task = next(t for t in app.task_service.list_tasks() if t.status == "open")
            app.task_service.toggle_complete(open_task.id)
        today = date.today()
        assert (
            compute_habits(app.task_service, app.recurrence_repo, app.project_repo, today)[
                0
            ].current_streak
            == 3
        )

        # Editing the rule through the form must keep the same series.
        app.screen.refresh_all()
        await pilot.pause()
        open_task = next(t for t in app.task_service.list_tasks() if t.status == "open")
        app.screen.select_task_by_id(open_task.id)
        await pilot.pause()
        await pilot.press("e")
        await pilot.pause()
        from textual.widgets import Input

        app.screen.query_one("#recurrence", Input).value = "every weekday"
        await pilot.click("#save")
        await pilot.pause()

        (habit,) = compute_habits(app.task_service, app.recurrence_repo, app.project_repo, today)
        assert habit.rule_text == "every weekday"
        assert habit.current_streak == 3  # history followed the edit
        assert task.id in [t.id for t in app.task_service.list_tasks()]
        assert len({t.recurrence_id for t in app.task_service.list_tasks()}) == 1


# ---- rendering ----


async def test_render_shows_streak_marks_and_legend(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test():
        seed(
            app,
            "Gym",
            RecurrenceRule(rule="weekly", weekdays=(0, 2, 4)),
            [("2026-07-24", "2026-07-24"), ("2026-07-25", "2026-07-26"), ("2026-07-26", None)],
        )
        text = Content.from_markup(render_habits(habits(app))).plain
        assert "Gym" in text and "every mon,wed,fri" in text
        assert "■▲✗" in text
        assert "on time" in text and "missed" in text


def test_render_empty_state_explains_what_a_habit_is() -> None:
    assert render_habits([]) == EMPTY
    assert "recurring task" in EMPTY


async def test_render_truncates_long_titles_and_escapes_markup(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test():
        seed(
            app,
            "[bold]Brackets[/] and a very long habit title",
            RecurrenceRule(rule="daily"),
            [(T, None)],
        )
        text = Content.from_markup(render_habits(habits(app))).plain
        assert "[bold]Brackets" in text
        assert "…" in text


async def test_screen_opens_from_key_and_palette(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        seed(app, "Gym", RecurrenceRule(rule="daily"), [(date.today().isoformat(), None)])
        await pilot.pause()

        await pilot.press("H")
        await pilot.pause()
        assert isinstance(app.screen, HabitsScreen)
        assert "Gym" in str(app.screen.query_one("#habits-body").render())
        await pilot.press("escape")
        await pilot.pause()
        assert not isinstance(app.screen, HabitsScreen)

        assert "Habits" in [c.title for c in app.get_system_commands(app.screen)]
        app._cmd_open_habits()
        await pilot.pause()
        assert isinstance(app.screen, HabitsScreen)
