"""Turns the [keys] config table into a Textual keymap, reporting mistakes.

Every configurable binding carries an `id` equal to its action name, so
`[keys] add_task = "n"` rebinds it. Only the home screen and app-level
bindings are configurable; modal dialogs keep their fixed keys.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable

from textual.binding import Binding


def split_keys(spec: str) -> list[str]:
    return [k.strip() for k in spec.split(",") if k.strip()]


def build_keymap(
    configured: dict[str, str], defaults: Iterable[Binding]
) -> tuple[dict[str, str], list[str]]:
    """Returns (keymap to apply, warnings). Unknown binding ids are dropped;
    a key that ends up bound to two actions (where one was configured) is
    still applied but reported, since the user asked for it."""
    defaults = list(defaults)
    known = {b.id: b.key for b in defaults if b.id}
    warnings: list[str] = []
    keymap: dict[str, str] = {}

    for binding_id, spec in configured.items():
        if binding_id not in known:
            warnings.append(
                f"Unknown key binding '{binding_id}' in [keys] "
                f"(available: {', '.join(sorted(known))})"
            )
        elif not split_keys(spec):
            warnings.append(f"[keys] {binding_id} has no key (ignored)")
        else:
            keymap[binding_id] = spec

    effective = {**known, **keymap}
    owners: dict[str, list[str]] = defaultdict(list)
    for binding_id, spec in effective.items():
        for key in split_keys(spec):
            owners[key].append(binding_id)
    for key, ids in sorted(owners.items()):
        if len(ids) > 1 and any(i in keymap for i in ids):
            warnings.append(f"Key '{key}' is bound to both {' and '.join(sorted(ids))}")
    return keymap, warnings
