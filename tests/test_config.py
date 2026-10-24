"""load_config() had no dedicated test — only its dataclass defaults were
exercised incidentally via AppConfig(...) construction elsewhere."""

from pathlib import Path

from nokkam.config import DEFAULT_ACCENT, AppConfig, load_config


def test_missing_config_file_returns_defaults(tmp_path: Path) -> None:
    config = load_config(tmp_path / "does-not-exist.toml")
    assert config == AppConfig()


def test_load_config_reads_theme_and_accent(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    path.write_text('theme = "nokkam-light"\naccent = "#00FF00"\n')

    config = load_config(path)

    assert config.theme == "nokkam-light"
    assert config.accent == "#00FF00"


def test_load_config_defaults_theme_and_accent_when_absent(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    path.write_text('db_path = "/tmp/somewhere/data.db"\n')

    config = load_config(path)

    assert config.theme == "nokkam-dark"
    assert config.accent == DEFAULT_ACCENT


def test_load_config_reads_icons_and_ics_sources() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "config.toml"
        path.write_text(
            'icons = { flight = "✈", standup = "\U0001f5e3" }\n'
            'ics_sources = ["/home/me/calendar.ics", "https://example.com/cal.ics"]\n'
        )

        config = load_config(path)

        assert config.icons == {"flight": "✈", "standup": "\U0001f5e3"}
        assert config.ics_sources == ["/home/me/calendar.ics", "https://example.com/cal.ics"]


def test_load_config_expands_custom_db_path(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    db_path = tmp_path / "custom" / "data.db"
    path.write_text(f'db_path = "{db_path}"\n')

    config = load_config(path)

    assert config.db_path == db_path


def test_load_config_reads_new_options(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    path.write_text(
        'default_priority = "High"\n'
        'first_weekday = "sunday"\n'
        'start_filter = "today"\n'
        "[keys]\n"
        'add_task = "n"\n'
        'nav_left = "left,a"\n'
    )

    config = load_config(path)

    assert config.default_priority == 1
    assert config.first_weekday == 6
    assert config.start_filter == "today"
    assert config.keys == {"add_task": "n", "nav_left": "left,a"}
    assert config.warnings == []


def test_new_option_defaults() -> None:
    config = AppConfig()
    assert (config.default_priority, config.first_weekday, config.start_filter) == (2, 0, None)
    assert config.keys == {} and config.warnings == []


def test_malformed_toml_falls_back_to_defaults_with_a_warning(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    path.write_text('theme = "unterminated\n')

    config = load_config(path)

    assert config == AppConfig()
    assert len(config.warnings) == 1
    assert "Could not read" in config.warnings[0] and "using defaults" in config.warnings[0]


def test_bad_values_warn_and_keep_defaults(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    path.write_text(
        "theme = 5\n"
        'default_priority = "urgent"\n'
        'first_weekday = "friday"\n'
        'ics_sources = "not-a-list"\n'
        "start_filter = 3\n"
        "[keys]\n"
        'add_task = ""\n'
        "edit_task = 7\n"
    )

    config = load_config(path)

    assert config.theme == "nokkam-dark"
    assert config.default_priority == 2
    assert config.first_weekday == 0
    assert config.ics_sources == []
    assert config.start_filter is None
    assert config.keys == {}
    text = "\n".join(config.warnings)
    for fragment in (
        "'theme'",
        "default_priority 'urgent'",
        "first_weekday 'friday'",
        "'ics_sources'",
        "'start_filter'",
        "add_task",
        "edit_task",
    ):
        assert fragment in text


def test_unknown_options_are_reported_not_fatal(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    path.write_text('acent = "#fff"\ntheme = "nokkam-light"\n')

    config = load_config(path)

    assert config.theme == "nokkam-light"
    assert config.warnings == ["Unknown config option 'acent' (ignored)"]
