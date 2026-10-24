from datetime import date

import pytest

from nokkam.domain.filter_query import QueryError, TaskQuery, parse_query
from nokkam.domain.models import Priority, Status, Task

TODAY = date(2026, 7, 27)


def matches(
    query: str,
    task: Task,
    project: str | None = None,
    tags: tuple[str, ...] = (),
) -> bool:
    return parse_query(query).matches(task, project_name=project, tag_names=tags, today=TODAY)


def test_parse_collects_every_key() -> None:
    query = parse_query(
        'project:Work tag:urgent tag:home priority:high due:week status:all "big deal"'
    )
    assert query == TaskQuery(
        projects=frozenset({"work"}),
        tags=frozenset({"urgent", "home"}),
        priorities=frozenset({Priority.HIGH}),
        due="week",
        status="all",
        words=("big deal",),
    )


def test_status_defaults_to_open() -> None:
    assert not matches("report", Task(title="report", status=Status.DONE))
    assert matches("report", Task(title="report"))
    assert matches("status:all report", Task(title="report", status=Status.DONE))
    assert matches("status:done", Task(title="x", status=Status.DONE))


def test_project_match_is_case_insensitive_and_ors_values() -> None:
    task = Task(title="x")
    assert matches("project:work", task, project="Work")
    assert matches("project:work project:home", task, project="Home")
    assert not matches("project:work", task, project="Home")
    assert not matches("project:work", task, project=None)


def test_tags_match_any_listed_tag() -> None:
    task = Task(title="x")
    assert matches("tag:a tag:b", task, tags=("B", "c"))
    assert not matches("tag:a", task, tags=("b",))
    assert not matches("tag:a", task, tags=())


def test_keys_combine_with_and() -> None:
    task = Task(title="x", priority=Priority.HIGH)
    assert matches("project:work priority:high", task, project="Work")
    assert not matches("project:work priority:low", task, project="Work")


@pytest.mark.parametrize(
    ("due_filter", "due_date", "expected"),
    [
        ("today", "2026-07-27", True),
        ("today", "2026-07-28", False),
        ("tomorrow", "2026-07-28", True),
        ("overdue", "2026-07-26", True),
        ("overdue", "2026-07-27", False),
        ("week", "2026-08-03", True),
        ("week", "2026-08-04", False),
        ("week", "2026-07-26", False),
        ("none", None, True),
        ("none", "2026-07-27", False),
        ("2026-09-01", "2026-09-01", True),
        ("2026-09-01", "2026-09-02", False),
        ("today", None, False),
    ],
)
def test_due_filters(due_filter: str, due_date: str | None, expected: bool) -> None:
    assert matches(f"due:{due_filter}", Task(title="x", due_date=due_date)) is expected


def test_overdue_ignores_done_tasks() -> None:
    task = Task(title="x", due_date="2026-07-01", status=Status.DONE)
    assert not matches("status:all due:overdue", task)


def test_priority_aliases() -> None:
    assert parse_query("priority:h").priorities == {Priority.HIGH}
    assert parse_query("priority:medium").priorities == {Priority.MEDIUM}
    assert parse_query("priority:3 priority:low").priorities == {Priority.LOW}


def test_free_words_must_all_appear_in_title() -> None:
    assert matches("quarterly report", Task(title="Write the QUARTERLY sales Report"))
    assert not matches("quarterly report", Task(title="Write the quarterly plan"))


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("", "empty"),
        ("   ", "empty"),
        ("colour:red", "Unknown filter 'colour:'"),
        ("priority:urgent", "Unknown priority"),
        ("due:someday", "Unknown due"),
        ("due:2026-13-40", "Unknown due"),
        ("status:pending", "Unknown status"),
        ("project:", "needs a value"),
        ('project:"Big', "Unbalanced quote"),
    ],
)
def test_invalid_queries_raise_readable_errors(text: str, message: str) -> None:
    with pytest.raises(QueryError, match=message):
        parse_query(text)
