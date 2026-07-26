"""Minimal RFC 5545 VEVENT reader — enough to show read-only events synced
from a local .ics file or a remote .ics URL (iCloud/Google Calendar share
links, etc). Does not expand RRULE recurrence: a recurring event shows only
its first occurrence. That's a known, documented limitation, not a bug —
full recurrence expansion is a much bigger feature than "view my events"."""

from __future__ import annotations

import urllib.request
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ParsedEvent:
    uid: str
    title: str
    start_at: str  # "YYYY-MM-DD" or "YYYY-MM-DD HH:MM"
    end_at: str | None
    all_day: bool
    location: str | None
    notes: str | None


def fetch_ics_text(source: str, timeout: float = 5.0) -> str:
    """Reads raw .ics content from a local path or an http(s) URL.

    Raises on failure (network error, missing file, ...) — this is
    intentionally best-effort at the *caller's* level (see IcsService),
    not swallowed here, so a caller can decide what "failed to sync"
    means for that specific source.
    """
    if source.startswith(("http://", "https://")):
        with urllib.request.urlopen(source, timeout=timeout) as response:
            return response.read().decode("utf-8", errors="replace")
    return Path(source).expanduser().read_text(encoding="utf-8", errors="replace")


def parse_ics(text: str) -> list[ParsedEvent]:
    """Parses every VEVENT block in `text` into a flat list of events."""
    events: list[ParsedEvent] = []
    current: dict[str, object] | None = None
    for line in _unfold_lines(text):
        name, params, value = _split_property(line)
        if name == "BEGIN" and value == "VEVENT":
            current = {}
            continue
        if name == "END" and value == "VEVENT":
            if current is not None and "start_at" in current:
                events.append(_finish_event(current, len(events)))
            current = None
            continue
        if current is None:
            continue
        _apply_property(current, name, params, value)
    return events


def _get_str(current: dict[str, object], key: str) -> str | None:
    value = current.get(key)
    return value if isinstance(value, str) else None


def _finish_event(current: dict[str, object], index: int) -> ParsedEvent:
    return ParsedEvent(
        uid=str(current.get("uid") or f"noid-{index}"),
        title=str(current.get("title") or "(untitled)"),
        start_at=str(current["start_at"]),
        end_at=_get_str(current, "end_at"),
        all_day=bool(current.get("all_day", False)),
        location=_get_str(current, "location"),
        notes=_get_str(current, "notes"),
    )


def _apply_property(
    current: dict[str, object], name: str, params: dict[str, str], value: str
) -> None:
    if name == "UID":
        current["uid"] = value
    elif name == "SUMMARY":
        current["title"] = _unescape(value)
    elif name == "DTSTART":
        start_at, all_day = _parse_dt(value, params)
        current["start_at"] = start_at
        current["all_day"] = all_day
    elif name == "DTEND":
        end_at, _ = _parse_dt(value, params)
        current["end_at"] = end_at
    elif name == "LOCATION":
        current["location"] = _unescape(value)
    elif name == "DESCRIPTION":
        current["notes"] = _unescape(value)


def _unfold_lines(text: str) -> list[str]:
    """RFC5545 line folding: a line starting with a space/tab is a
    continuation of the previous line, not a new property."""
    lines: list[str] = []
    for raw_line in text.replace("\r\n", "\n").split("\n"):
        if raw_line.startswith((" ", "\t")) and lines:
            lines[-1] += raw_line[1:]
        elif raw_line:
            lines.append(raw_line)
    return lines


def _split_property(line: str) -> tuple[str, dict[str, str], str]:
    """Splits "NAME;PARAM=X:VALUE" into (NAME, {PARAM: X}, VALUE)."""
    head, _, value = line.partition(":")
    name, *param_parts = head.split(";")
    params: dict[str, str] = {}
    for part in param_parts:
        key, _, val = part.partition("=")
        params[key.upper()] = val
    return name.upper(), params, value


def _parse_dt(value: str, params: dict[str, str]) -> tuple[str, bool]:
    """Normalizes an ICS DATE or DATE-TIME value to "YYYY-MM-DD[ HH:MM]"."""
    value = value.strip()
    if params.get("VALUE") == "DATE" or (len(value) == 8 and value.isdigit()):
        return f"{value[0:4]}-{value[4:6]}-{value[6:8]}", True
    date_part = value[0:8]
    normalized = f"{date_part[0:4]}-{date_part[4:6]}-{date_part[6:8]}"
    if len(value) >= 13:
        normalized += f" {value[9:11]}:{value[11:13]}"
    return normalized, False


def _unescape(value: str) -> str:
    return value.replace("\\n", "\n").replace("\\,", ",").replace("\\;", ";").replace("\\\\", "\\")
