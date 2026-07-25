"""OS-level desktop notifications. Best-effort: any failure (unsupported
platform, missing binary, timeout) is swallowed rather than raised —
notifications are a nicety, never something that should crash the app."""

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
    except Exception:
        return False
    return False


def _notify_macos(message: str, title: str) -> bool:
    script = (
        f"display notification {_applescript_escape(message)} "
        f"with title {_applescript_escape(title)}"
    )
    result = subprocess.run(["osascript", "-e", script], capture_output=True, timeout=5)
    return result.returncode == 0


def _notify_linux(message: str, title: str) -> bool:
    if shutil.which("notify-send") is None:
        return False
    result = subprocess.run(["notify-send", title, message], capture_output=True, timeout=5)
    return result.returncode == 0


def _applescript_escape(text: str) -> str:
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'
