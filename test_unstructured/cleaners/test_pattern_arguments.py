import re

import pytest

from unstructured.cleaners.core import (
    auto_paragraph_grouper,
    group_broken_paragraphs,
    new_line_grouper,
)


TEXT = "The big red fox\nis walking down the lane."
LINE_SPLIT = r"\s*\n\s*"


def test_group_broken_paragraphs_accepts_string_patterns():
    grouped = group_broken_paragraphs(TEXT, line_split=LINE_SPLIT)

    assert grouped == "The big red fox is walking down the lane."


def test_new_line_grouper_accepts_a_string_pattern():
    grouped = new_line_grouper(TEXT, paragraph_split=LINE_SPLIT)

    assert grouped == "The big red fox\n\nis walking down the lane."


def test_auto_paragraph_grouper_accepts_a_string_pattern():
    assert auto_paragraph_grouper(TEXT, line_split=LINE_SPLIT) == TEXT


def test_invalid_string_pattern_fails_loudly():
    with pytest.raises(re.error):
        new_line_grouper(TEXT, paragraph_split="[")
