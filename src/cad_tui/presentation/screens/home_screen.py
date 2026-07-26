"""Home: calendar and tasks side by side (calcurse-style layout).

Left: month calendar. Middle-top: tasks due on the selected calendar day.
Middle-bottom: the full task list. Right: projects and tags — select one
or more to filter both task lists down to matching tasks. Tab cycles focus
between all panes; add/edit/delete/toggle act on whichever pane has focus.
"""

from __future__ import annotations

import calendar as calendar_mod
from datetime import date, timedelta
from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Footer, ListItem, ListView, Static, TabbedContent, TabPane

from cad_tui.domain.models import Event, Project, Status, Tag, Task
from cad_tui.domain.recurrence import RecurrenceRule
from cad_tui.presentation.screens.help import HelpModal
from cad_tui.presentation.screens.quick_add import QuickAddModal
from cad_tui.presentation.screens.task_form import TaskFormModal, TaskFormResult
from cad_tui.presentation.screens.task_list import TaskRow
from cad_tui.presentation.screens.text_prompt import TextPromptModal
from cad_tui.presentation.widgets.app_header import AppHeader
from cad_tui.presentation.widgets.calendar_grid import CalendarGrid, DayCell

if TYPE_CHECKING:
    from cad_tui.app import CadTuiApp


class ProjectRow(ListItem):
    def __init__(self, project: Project, selected: bool) -> None:
        super().__init__()
        self.project = project
        self.selected = selected

    def compose(self) -> ComposeResult:
        mark = "[$success]✓[/]" if self.selected else " "
        yield Static(f"{mark} [{self.project.color}]●[/] {self.project.name}")


class TagRow(ListItem):
    def __init__(self, tag: Tag, selected: bool) -> None:
        super().__init__()
        self.tag = tag
        self.selected = selected

    def compose(self) -> ComposeResult:
        mark = "[$success]✓[/]" if self.selected else " "
        yield Static(f"{mark} [{self.tag.color}]#[/] {self.tag.name}")


class ProjectGroupHeader(ListItem):
    """A non-actionable divider labelling a run of tasks in the "All tasks"
    list by project, colored to match that project's marker elsewhere."""

    def __init__(self, label: str, color: str) -> None:
        super().__init__(classes="project-group-header")
        self.label_text = label
        self.color = color

    def compose(self) -> ComposeResult:
        yield Static(f"[{self.color}]●[/] [b]{self.label_text}[/b]")


class EventRow(ListItem):
    """A read-only .ics-synced event shown alongside a day's tasks — never
    editable/deletable from within cad-tui, so no action handles it (the
    same "isinstance(child, TaskRow)" guards used for group headers make
    this a safe no-op target for e/d/space/etc.)."""

    def __init__(self, event: Event) -> None:
        super().__init__(classes="event-row")
        self.event = event

    def compose(self) -> ComposeResult:
        time_part = ""
        if not self.event.all_day and " " in self.event.start_at:
            time_part = f"  [dim]{self.event.start_at.split(' ', 1)[1]}[/]"
        yield Static(f"[$secondary]▸[/] {self.event.title}{time_part}")


