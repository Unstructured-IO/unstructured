import re

import pytest

from unstructured.cleaners import core


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            "\x88This text contains non-ascii characters!\x88",
            "This text contains non-ascii characters!",
        ),
        ("\x93A lovely quote!\x94", "A lovely quote!"),
        ("● An excellent point! ●●●", " An excellent point! "),
        ("Item\xa01A", "Item1A"),
        ("Our dog&apos;s bowl.", "Our dog&apos;s bowl."),
        ("5 w=E2=80=99s", "5 w=E2=80=99s"),
    ],
)
def test_clean_non_ascii_chars(text, expected):
    assert core.clean_non_ascii_chars(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
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
    ("text", "expected"),
    [
        ("1. Introduction:", "Introduction:"),
        ("a. Introduction:", "Introduction:"),
        ("20.3 Morse code ●●●", "Morse code ●●●"),
        ("5.3.1 Convolutional Networks ", "Convolutional Networks"),
        ("D.b.C Recurrent Neural Networks", "Recurrent Neural Networks"),
        ("2.b.1 Recurrent Neural Networks", "Recurrent Neural Networks"),
        ("eins. Neural Networks", "eins. Neural Networks"),
        ("bb.c Feed Forward Neural Networks", "Feed Forward Neural Networks"),
        ("aaa.ccc Metrics", "aaa.ccc Metrics"),
        (" version = 3.8", " version = 3.8"),
        ("1 2. 3 4", "1 2. 3 4"),
        ("1) 2. 3 4", "1) 2. 3 4"),
        ("2,3. Morse code 3. ●●●", "2,3. Morse code 3. ●●●"),
        ("1..2.3 four", "1..2.3 four"),
        ("Fig. 2: The relationship", "Fig. 2: The relationship"),
        ("23 is everywhere", "23 is everywhere"),
    ],
)
def test_clean_ordered_bullets(text, expected):
    assert core.clean_ordered_bullets(text=text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("The æther is a classic element.", "The aether is a classic element."),
        ("In old texts, Æsop's fables are", "In old texts, AEsop's fables are"),
        ("The buﬀer zone is there.", "The buffer zone is there."),
        ("The ﬁle was found in the system.", "The file was found in the system."),
        ("She had a ﬂower in her hair.", "She had a flower in her hair."),
        ("The coﬃn was placed in the grave.", "The coffin was placed in the grave."),
        ("The buﬄe zone was clearly marked.", "The buffle zone was clearly marked."),
        ("The craﬅsman worked with dedication.", "The craftsman worked with dedication."),
        ("The symbol ʪ is very rare.", "The symbol ls is very rare."),
        ("The word 'cœur' means 'heart' in French.", "The word 'coeur' means 'heart' in French."),
        ("The word 'Œuvre' refers to the works", "The word 'OEuvre' refers to the works"),
        ("The ȹ symbol is used in some contexts.", "The qp symbol is used in some contexts."),
        ("The poﬆman delivers mail daily.", "The postman delivers mail daily."),
        (
            "The symbol ʦ can be found in certain alphabets.",
            "The symbol ts can be found in certain alphabets.",
        ),
    ],
)
def test_clean_ligatures(text, expected):
    assert core.clean_ligatures(text=text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("\x93A lovely quote!\x94", "“A lovely quote!”"),
        ("\x91A lovely quote!\x92", "‘A lovely quote!’"),
        ("Our dog&apos;s bowl.", "Our dog's bowl."),
    ],
)
def test_replace_unicode_quotes(text, expected):
    assert core.replace_unicode_quotes(text=text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [("5 w=E2=80=99s", "5 w’s")],
)
def test_replace_mime_encodings(text, expected):
    assert core.replace_mime_encodings(text=text) == expected


def test_replace_mime_encodings_works_with_different_encodings():
    text = "5 w=E2=80-99s=E2=80-92"
    assert core.replace_mime_encodings(text=text, encoding="latin-1") == "5 wâ\x80-99sâ\x80-92"


def test_replace_mime_encodings_works_with_right_to_left_encodings():
    text = "=EE=E0=E9=E4"
    assert core.replace_mime_encodings(text=text, encoding="iso-8859-8") == "מאיה"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("“A lovely quote!”", "A lovely quote"),
        ("‘A lovely quote!’", "A lovely quote"),
        ("'()[]{};:'\",.?/\\-_", ""),
    ],
)
def test_remove_punctuation(text, expected):
    assert core.remove_punctuation(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
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
    ("text", "expected"),
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
    ("text", "expected"),
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
    ("text", "pattern", "ignore_case", "strip", "expected"),
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
    ("text", "pattern", "ignore_case", "strip", "expected"),
    [
        ("The END! END", r"(END|STOP)", False, True, "The END!"),
        ("The END! STOP", r"(END|STOP)", False, True, "The END!"),
        ("The END! END", r"(END|STOP)", False, False, "The END! "),
        ("The END! end", r"(END|STOP)", True, True, "The END!"),
    ],
)
def test_clean_postfix(text, pattern, ignore_case, strip, expected):
    assert core.clean_postfix(text, pattern, ignore_case, strip) == expected


def test_group_broken_paragraphs():
    text = """The big red fox
is walking down the lane.

At the end of the lane
the fox met a friendly bear."""

    assert (
        core.group_broken_paragraphs(text)
        == """The big red fox is walking down the lane.

At the end of the lane the fox met a friendly bear."""
    )


def test_group_broken_paragraphs_non_default_settings():
    text = """The big red fox

is walking down the lane.


At the end of the lane

the fox met a friendly bear."""

    para_split_re = re.compile(r"(\s*\n\s*){3}")

    clean_text = core.group_broken_paragraphs(text, paragraph_split=para_split_re)
    assert (
        clean_text
        == """The big red fox is walking down the lane.

At the end of the lane the fox met a friendly bear."""
    )


def test_group_broken_paragraphs_with_bullets():
    text = """○The big red fox
is walking down the lane.

○At the end of the lane
the fox met a friendly bear."""
    assert core.group_bullet_paragraph(text) == [
        "○The big red fox is walking down the lane. ",
        "○At the end of the lane the fox met a friendly bear.",
    ]


def test_group_bullet_paragraph_with_e_bullets():
    text = """e The big red fox
is walking down the lane.

e At the end of the lane
the fox met a friendly bear."""
    assert core.group_bullet_paragraph(text) == [
        "· The big red fox is walking down the lane. ",
        "· At the end of the lane the fox met a friendly bear.",
    ]


@pytest.mark.parametrize(
    # NOTE(yuming): Tests combined cleaners
    (
        "text",
        "extra_whitespace",
        "dashes",
        "bullets",
        "lowercase",
        "trailing_punctuation",
        "expected",
    ),
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


def test_bytes_string_to_string():
    text = "\xe6\xaf\x8f\xe6\x97\xa5\xe6\x96\xb0\xe9\x97\xbb"
    assert core.bytes_string_to_string(text, "utf-8") == "每日新闻"
