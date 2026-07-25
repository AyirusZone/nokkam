"""Design tokens.

Deliberately not "Apple system blue on near-black" — every TUI reaches for
that by default. Instead: warm-tinted neutrals (not clinical pure black/
white) with a single confident signature accent — a warm vermillion, not
another SaaS blue or violet. Restraint and generous spacing carry the
"considered" feeling; color is spent in exactly one place.

Two themes only (cad-dark / cad-light), accent is user-configurable (see
config.py) but the neutral scaffolding around it is fixed.
"""

from __future__ import annotations

from textual.theme import Theme

from cad_tui.config import DEFAULT_ACCENT

_DARK = {
    "background": "#0C0C0E",  # espresso black, not pure #000
    "surface": "#151519",  # first elevation — rows, cards
    "panel": "#1F1F24",  # second elevation — modals, overlays
    "foreground": "#EDEDEF",  # soft off-white, not #FFF
    "warning": "#E8A33D",
    "error": "#FF5F57",
    "success": "#32D74A",
    "secondary": "#6E7BFF",
}

_LIGHT = {
    "background": "#F7F6F3",  # linen white, not clinical #FFF
    "surface": "#FFFFFF",
    "panel": "#EDEBE6",
    "foreground": "#1C1B1A",  # warm near-black
    "warning": "#B9791F",
    "error": "#D6373A",
    "success": "#1AA251",
    "secondary": "#4B54D6",
}


def build_themes(accent: str = DEFAULT_ACCENT) -> list[Theme]:
    dark = Theme(
        name="cad-dark",
        dark=True,
        primary=accent,
        accent=accent,
        secondary=_DARK["secondary"],
        warning=_DARK["warning"],
        error=_DARK["error"],
        success=_DARK["success"],
        foreground=_DARK["foreground"],
        background=_DARK["background"],
        surface=_DARK["surface"],
        panel=_DARK["panel"],
    )
    light = Theme(
        name="cad-light",
        dark=False,
        primary=accent,
        accent=accent,
        secondary=_LIGHT["secondary"],
        warning=_LIGHT["warning"],
        error=_LIGHT["error"],
        success=_LIGHT["success"],
        foreground=_LIGHT["foreground"],
        background=_LIGHT["background"],
        surface=_LIGHT["surface"],
        panel=_LIGHT["panel"],
    )
    return [dark, light]
