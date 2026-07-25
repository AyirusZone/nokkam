from unittest.mock import MagicMock, patch

from cad_tui.infra.notification_adapter import _applescript_escape, send_notification


def test_macos_notification_success() -> None:
    with patch("cad_tui.infra.notification_adapter.sys.platform", "darwin"):
        with patch("cad_tui.infra.notification_adapter.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            assert send_notification("Hello", "Title") is True
            assert mock_run.call_args[0][0][0] == "osascript"


def test_macos_notification_nonzero_exit_returns_false() -> None:
    with patch("cad_tui.infra.notification_adapter.sys.platform", "darwin"):
        with patch("cad_tui.infra.notification_adapter.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1)
            assert send_notification("Hello") is False


def test_macos_notification_exception_is_swallowed() -> None:
    with patch("cad_tui.infra.notification_adapter.sys.platform", "darwin"):
        with patch(
            "cad_tui.infra.notification_adapter.subprocess.run", side_effect=OSError("boom")
        ):
            assert send_notification("Hello") is False


def test_linux_notification_missing_binary_returns_false() -> None:
    with patch("cad_tui.infra.notification_adapter.sys.platform", "linux"):
        with patch("cad_tui.infra.notification_adapter.shutil.which", return_value=None):
            assert send_notification("Hello") is False


def test_linux_notification_success() -> None:
    with patch("cad_tui.infra.notification_adapter.sys.platform", "linux"):
        with patch(
            "cad_tui.infra.notification_adapter.shutil.which", return_value="/usr/bin/notify-send"
        ):
            with patch("cad_tui.infra.notification_adapter.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0)
                assert send_notification("Hello", "Title") is True


def test_windows_notification_missing_powershell_returns_false() -> None:
    with patch("cad_tui.infra.notification_adapter.sys.platform", "win32"):
        with patch("cad_tui.infra.notification_adapter.shutil.which", return_value=None):
            assert send_notification("Hello") is False


def test_windows_notification_success() -> None:
    with patch("cad_tui.infra.notification_adapter.sys.platform", "win32"):
        with patch(
            "cad_tui.infra.notification_adapter.shutil.which",
            return_value="C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe",
        ):
            with patch("cad_tui.infra.notification_adapter.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0)
                assert send_notification("Hello", "Title") is True
                assert mock_run.call_args[0][0][0] == "powershell"


def test_unsupported_platform_returns_false() -> None:
    with patch("cad_tui.infra.notification_adapter.sys.platform", "freebsd13"):
        assert send_notification("Hello") is False


def test_applescript_escapes_quotes_and_backslashes() -> None:
    assert _applescript_escape('He said "hi"') == '"He said \\"hi\\""'
    assert _applescript_escape("back\\slash") == '"back\\\\slash"'


def test_powershell_escapes_single_quotes() -> None:
    from cad_tui.infra.notification_adapter import _powershell_escape

    assert _powershell_escape("It's due") == "'It''s due'"
