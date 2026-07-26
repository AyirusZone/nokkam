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
