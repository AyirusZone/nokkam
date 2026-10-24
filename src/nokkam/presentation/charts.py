"""Tiny Unicode chart helpers — pure string functions, no Textual."""

from __future__ import annotations

from collections.abc import Sequence

_EIGHTHS = " ▁▂▃▄▅▆▇█"
_LEFT_EIGHTHS = " ▏▎▍▌▋▊▉█"


def hbar(value: float, maximum: float, width: int) -> str:
    """A horizontal bar `width` cells wide (eighth-block precision), padded
    with ░. Any positive value shows at least a sliver."""
    if maximum <= 0 or value <= 0:
        return "░" * width
    eighths = max(1, round(value / maximum * width * 8))
    eighths = min(eighths, width * 8)
    full, part = divmod(eighths, 8)
    bar = "█" * full + (_LEFT_EIGHTHS[part] if part else "")
    return bar + "░" * (width - len(bar))


def column_chart(
    values: Sequence[float], height: int, col_width: int = 1, gap: int = 0
) -> list[str]:
    """Vertical bars, one column per value, as `height` rows top to bottom.
    Scaled to the largest value; any positive value shows at least a sliver."""
    peak = max(values, default=0)
    heights = [0 if peak <= 0 or v <= 0 else max(1, round(v / peak * height * 8)) for v in values]
    rows: list[str] = []
    for row in range(height - 1, -1, -1):  # top row first
        cells = []
        for eighths in heights:
            remaining = eighths - 8 * row
            glyph = "█" if remaining >= 8 else _EIGHTHS[max(remaining, 0)]
            cells.append(glyph * col_width)
        rows.append((" " * gap).join(cells).rstrip())
    return rows
