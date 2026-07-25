from cad_tui.config import DEFAULT_ACCENT
from cad_tui.presentation.theme import build_themes


def test_custom_accent_applied_to_both_themes() -> None:
    themes = build_themes("#FF0000")
    by_name = {t.name: t for t in themes}
    assert by_name["cad-dark"].primary == "#FF0000"
    assert by_name["cad-dark"].accent == "#FF0000"
    assert by_name["cad-light"].primary == "#FF0000"
    assert by_name["cad-light"].accent == "#FF0000"


def test_default_accent_used_when_not_specified() -> None:
    themes = build_themes()
    assert all(t.primary == DEFAULT_ACCENT for t in themes)


def test_themes_have_distinct_dark_flag() -> None:
    dark, light = build_themes()
    assert dark.dark is True
    assert light.dark is False
