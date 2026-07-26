"""OS-level desktop notifications. Best-effort: any failure (unsupported
platform, missing binary, timeout) is swallowed rather than raised —
notifications are a nicety, never something that should crash the app.

No extra dependency on any platform: osascript (macOS), notify-send
(Linux, most desktop environments ship it), powershell + the .NET
System.Windows.Forms balloon tip (Windows — built into every install)."""

from __future__ import annotations

import shutil
import subprocess
import sys


def send_notification(message: str, title: str = "cad-tui") -> bool:
    """Returns True if a notification was actually dispatched."""
    try:
        if sys.platform == "darwin":
            return _notify_macos(message, title)
        if sys.platform.startswith("linux"):
            return _notify_linux(message, title)
        if sys.platform == "win32":
            return _notify_windows(message, title)
    except Exception:  # noqa: BLE001 - best-effort notification, must never crash the app
        return False
    return False


def _notify_macos(message: str, title: str) -> bool:
    script = (
        f"display notification {_applescript_escape(message)} "
        f"with title {_applescript_escape(title)}"
    )
    result = subprocess.run(
        ["osascript", "-e", script], capture_output=True, timeout=5, check=False
    )
    return result.returncode == 0


def _notify_linux(message: str, title: str) -> bool:
    if shutil.which("notify-send") is None:
        return False
    result = subprocess.run(
        ["notify-send", title, message], capture_output=True, timeout=5, check=False
    )
    return result.returncode == 0


def _notify_windows(message: str, title: str) -> bool:
    if shutil.which("powershell") is None:
        return False
    script = (
        "Add-Type -AssemblyName System.Windows.Forms; "
        "$n = New-Object System.Windows.Forms.NotifyIcon; "
        "$n.Icon = [System.Drawing.SystemIcons]::Information; "
        "$n.Visible = $true; "
        f"$n.ShowBalloonTip(5000, {_powershell_escape(title)}, "
        f"{_powershell_escape(message)}, "
        "[System.Windows.Forms.ToolTipIcon]::Info); "
        "Start-Sleep -Seconds 1; "
        "$n.Dispose()"
    )
    result = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output=True,
        timeout=8,
        check=False,
    )
    return result.returncode == 0


def _applescript_escape(text: str) -> str:
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _powershell_escape(text: str) -> str:
    escaped = text.replace("'", "''")
    return f"'{escaped}'"
