"""Custom Textual themes: Material-style tonal roles, Apple HIG accent seeds.

Two themes only (cad-dark / cad-light) — no rainbow-UI, single accent color
per Apple HIG convention, tonal surface/panel steps per Material convention.
"""

from __future__ import annotations

from textual.theme import Theme

CAD_DARK = Theme(
    name="cad-dark",
    dark=True,
    primary="#0A84FF",      # Apple system blue (dark)
    secondary="#5E5CE6",    # Apple system indigo
    accent="#0A84FF",
    warning="#FF9F0A",
    error="#FF453A",
    success="#32D74B",
    foreground="#F2F2F7",
    background="#0B0B0D",
    surface="#1C1C1E",
    panel="#2C2C2E",
)

CAD_LIGHT = Theme(
    name="cad-light",
    dark=False,
    primary="#007AFF",      # Apple system blue (light)
    secondary="#5856D6",
    accent="#007AFF",
    warning="#FF9500",
    error="#FF3B30",
    success="#34C759",
    foreground="#1C1C1E",
    background="#F2F2F7",
    surface="#FFFFFF",
    panel="#E5E5EA",
)

THEMES = [CAD_DARK, CAD_LIGHT]
