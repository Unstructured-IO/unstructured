import re

import pytest

from unstructured.cleaners.core import (
    auto_paragraph_grouper,
    blank_line_grouper,
    new_line_grouper,
)


@pytest.mark.parametrize("sample_size", [1, 2, 2000])
def test_blank_lines_after_the_sample_do_not_change_the_selected_grouper(sample_size):
    text = "A complete line of document text.\n" * sample_size + "\n" * 20 + "Final content."

    assert auto_paragraph_grouper(text, max_line_count=sample_size) == new_line_grouper(text)


@pytest.mark.parametrize("sample_size", [2, 2000, 5000])
def test_short_documents_use_their_actual_sample_size(sample_size):
    text = "The first paragraph has several useful words.\n\nThe last paragraph does too."

    assert auto_paragraph_grouper(text, max_line_count=sample_size) == blank_line_grouper(text)


def test_capturing_groups_keep_their_existing_sampling_semantics():
    text = "The first line has several useful words.\nThe next line also has useful words."

    assert auto_paragraph_grouper(
        text, line_split=re.compile(r"(\n)"), max_line_count=2
    ) == blank_line_grouper(text)


def test_custom_line_pattern_only_affects_grouper_selection():
    text = "The first paragraph has several useful words.| |The final paragraph has more words."

    assert auto_paragraph_grouper(
        text, line_split=re.compile(r"\|"), max_line_count=2
    ) == blank_line_grouper(text)


def test_empty_input_still_returns_empty_text():
    assert auto_paragraph_grouper("") == ""
