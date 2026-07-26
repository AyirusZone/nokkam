"""Best-effort icon for a task, guessed from keywords in its title."""

from __future__ import annotations

# Matching is a case-insensitive substring search over the title; when
# multiple keywords match, the longest (most specific) one wins regardless
# of dict order, so e.g. a title containing both "trip" and "beach" always
# resolves the same way rather than depending on iteration order.
DEFAULT_ICON_KEYWORDS: dict[str, str] = {
    "flight": "✈",
    "fly": "✈",
    "airport": "✈",
    "ski": "⛷",
    "snowboard": "🏂",
    "beach": "⛱",
    "vacation": "🏖",
    "holiday": "🏖",
    "gym": "💪",
    "workout": "💪",
    "run": "🏃",
    "birthday": "🎂",
    "party": "🎉",
    "meeting": "👥",
    "standup": "👥",
    "call": "📞",
    "doctor": "🩺",
    "dentist": "🦷",
    "haircut": "💇",
    "shopping": "🛒",
    "groceries": "🛒",
    "movie": "🎬",
    "dinner": "🍽",
    "lunch": "🍽",
    "breakfast": "🍳",
    "coffee": "☕",
    "book": "📖",
    "read": "📖",
    "study": "📚",
    "class": "📚",
    "exam": "📝",
    "wedding": "💍",
    "anniversary": "💍",
    "concert": "🎵",
    "music": "🎵",
    "travel": "🧳",
    "trip": "🧳",
    "hike": "🥾",
    "hiking": "🥾",
    "yoga": "🧘",
    "drive": "🚗",
    "train": "🚆",
    "bike": "🚲",
    "cycling": "🚲",
}


def icon_for_title(title: str, overrides: dict[str, str] | None = None) -> str | None:
    """Best-effort icon for `title`, or None if nothing matches.

    `overrides` (from config.toml's `[icons]` table) are merged over the
    built-in keywords, so a user-defined keyword can replace a default
    one's icon or add a brand-new keyword.
    """
    keywords = DEFAULT_ICON_KEYWORDS if not overrides else {**DEFAULT_ICON_KEYWORDS, **overrides}
    lowered = title.lower()
    best: tuple[int, str] | None = None
    for keyword, icon in keywords.items():
        if keyword.lower() in lowered and (best is None or len(keyword) > best[0]):
            best = (len(keyword), icon)
    return best[1] if best else None
