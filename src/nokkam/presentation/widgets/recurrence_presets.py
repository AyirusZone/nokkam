"""Ready-made repeat intervals for the task form's Repeats picker.

Each option's value is the rule text the form parses, so a preset is just a
shortcut for typing it. "Custom…" leaves the text field for your own rule."""

from __future__ import annotations

CUSTOM = "custom"

RECURRENCE_PRESETS: list[tuple[str, str]] = [
    ("None", ""),
    ("Every day", "every day"),
    ("Every weekday", "every weekday"),
    ("Every weekend", "every weekend"),
    ("Every week", "every week"),
    ("Every 2 weeks", "every 2 weeks"),
    ("Every month", "every month"),
    ("Every 3 months", "every 3 months"),
    ("Every year", "every year"),
    ("Custom…", CUSTOM),
]
_PRESET_VALUES = {value for _, value in RECURRENCE_PRESETS if value != CUSTOM}


def preset_for(rule_text: str) -> str:
    """The picker value for an existing rule text: its preset if it is one
    exactly, "" (None) when empty, otherwise Custom…."""
    text = rule_text.strip().lower()
    return text if text in _PRESET_VALUES else CUSTOM
