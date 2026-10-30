"""Tests for the enumerated bullet pattern used when splitting list blocks."""

import pytest

from unstructured.nlp.patterns import ENUMERATED_BULLETS_RE
from unstructured.partition.common.common import layout_list_to_list_items

BULLET = "\u2022"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        # numeric bullets keep splitting exactly as before
        ("1. foo\n2. bar", ["foo", "bar"]),
        ("1.1 This is a very important point", ["This is a very important point"]),
        ("1.1.1 Deep point", ["Deep point"]),
        # a single letter is a bullet marker too, like the ordered-bullet helpers say
        ("a. foo\nb. bar", ["foo", "bar"]),
        ("A. foo\nB. bar", ["foo", "bar"]),
        ("a. one\nb. two\nc. three", ["one", "two", "three"]),
        ("a. only one item", ["only one item"]),
        ("  a. indented\n  b. indented", ["indented", "indented"]),
        # a lead-in line stays its own item
        ("Consider the following:\na. foo\nb. bar", ["Consider the following:", "foo", "bar"]),
        # a block can mix enumerated markers with bullet glyphs, in either order
        (
            "a. heading\n" + BULLET + " first\n" + BULLET + " second",
            ["heading", "first", "second"],
        ),
        (BULLET + " first\na. heading\nb. other", ["first", "heading", "other"]),
        ("1. first\n" + BULLET + " second", ["first", "second"]),
        # abbreviations and prose are not bullets
        ("e. g. spaced example", ["e. g. spaced example"]),
        ("e.  g. spaced example", ["e.  g. spaced example"]),
        ("e. \tg. spaced example", ["e. \tg. spaced example"]),
        ("e.\tg. spaced example", ["e.\tg. spaced example"]),
        ("i. e. the letter", ["i. e. the letter"]),
        ("a cat sat on a mat.", ["a cat sat on a mat."]),
        ("See section A. Appendix", ["See section A. Appendix"]),
    ],
)
def test_layout_list_to_list_items_splits_enumerated_bullets(text, expected):
    elements = layout_list_to_list_items(text, None, None, None, None)
    assert [element.text for element in elements] == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1. foo\n2. bar", ["", " foo\n", " bar"]),
        ("a. foo\nb. bar", ["", " foo\n", " bar"]),
        ("A. foo\nB. bar", ["", " foo\n", " bar"]),
        ("a. only one item", ["", " only one item"]),
        ("e. g. spaced example", ["e. g. spaced example"]),
        ("e.  g. spaced example", ["e.  g. spaced example"]),
        ("e. \tg. spaced example", ["e. \tg. spaced example"]),
        ("i. e. the letter", ["i. e. the letter"]),
        ("a cat sat on a mat.", ["a cat sat on a mat."]),
    ],
)
def test_enumerated_bullets_re_splits_lettered_and_numeric_bullets(text, expected):
    assert ENUMERATED_BULLETS_RE.split(text) == expected
