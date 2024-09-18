"""Test-suite for `unstructured.partition.common.metadata` module."""

from __future__ import annotations

import datetime as dt
import io
import os
import pathlib

import pytest

from unstructured.documents.elements import (
    CheckBox,
    ElementMetadata,
    FigureCaption,
    Header,
    ListItem,
    NarrativeText,
    Text,
    Title,
)
from unstructured.partition.common.metadata import (
    get_last_modified,
    get_last_modified_date,
    get_last_modified_date_from_file,
    set_element_hierarchy,
)

# ================================================================================================
# LAST-MODIFIED
# ================================================================================================


class Describe_get_last_modified:
    """Isolated unit-tests for `unstructured.partition.common.metadata.get_last_modified()."""

    def it_pulls_last_modified_from_the_filesystem_when_a_path_is_provided(
        self, file_and_last_modified: tuple[str, str]
    ):
        file_path, last_modified = file_and_last_modified
        last_modified_date = get_last_modified(str(file_path), None, False)
        assert last_modified_date == last_modified

    def and_it_pulls_last_modified_from_the_file_like_object_when_one_is_provided(
        self, file_and_last_modified: tuple[str, str]
    ):
        file_path, last_modified = file_and_last_modified
        with open(file_path, "rb") as f:
            last_modified_date = get_last_modified(None, f, True)
        assert last_modified_date == last_modified

    def but_not_when_date_from_file_object_is_False(self, file_and_last_modified: tuple[str, str]):
        file_path, _ = file_and_last_modified
        with open(file_path, "rb") as f:
            last_modified_date = get_last_modified(None, f, False)
        assert last_modified_date is None

    # -- fixtures --------------------------------------------------------------------------------

    @pytest.fixture()
    def file_and_last_modified(self, tmp_path: pathlib.Path) -> tuple[str, str]:
        modified_timestamp = dt.datetime(
            year=2024, month=6, day=14, hour=15, minute=39, second=25
        ).timestamp()
        file_path = tmp_path / "some_file.txt"
        file_path.write_text("abcdefg")
        os.utime(file_path, (modified_timestamp, modified_timestamp))
        return str(file_path), "2024-06-14T15:39:25"


class Describe_get_last_modified_date:
    def it_gets_the_modified_time_of_a_file_identified_by_a_path(self, tmp_path: pathlib.Path):
        modified_timestamp = dt.datetime(
            year=2024, month=3, day=5, hour=17, minute=43, second=40
        ).timestamp()
        file_path = tmp_path / "some_file.txt"
        file_path.write_text("abcdefg")
        os.utime(file_path, (modified_timestamp, modified_timestamp))

        last_modified_date = get_last_modified_date(str(file_path))

        assert last_modified_date == "2024-03-05T17:43:40"

    def but_it_returns_None_when_there_is_no_file_at_that_path(self, tmp_path: pathlib.Path):
        file_path = tmp_path / "some_file_that_does_not_exist.txt"

        last_modified_date = get_last_modified_date(str(file_path))

        assert last_modified_date is None


class Describe_get_last_modified_date_from_file:
    def it_gets_the_modified_time_of_a_file_like_object_corresponding_to_a_filesystem_file(
        self, tmp_path: pathlib.Path
    ):
        modified_timestamp = dt.datetime(
            year=2024, month=3, day=5, hour=20, minute=48, second=26
        ).timestamp()
        file_path = tmp_path / "some_file_2.txt"
        file_path.write_text("abcdefg")
        os.utime(file_path, (modified_timestamp, modified_timestamp))

        with open(file_path, "rb") as f:
            last_modified_date = get_last_modified_date_from_file(f)

        assert last_modified_date == "2024-03-05T20:48:26"

    def but_it_returns_None_when_the_argument_is_a_bytes_object(self):
        assert get_last_modified_date_from_file(b"abcdefg") is None

    def and_it_returns_None_when_the_file_like_object_has_no_name_attribute(self):
        file = io.BytesIO(b"abcdefg")
        assert hasattr(file, "name") is False

        last_modified_date = get_last_modified_date_from_file(file)

        assert last_modified_date is None

    def and_it_returns_None_when_the_file_like_object_name_is_not_a_path_to_a_file(
        self, tmp_path: pathlib.Path
    ):
        file = io.BytesIO(b"abcdefg")
        file.name = str(tmp_path / "a_file_that_isn't_here.txt")

        last_modified_date = get_last_modified_date_from_file(file)

        assert last_modified_date is None


