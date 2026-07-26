from cad_tui.domain.icons import icon_for_title


def test_matches_a_default_keyword_case_insensitively() -> None:
    assert icon_for_title("Book a Flight to Tokyo") == "✈"
    assert icon_for_title("SKI trip") is not None


def test_no_match_returns_none() -> None:
    assert icon_for_title("Finish the quarterly report") is None


def test_longest_keyword_wins_when_multiple_match() -> None:
    # "trip" and "beach" both match; "beach" (5 chars) beats "trip" (4 chars)
    assert icon_for_title("beach trip") == "⛱"


def test_override_replaces_default_icon() -> None:
    assert icon_for_title("Team standup", overrides={"standup": "🔔"}) == "🔔"


def test_override_adds_new_keyword() -> None:
    assert icon_for_title("Water the plants", overrides={"water the plants": "🪴"}) == "🪴"
