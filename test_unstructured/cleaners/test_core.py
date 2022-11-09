import pytest

import unstructured.cleaners.core as core


@pytest.mark.parametrize(
    "text, expected",
    [
        ("● An excellent point!", "An excellent point!"),
        ("● An excellent point! ●●●", "An excellent point! ●●●"),
        ("An excellent point!", "An excellent point!"),
        ("Morse code! ●●●", "Morse code! ●●●"),
    ],
)
def test_clean_bullets(text, expected):
    assert core.clean_bullets(text=text) == expected
    assert core.clean(text=text, bullets=True) == expected


@pytest.mark.parametrize(
    "text, expected",
    [
        ("\x93A lovely quote!\x94", "“A lovely quote!”"),
        ("\x91A lovely quote!\x92", "‘A lovely quote!’"),
    ],
)
def test_replace_unicode_quotes(text, expected):
    assert core.replace_unicode_quotes(text=text) == expected


@pytest.mark.parametrize(
    "text, expected",
    [
        ("“A lovely quote!”", "A lovely quote"),
        ("‘A lovely quote!’", "A lovely quote"),
        ("'()[]{};:'\",.?/\\-_", ""),
    ],
)
def test_remove_punctuation(text, expected):
    assert core.remove_punctuation(text) == expected


@pytest.mark.parametrize(
    "text, expected",
    [
        ("RISK\n\nFACTORS", "RISK FACTORS"),
        ("Item\xa01A", "Item 1A"),
        ("  Risk factors ", "Risk factors"),
        ("Risk   factors ", "Risk factors"),
    ],
)
def test_clean_extra_whitespace(text, expected):
    assert core.clean_extra_whitespace(text) == expected
    assert core.clean(text=text, extra_whitespace=True) == expected


@pytest.mark.parametrize(
    "text, expected",
    [
        ("Risk-factors", "Risk factors"),
        ("Risk – factors", "Risk   factors"),
        ("Risk\u2013factors", "Risk factors"),
        ("Risk factors-\u2013", "Risk factors"),
    ],
)
def test_clean_dashes(text, expected):
    assert core.clean_dashes(text) == expected
    assert core.clean(text=text, dashes=True) == expected


@pytest.mark.parametrize(
    "text, expected",
    [
        ("Item 1A:", "Item 1A"),
        ("Item 1A;", "Item 1A"),
        ("Item 1A.", "Item 1A"),
        ("Item 1A,", "Item 1A"),
        ("Item, 1A: ", "Item, 1A"),
    ],
)
def test_clean_trailing_punctuation(text, expected):
    assert core.clean_trailing_punctuation(text) == expected
    assert core.clean(text=text, trailing_punctuation=True) == expected


@pytest.mark.parametrize(
    "text, pattern, ignore_case, strip, expected",
    [
        ("SUMMARY: A great SUMMARY", r"(SUMMARY|DESC):", False, True, "A great SUMMARY"),
        ("DESC: A great SUMMARY", r"(SUMMARY|DESC):", False, True, "A great SUMMARY"),
        ("SUMMARY: A great SUMMARY", r"(SUMMARY|DESC):", False, False, " A great SUMMARY"),
        ("summary: A great SUMMARY", r"(SUMMARY|DESC):", True, True, "A great SUMMARY"),
    ],
)
def test_clean_prefix(text, pattern, ignore_case, strip, expected):
    assert core.clean_prefix(text, pattern, ignore_case, strip) == expected


@pytest.mark.parametrize(
    "text, pattern, ignore_case, strip, expected",
    [
        ("The END! END", r"(END|STOP)", False, True, "The END!"),
        ("The END! STOP", r"(END|STOP)", False, True, "The END!"),
        ("The END! END", r"(END|STOP)", False, False, "The END! "),
        ("The END! end", r"(END|STOP)", True, True, "The END!"),
    ],
)
def test_clean_postfix(text, pattern, ignore_case, strip, expected):
    assert core.clean_postfix(text, pattern, ignore_case, strip) == expected


@pytest.mark.parametrize(
    # NOTE(yuming): Tests combined cleaners
    "text, extra_whitespace, dashes, bullets, lowercase, trailing_punctuation, expected",
    [
        ("  Risk-factors ", True, True, False, False, False, "Risk factors"),
        ("● Point!  ●●● ", True, False, True, False, False, "Point! ●●●"),
        ("Risk- factors ", True, False, False, True, False, "risk- factors"),
        ("Risk   factors: ", True, False, False, False, True, "Risk factors"),
        ("● Risk-factors●●● ", False, True, True, False, False, "Risk factors●●●"),
        ("Risk-factors ", False, True, False, True, False, "risk factors"),
        ("Risk-factors: ", False, True, False, False, True, "Risk factors"),
        ("● Point! ●●● ", False, False, True, True, False, "point! ●●●"),
        ("● Point! ●●●: ", False, False, True, False, True, "Point! ●●●"),
        ("Risk factors: ", False, False, False, True, True, "risk factors"),
    ],
)
def test_clean(text, extra_whitespace, dashes, bullets, lowercase, trailing_punctuation, expected):
    assert (
        core.clean(
            text=text,
            extra_whitespace=extra_whitespace,
            dashes=dashes,
            bullets=bullets,
            trailing_punctuation=trailing_punctuation,
            lowercase=lowercase,
        )
        == expected
    )