# ================================================================================================
# ELEMENT HIERARCHY
# ================================================================================================


def test_set_element_hierarchy():
    elements_to_set = [
        Title(text="Title"),  # 0
        NarrativeText(text="NarrativeText"),  # 1
        FigureCaption(text="FigureCaption"),  # 2
        ListItem(text="ListItem"),  # 3
        ListItem(text="ListItem", metadata=ElementMetadata(category_depth=1)),  # 4
        ListItem(text="ListItem", metadata=ElementMetadata(category_depth=1)),  # 5
        ListItem(text="ListItem"),  # 6
        CheckBox(element_id="some-id-1", checked=True),  # 7
        Title(text="Title 2"),  # 8
        ListItem(text="ListItem"),  # 9
        ListItem(text="ListItem"),  # 10
        Text(text="Text"),  # 11
    ]
    elements = set_element_hierarchy(elements_to_set)

    assert (
        elements[1].metadata.parent_id == elements[0].id
    ), "NarrativeText should be child of Title"
    assert (
        elements[2].metadata.parent_id == elements[0].id
    ), "FigureCaption should be child of Title"
    assert elements[3].metadata.parent_id == elements[0].id, "ListItem should be child of Title"
    assert elements[4].metadata.parent_id == elements[3].id, "ListItem should be child of Title"
    assert elements[5].metadata.parent_id == elements[3].id, "ListItem should be child of Title"
    assert elements[6].metadata.parent_id == elements[0].id, "ListItem should be child of Title"
    # NOTE(Hubert): moving the category field to Element, caused this to fail.
    # Checkboxes will soon be deprecated, then we can remove the test.
    # assert (
    #         elements[7].metadata.parent_id is None
    # ), "CheckBox should be None, as it's not a Text based element"
    assert elements[8].metadata.parent_id is None, "Title 2 should be child of None"
    assert elements[9].metadata.parent_id == elements[8].id, "ListItem should be child of Title 2"
    assert elements[10].metadata.parent_id == elements[8].id, "ListItem should be child of Title 2"
    assert elements[11].metadata.parent_id == elements[8].id, "Text should be child of Title 2"


def test_set_element_hierarchy_custom_rule_set():
    elements_to_set = [
        Header(text="Header"),  # 0
        Title(text="Title"),  # 1
        NarrativeText(text="NarrativeText"),  # 2
        Text(text="Text"),  # 3
        Title(text="Title 2"),  # 4
        FigureCaption(text="FigureCaption"),  # 5
    ]

    custom_rule_set = {
        "Header": ["Title", "Text"],
        "Title": ["NarrativeText", "UncategorizedText", "FigureCaption"],
    }

    elements = set_element_hierarchy(
        elements=elements_to_set,
        ruleset=custom_rule_set,
    )

    assert elements[1].metadata.parent_id == elements[0].id, "Title should be child of Header"
    assert (
        elements[2].metadata.parent_id == elements[1].id
    ), "NarrativeText should be child of Title"
    assert elements[3].metadata.parent_id == elements[1].id, "Text should be child of Title"
    assert elements[4].metadata.parent_id == elements[0].id, "Title 2 should be child of Header"
    assert (
        elements[5].metadata.parent_id == elements[4].id
    ), "FigureCaption should be child of Title 2"
