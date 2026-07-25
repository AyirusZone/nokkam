"""Custom Textual themes: Material-style tonal roles, Apple HIG accent seed.

Two themes only (cad-dark / cad-light) — no rainbow-UI, single configurable
accent color (see config.py) per Apple HIG convention, tonal surface/panel
steps per Material convention.
"""

from __future__ import annotations

from textual.theme import Theme

DEFAULT_ACCENT = "#0A84FF"  # Apple system blue


def build_themes(accent: str = DEFAULT_ACCENT) -> list[Theme]:
    dark = Theme(
        name="cad-dark",
        dark=True,
        primary=accent,
        secondary="#5E5CE6",  # Apple system indigo
        accent=accent,
        warning="#FF9F0A",
        error="#FF453A",
        success="#32D74B",
        foreground="#F2F2F7",
        background="#0B0B0D",
        surface="#1C1C1E",
        panel="#2C2C2E",
    )
    light = Theme(
        name="cad-light",
        dark=False,
        primary=accent,
        secondary="#5856D6",
        accent=accent,
        warning="#FF9500",
        error="#FF3B30",
        success="#34C759",
        foreground="#1C1C1E",
        background="#F2F2F7",
        surface="#FFFFFF",
        panel="#E5E5EA",
    )
    return [dark, light]