class HomeScreen(Screen):
    # Narrows self.app's type for mypy only (Textual's own `app` property is
    # untouched at runtime — this is a bare annotation, not an assignment).
    app: CadTuiApp

    BINDINGS = [
        Binding("left,h", "nav_left", "Left", show=False),
        Binding("right,l", "nav_right", "Right", show=False),
        Binding("up,k", "nav_up", "Up", show=False),
        Binding("down,j", "nav_down", "Down", show=False),
        Binding("[", "prev_month", "Prev month"),
        Binding("]", "next_month", "Next month"),
        Binding("t", "context_today_or_timer", "Today/Timer"),
        Binding("p", "pause_resume_timer", "Pause/Resume timer"),
        Binding("a", "add_task", "Add"),
        Binding("e", "edit_task", "Edit"),
        Binding("d", "delete_task", "Delete"),
        Binding("space", "toggle_complete", "Toggle"),
        Binding("u", "undo", "Undo"),
        Binding("s", "add_subtask", "Subtask"),
        Binding("A", "quick_add", "Quick add"),
        Binding("w", "open_agenda", "Agenda"),
        Binding("S", "open_stats", "Stats"),
        Binding("P", "open_pomodoro", "Pomodoro"),
        Binding("R", "sync_calendars", "Sync calendars"),
        Binding("question_mark", "show_help", "Help"),
    ]

    SMART_LIST_LABELS = {
        "today": "Today",
        "overdue": "Overdue",
        "week": "This week",
    }

    def __init__(self) -> None:
        super().__init__()
        self.smart_filter: str | None = None
        self.selected_project_ids: set[int] = set()
        self.selected_tag_ids: set[int] = set()

    def compose(self) -> ComposeResult:
        yield AppHeader(subtitle="home")
        with Horizontal(id="home-body"):
            with Vertical(id="main-pane"):
                yield CalendarGrid(id="calendar")
                with Vertical(id="day-pane"):
                    yield Static("", id="day-title", classes="accent-text")
                    yield ListView(id="day-tasks")
            with TabbedContent(id="filter-tabs"):
                with TabPane("Projects", id="projects-tab"):
                    yield ListView(id="projects-list")
                with TabPane("Tags", id="tags-tab"):
                    yield ListView(id="tags-list")
                with TabPane("All Tasks", id="all-tasks-tab"):
                    yield ListView(id="task-list")
        yield Footer()

    def on_mount(self) -> None:
        self.refresh_all()
        self.all_list.focus()

    # ---- widget accessors ----
    @property
    def calendar(self) -> CalendarGrid:
        return self.query_one("#calendar", CalendarGrid)

    @property
    def day_list(self) -> ListView:
        return self.query_one("#day-tasks", ListView)

    @property
    def all_list(self) -> ListView:
        return self.query_one("#task-list", ListView)

    @property
    def projects_list(self) -> ListView:
        return self.query_one("#projects-list", ListView)

    @property
    def tags_list(self) -> ListView:
        return self.query_one("#tags-list", ListView)

    # ---- focus / context ----
    def _in_day_context(self) -> bool:
        return self.focused is self.calendar or self.focused is self.day_list

    def _focused_pane(self) -> str:
        if self._in_day_context():
            return "day"
        if self.focused is self.projects_list:
            return "projects"
        if self.focused is self.tags_list:
            return "tags"
        if self.focused is self.all_list:
            return "all"
        # Anything else focused (typically the tab bar itself, reached by
        # tabbing past day-tasks) resolves to whichever tab is currently
        # showing, so actions stay consistent with what's visually active
        # instead of silently falling back to a hidden tab's list.
        active_tab = self.query_one(TabbedContent).active
        return {
            "projects-tab": "projects",
            "tags-tab": "tags",
            "all-tasks-tab": "all",
        }.get(active_tab, "all")

    def _active_list(self) -> ListView:
        return {
            "day": self.day_list,
            "projects": self.projects_list,
            "tags": self.tags_list,
            "all": self.all_list,
        }[self._focused_pane()]

    def focus_calendar(self) -> None:
        self.calendar.focus()

    # ---- calendar day selection (mouse) ----
    def on_day_cell_selected(self, message: DayCell.Selected) -> None:
        self.calendar.focus_date = message.day
        self.refresh_all()
        self.calendar.focus()

    # ---- refresh ----
    def refresh_all(self) -> None:
        self._refresh_calendar()
        self._refresh_projects_list()
        self._refresh_tags_list()
        self._refresh_day_tasks()
        self._refresh_all_tasks()
        self._update_header_meta()

    def _refresh_calendar(self) -> None:
        fd = self.calendar.focus_date
        self.calendar.project_colors = {
            p.id: p.color for p in self.app.project_repo.list() if p.id is not None
        }
        self.calendar.icon_overrides = self.app.config.icons
        self.calendar.tasks_by_date = self._month_tasks(fd.year, fd.month)
        self.calendar.events_by_date = self.app.ics_service.events_by_date(
            f"{fd.year:04d}-{fd.month:02d}"
        )
        self.calendar.render_month()

    def _update_header_meta(self) -> None:
        if self.smart_filter:
            meta = self.SMART_LIST_LABELS[self.smart_filter]
        else:
            meta = self.calendar.focus_date.strftime("%B %Y")
        self.query_one(AppHeader).set_meta(meta)

    def _month_tasks(self, year: int, month: int) -> dict[str, list[Task]]:
        """Tasks due within `year`/`month`, grouped by ISO date, for the
        calendar grid's inline day-cell previews."""
        by_date: dict[str, list[Task]] = {}
        prefix = f"{year:04d}-{month:02d}"
        for task in self.app.task_service.list_tasks():
            if task.due_date and task.due_date.startswith(prefix) and self._passes_filters(task):
                by_date.setdefault(task.due_date, []).append(task)
        return by_date

    def _passes_filters(self, task: Task) -> bool:
        """Whether `task` matches the currently selected project/tag filters
        — unrelated tasks and dates are removed from the calendar and task
        lists entirely (an empty selection on either axis means "no
        restriction")."""
        if self.selected_project_ids and task.project_id not in self.selected_project_ids:
            return False
        return not self.selected_tag_ids or bool(set(task.tag_ids) & self.selected_tag_ids)

    def _refresh_day_tasks(self, select_index: int | None = None) -> None:
        if select_index is None:
            select_index = self.day_list.index
        fd = self.calendar.focus_date
        self.query_one("#day-title", Static).update(fd.strftime("%A, %d %B %Y"))
        day_list = self.day_list
        day_list.clear()
        tasks = [
            t
            for t in self.app.task_service.list_tasks()
            if t.due_date == fd.isoformat() and self._passes_filters(t)
        ]
        for task in tasks:
            day_list.append(TaskRow(task))
        for event in self.app.ics_service.events_by_date(fd.isoformat()).get(fd.isoformat(), []):
            day_list.append(EventRow(event))
        if tasks:
            index = 0 if select_index is None else max(0, min(select_index, len(tasks) - 1))
            day_list.index = index

    def _refresh_all_tasks(self, select_index: int | None = None) -> None:
        if select_index is None:
            select_index = self.all_list.index
        all_list = self.all_list
        all_list.clear()
        if self.smart_filter is None:
            rows = self.app.task_service.list_tasks_tree()
        else:
            rows = [(t, 0) for t in self._smart_list_tasks()]
        rows = [(t, d) for t, d in rows if self._passes_filters(t)]

        # Smart lists (Today/Overdue/This week) stay flat and chronological;
        # the default "All tasks" view groups by project so the app reads
        # project-first, with a colored header matching that project's
        # marker in the projects pane. Task rows skip their own project dot
        # in that grouped view — the header already carries it — but keep it
        # in the flat smart-list view, which has no header to carry it.
        items: list[tuple]
        show_project = self.smart_filter is not None
        if self.smart_filter is None:
            items = self._grouped_by_project(rows)
        else:
            items = [("task", task, depth) for task, depth in rows]

        for item in items:
            if item[0] == "header":
                _, label, color = item
                all_list.append(ProjectGroupHeader(label, color))
            else:
                _, task, depth = item
                all_list.append(TaskRow(task, depth=depth, show_project=show_project))

        task_positions = [i for i, item in enumerate(items) if item[0] == "task"]
        if task_positions:
            if select_index is None:
                position = 0
            else:
                position = max(0, min(select_index, len(task_positions) - 1))
            all_list.index = task_positions[position]

    def _grouped_by_project(self, rows: list[tuple[Task, int]]) -> list[tuple]:
        """Group top-level tasks by project (subtasks stay under whichever
        group their parent landed in), ordered to match the projects pane,
        with an unaffiliated "No project" group last."""
        groups: dict[int | None, list[tuple[Task, int]]] = {}
        last_key: int | None = None
        for task, depth in rows:
            key = task.project_id if depth == 0 else last_key
            groups.setdefault(key, []).append((task, depth))
            if depth == 0:
                last_key = key

        ordered_keys: list[int | None] = [
            p.id for p in self.app.project_repo.list() if p.id in groups
        ]
        ordered_keys += [k for k in groups if k is not None and k not in ordered_keys]
        if None in groups:
            ordered_keys.append(None)

        items: list[tuple] = []
        for key in ordered_keys:
            project = self.app.project_repo.get(key) if key is not None else None
            label = project.name if project else "No project"
            color = project.color if project else "$foreground 40%"
            items.append(("header", label, color))
            items.extend(("task", task, depth) for task, depth in groups[key])
        return items

    def _attached_project_ids(self) -> set[int]:
        return {
            t.project_id for t in self.app.task_service.list_tasks() if t.project_id is not None
        }

    def _attached_tag_ids(self) -> set[int]:
        ids: set[int] = set()
        for t in self.app.task_service.list_tasks():
            ids.update(t.tag_ids)
        return ids

    def _refresh_projects_list(self) -> None:
        select_index = self.projects_list.index
        lv = self.projects_list
        lv.clear()
        attached = self._attached_project_ids()
        self.selected_project_ids &= attached
        projects = [p for p in self.app.project_repo.list() if p.id in attached]
        for project in projects:
            assert project.id is not None  # loaded from the repository
            lv.append(ProjectRow(project, selected=project.id in self.selected_project_ids))
        if projects:
            lv.index = 0 if select_index is None else max(0, min(select_index, len(projects) - 1))

    def _refresh_tags_list(self) -> None:
        select_index = self.tags_list.index
        lv = self.tags_list
        lv.clear()
        attached = self._attached_tag_ids()
        self.selected_tag_ids &= attached
        tags = [tag for tag in self.app.tag_repo.list() if tag.id in attached]
        for tag in tags:
            assert tag.id is not None  # loaded from the repository
            lv.append(TagRow(tag, selected=tag.id in self.selected_tag_ids))
        if tags:
            lv.index = 0 if select_index is None else max(0, min(select_index, len(tags) - 1))

    def _toggle_project_filter(self) -> None:
        child = self.projects_list.highlighted_child
        if not isinstance(child, ProjectRow):
            return
        pid = child.project.id
        assert pid is not None
        self.selected_project_ids.symmetric_difference_update({pid})
        self._refresh_projects_list()
        self._refresh_calendar()
        self._refresh_day_tasks()
        self._refresh_all_tasks()

    def _toggle_tag_filter(self) -> None:
        child = self.tags_list.highlighted_child
        if not isinstance(child, TagRow):
            return
        tid = child.tag.id
        assert tid is not None
        self.selected_tag_ids.symmetric_difference_update({tid})
        self._refresh_tags_list()
        self._refresh_calendar()
        self._refresh_day_tasks()
        self._refresh_all_tasks()

    def _prompt_add_project(self) -> None:
        def on_result(name: str | None) -> None:
            if not name:
                return
            self.app.project_repo.get_or_create(name)
            self._refresh_projects_list()

        self.app.push_screen(TextPromptModal("Add project", "Project name"), on_result)

    def _prompt_add_tag(self) -> None:
        def on_result(name: str | None) -> None:
            if not name:
                return
            self.app.tag_repo.get_or_create(name)
            self._refresh_tags_list()

        self.app.push_screen(TextPromptModal("Add tag", "Tag name"), on_result)

    def _smart_list_tasks(self) -> list[Task]:
        today_iso = date.today().isoformat()
        open_tasks = self.app.task_service.list_tasks(status=Status.OPEN)
        if self.smart_filter == "today":
            return [t for t in open_tasks if t.due_date == today_iso]
        if self.smart_filter == "overdue":
            return [t for t in open_tasks if t.due_date and t.due_date < today_iso]
        if self.smart_filter == "week":
            week_end = (date.today() + timedelta(days=7)).isoformat()
            return [t for t in open_tasks if t.due_date and today_iso <= t.due_date <= week_end]
        return open_tasks

    def set_smart_filter(self, filter_name: str | None) -> None:
        self.smart_filter = filter_name
        self._refresh_all_tasks()
        self._update_header_meta()

    def select_task_by_id(self, task_id: int) -> None:
        self.set_smart_filter(None)
        self.all_list.focus()
        for index, item in enumerate(self.all_list.children):
            if isinstance(item, TaskRow) and item.model.id == task_id:
                self.all_list.index = index
                return

    @property
    def selected_task(self) -> Task | None:
        child = self._active_list().highlighted_child
        return child.model if isinstance(child, TaskRow) else None

    # ---- navigation ----
    def _move_calendar(self, delta_days: int) -> None:
        self.calendar.focus_date = self.calendar.focus_date + timedelta(days=delta_days)
        self.refresh_all()

    def action_nav_left(self) -> None:
        if self.focused is self.calendar:
            self._move_calendar(-1)

    def action_nav_right(self) -> None:
        if self.focused is self.calendar:
            self._move_calendar(1)

    def action_nav_up(self) -> None:
        if self.focused is self.calendar:
            self._move_calendar(-7)
        else:
            self._active_list().action_cursor_up()

    def action_nav_down(self) -> None:
        if self.focused is self.calendar:
            self._move_calendar(7)
        else:
            self._active_list().action_cursor_down()

    def action_prev_month(self) -> None:
        fd = self.calendar.focus_date
        prev_last_day = fd.replace(day=1) - timedelta(days=1)
        self.calendar.focus_date = prev_last_day.replace(day=min(fd.day, prev_last_day.day))
        self.refresh_all()

    def action_next_month(self) -> None:
        fd = self.calendar.focus_date
        days_in_month = calendar_mod.monthrange(fd.year, fd.month)[1]
        next_month_first = fd.replace(day=days_in_month) + timedelta(days=1)
        days_in_next = calendar_mod.monthrange(next_month_first.year, next_month_first.month)[1]
        self.calendar.focus_date = next_month_first.replace(day=min(fd.day, days_in_next))
        self.refresh_all()

    def action_context_today_or_timer(self) -> None:
        if self.focused is self.calendar:
            self.calendar.focus_date = date.today()
            self.refresh_all()
        else:
            self.action_toggle_timer()

    # ---- task actions (context-aware) ----
    def action_add_task(self) -> None:
        pane = self._focused_pane()
        if pane == "projects":
            self._prompt_add_project()
            return
        if pane == "tags":
            self._prompt_add_tag()
            return
        default_due = self.calendar.focus_date.isoformat() if self._in_day_context() else ""

        def on_result(result: TaskFormResult | None) -> None:
            if result is None:
                return
            task = Task(
                title=result.title,
                notes=result.notes,
                priority=result.priority,
                due_date=result.due_date,
                due_time=result.due_time,
                project_id=self._resolve_project(result.project_name),
                tag_ids=self.app.tag_repo.get_or_create_many(result.tag_names),
                recurrence_id=self._resolve_recurrence(result.recurrence, None),
                private=result.private,
            )
            created = self.app.task_service.add_task(task)
            assert created.id is not None  # just persisted, must have an id
            self.app.task_service.set_blocked_by(
                created.id, self._resolve_blocker(result.blocked_by_title)
            )
            self.refresh_all()

        self.app.push_screen(TaskFormModal(default_due_date=default_due), on_result)

    def action_add_subtask(self) -> None:
        parent = self.selected_task
        if parent is None:
            return

        def on_result(result: TaskFormResult | None) -> None:
            if result is None:
                return
            task = Task(
                title=result.title,
                notes=result.notes,
                priority=result.priority,
                due_date=result.due_date,
                due_time=result.due_time,
                project_id=self._resolve_project(result.project_name),
                tag_ids=self.app.tag_repo.get_or_create_many(result.tag_names),
                recurrence_id=self._resolve_recurrence(result.recurrence, None),
                parent_task_id=parent.id,
                private=result.private,
            )
            created = self.app.task_service.add_task(task)
            assert created.id is not None  # just persisted, must have an id
            self.app.task_service.set_blocked_by(
                created.id, self._resolve_blocker(result.blocked_by_title)
            )
            self.refresh_all()

        self.app.push_screen(TaskFormModal(parent_title=parent.title), on_result)

    def action_quick_add(self) -> None:
        def on_result(result) -> None:
            if result is None or not result.title:
                return
            task = Task(title=result.title, due_date=result.due_date, due_time=result.due_time)
            self.app.task_service.add_task(task)
            self.refresh_all()

        self.app.push_screen(QuickAddModal(), on_result)

    def action_edit_task(self) -> None:
        task = self.selected_task
        if task is None:
            return
        assert task.id is not None  # selected tasks always come from the repository
        task_id = task.id
        project = self.app.project_repo.get(task.project_id) if task.project_id else None
        tags = self.app.tag_repo.get_many(task.tag_ids)
        recurrence_rule = (
            self.app.recurrence_repo.get(task.recurrence_id) if task.recurrence_id else None
        )
        blocker_id = self.app.dependency_repo.get_blocker_id(task_id)
        blocker = self.app.task_repo.get(blocker_id) if blocker_id else None

        def on_result(result: TaskFormResult | None) -> None:
            if result is None:
                return
            self.app.task_service.update_task(
                task_id,
                title=result.title,
                notes=result.notes,
                priority=result.priority,
                due_date=result.due_date,
                due_time=result.due_time,
                project_id=self._resolve_project(result.project_name),
                tag_ids=self.app.tag_repo.get_or_create_many(result.tag_names),
                recurrence_id=self._resolve_recurrence(result.recurrence, task.recurrence_id),
                private=result.private,
            )
            self.app.task_service.set_blocked_by(
                task_id, self._resolve_blocker(result.blocked_by_title)
            )
            self.refresh_all()

        self.app.push_screen(
            TaskFormModal(
                task=task,
                project_name=project.name if project else "",
                tag_names=", ".join(t.name for t in tags),
                recurrence=recurrence_rule.rule if recurrence_rule else "",
                blocked_by_title=blocker.title if blocker else "",
            ),
            on_result,
        )

    def action_delete_task(self) -> None:
        task = self.selected_task
        if task is None:
            return
        assert task.id is not None  # selected tasks always come from the repository
        self.app.task_service.delete_task(task.id)
        self.refresh_all()

    def action_toggle_complete(self) -> None:
        pane = self._focused_pane()
        if pane == "projects":
            self._toggle_project_filter()
            return
        if pane == "tags":
            self._toggle_tag_filter()
            return
        task = self.selected_task
        if task is None:
            return
        assert task.id is not None  # selected tasks always come from the repository
        if task.status == Status.OPEN and self.app.task_service.is_blocked(task.id):
            blocker_id = self.app.dependency_repo.get_blocker_id(task.id)
            blocker = self.app.task_repo.get(blocker_id) if blocker_id else None
            self.notify(
                f"Blocked by: {blocker.title if blocker else 'another task'}", severity="warning"
            )
            return
        self.app.task_service.toggle_complete(task.id)
        self.refresh_all()

    def action_toggle_timer(self) -> None:
        task = self.selected_task
        if task is None:
            return
        assert task.id is not None  # selected tasks always come from the repository
        running = self.app.toggle_task_timer(task.id)
        self.refresh_all()
        self.notify(f"Timer {'started' if running else 'stopped'}: {task.title}")

    def action_pause_resume_timer(self) -> None:
        paused = self.app.pause_resume_task_timer()
        if paused is None:
            return
        self.refresh_all()
        self.notify("Timer paused" if paused else "Timer resumed")

    def action_sync_calendars(self) -> None:
        if not self.app.ics_service.sources:
            self.notify("No .ics sources configured", severity="warning")
            return
        self.notify("Syncing calendars…")
        self.app.sync_ics()

    def action_undo(self) -> None:
        label = self.app.task_service.undo_last()
        self.refresh_all()
        if label:
            self.notify(f"Undid: {label}")

    def action_show_help(self) -> None:
        self.app.push_screen(HelpModal())

    def action_open_agenda(self) -> None:
        from cad_tui.presentation.screens.agenda_screen import AgendaScreen

        self.app.push_screen(AgendaScreen())

    def action_open_stats(self) -> None:
        from cad_tui.presentation.screens.stats_screen import StatsScreen

        self.app.push_screen(StatsScreen())

    def action_open_pomodoro(self) -> None:
        self.app.action_open_pomodoro()

    def _resolve_project(self, name: str | None) -> int | None:
        if not name:
            return None
        return self.app.project_repo.get_or_create(name)

    def _resolve_recurrence(self, rule: str, existing_id: int | None) -> int | None:
        if not rule:
            return None
        if existing_id is not None:
            existing = self.app.recurrence_repo.get(existing_id)
            if existing is not None and existing.rule == rule:
                return existing_id
        return self.app.recurrence_repo.create(RecurrenceRule(rule=rule))

    def _resolve_blocker(self, title: str | None) -> int | None:
        if not title:
            return None
        needle = title.strip().lower()
        for t in self.app.task_service.list_tasks():
            if t.title.lower() == needle:
                return t.id
        return None
