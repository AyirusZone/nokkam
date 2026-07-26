from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from nokkam.app import NokkamApp
from nokkam.config import AppConfig
from nokkam.domain.models import Task


def make_app(tmp_path: Path, accent: str = "#0A84FF") -> NokkamApp:
    return NokkamApp(config=AppConfig(db_path=tmp_path / "data.db", accent=accent))


async def test_notify_desktop_delegates_to_adapter(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test():
        with patch("nokkam.app.send_notification") as mock_send:
            app.notify_desktop("hello", title="Test")
        mock_send.assert_called_once_with("hello", "Test")


async def test_check_reminders_notifies_for_due_soon_task(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test():
        due = datetime.now() + timedelta(minutes=5)
        app.task_service.add_task(
            Task(title="Standup", due_date=due.date().isoformat(), due_time=due.strftime("%H:%M"))
        )
        with patch.object(app, "notify_desktop") as mock_notify:
            app._check_reminders()
        mock_notify.assert_called_once()
        assert "Standup" in mock_notify.call_args[0][0]


async def test_check_reminders_is_idempotent(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    async with app.run_test():
        due = datetime.now() + timedelta(minutes=5)
        app.task_service.add_task(
            Task(title="Standup", due_date=due.date().isoformat(), due_time=due.strftime("%H:%M"))
        )
        with patch.object(app, "notify_desktop") as mock_notify:
            app._check_reminders()
            app._check_reminders()
        assert mock_notify.call_count == 1


async def test_custom_accent_color_registers_theme(tmp_path: Path) -> None:
    app = make_app(tmp_path, accent="#FF0000")
    async with app.run_test():
        theme = app.get_theme("nokkam-dark")
        assert theme.primary == "#FF0000"
