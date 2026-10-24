from pathlib import Path

from textual.binding import Binding
from textual.widgets import Input

from nokkam.app import NokkamApp
from nokkam.config import AppConfig
from nokkam.presentation.keymap import build_keymap
from nokkam.presentation.screens.home_screen import HomeScreen
from nokkam.presentation.screens.task_form import TaskFormModal

DEFAULTS = [
    Binding("a", "add_task", "Add", id="add_task"),
    Binding("d", "delete_task", "Delete", id="delete_task"),
    Binding("left,h", "nav_left", "Left", id="nav_left"),
]


def test_valid_override_is_applied_without_warnings() -> None:
    keymap, warnings = build_keymap({"add_task": "n", "nav_left": "left,b"}, DEFAULTS)
    assert keymap == {"add_task": "n", "nav_left": "left,b"}
    assert warnings == []


def test_unknown_binding_id_is_dropped_and_lists_alternatives() -> None:
    keymap, warnings = build_keymap({"ad_task": "n"}, DEFAULTS)
    assert keymap == {}
    assert "Unknown key binding 'ad_task'" in warnings[0]
    assert "add_task" in warnings[0]


def test_empty_key_spec_is_ignored() -> None:
    keymap, warnings = build_keymap({"add_task": " , "}, DEFAULTS)
    assert keymap == {}
    assert "no key" in warnings[0]


def test_conflict_with_a_default_key_is_reported_but_applied() -> None:
    keymap, warnings = build_keymap({"add_task": "d"}, DEFAULTS)
    assert keymap == {"add_task": "d"}
    assert warnings == ["Key 'd' is bound to both add_task and delete_task"]


def test_two_overrides_sharing_a_key_conflict() -> None:
    _, warnings = build_keymap({"add_task": "x", "delete_task": "x"}, DEFAULTS)
    assert warnings == ["Key 'x' is bound to both add_task and delete_task"]


def test_untouched_bindings_never_warn() -> None:
    dupes = [*DEFAULTS, Binding("a", "other", "Other", id="other")]
    _, warnings = build_keymap({}, dupes)
    assert warnings == []


def test_every_configurable_binding_has_a_unique_id_matching_its_action() -> None:
    bindings = [*NokkamApp.BINDINGS, *HomeScreen.BINDINGS]
    assert all(isinstance(b, Binding) and b.id == b.action for b in bindings)
    ids = [b.id for b in bindings if isinstance(b, Binding)]
    assert len(ids) == len(set(ids))


def make_app(tmp_path: Path, **config) -> NokkamApp:
    return NokkamApp(config=AppConfig(db_path=tmp_path / "data.db", **config))


async def test_remapped_key_works_and_old_key_no_longer_does(tmp_path: Path) -> None:
    app = make_app(tmp_path, keys={"add_task": "n"})
    async with app.run_test() as pilot:
        await pilot.pause()

        await pilot.press("a")
        await pilot.pause()
        assert not isinstance(app.screen, TaskFormModal)

        await pilot.press("n")
        await pilot.pause()
        assert isinstance(app.screen, TaskFormModal)


async def test_multiple_keys_can_be_bound_to_one_action(tmp_path: Path) -> None:
    app = make_app(tmp_path, keys={"add_task": "n,ctrl+n"})
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("ctrl+n")
        await pilot.pause()
        assert isinstance(app.screen, TaskFormModal)


async def test_remapping_an_app_level_binding(tmp_path: Path) -> None:
    app = make_app(tmp_path, keys={"toggle_theme": "f2"})
    async with app.run_test() as pilot:
        await pilot.pause()
        before = app.theme
        await pilot.press("f2")
        await pilot.pause()
        assert app.theme != before


async def test_config_and_keymap_problems_surface_as_warning_notifications(
    tmp_path: Path,
) -> None:
    app = make_app(
        tmp_path,
        keys={"nope": "n", "add_task": "d"},
        warnings=["Unknown config option 'acent' (ignored)"],
    )
    async with app.run_test() as pilot:
        await pilot.pause()
        messages = [n.message for n in app._notifications]
        assert any("acent" in m for m in messages)
        assert any("Unknown key binding 'nope'" in m for m in messages)
        assert any("bound to both add_task and delete_task" in m for m in messages)
        assert all(n.severity == "warning" for n in app._notifications)


async def test_no_keys_configured_leaves_defaults_alone(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        assert list(app._notifications) == []
        await pilot.press("a")
        await pilot.pause()
        assert isinstance(app.screen, TaskFormModal)
        app.screen.query_one("#title", Input)  # form is really up


def test_readme_documents_every_configurable_binding_id() -> None:
    readme = (Path(__file__).parent.parent / "README.md").read_text()
    missing = [
        b.id
        for b in [*NokkamApp.BINDINGS, *HomeScreen.BINDINGS]
        if isinstance(b, Binding) and f"`{b.id}`" not in readme
    ]
    assert missing == []
