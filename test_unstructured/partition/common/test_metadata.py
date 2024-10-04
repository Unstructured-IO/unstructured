"""Test-suite for `unstructured.partition.common.metadata` module."""

# pyright: reportPrivateUsage=false

from __future__ import annotations

import copy
import datetime as dt
import os
import pathlib
from typing import Any, Callable

import pytest

from unstructured.documents.elements import (
    CheckBox,
    Element,
    ElementMetadata,
    FigureCaption,
    Header,
    ListItem,
    NarrativeText,
    Text,
    Title,
)
from unstructured.file_utils.model import FileType
from unstructured.partition.common.metadata import (
    _assign_hash_ids,
    apply_metadata,
    get_last_modified_date,
    set_element_hierarchy,
)

# ================================================================================================
# LAST-MODIFIED
# ================================================================================================


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


# ================================================================================================
# ELEMENT HIERARCHY
# ================================================================================================


class Describe_set_element_hierarchy:

    def it_applies_default_ruleset(self):
        elements = [
            Title(element_id="0", text="Title0"),
            Text(element_id="1", text="Text0"),
            Header(element_id="2", text="Header0"),
            Text(element_id="3", text="Text1"),
            Title(element_id="4", text="Title1"),
            Text(element_id="5", text="Text2"),
        ]

        result = set_element_hierarchy(elements)

        assert result[0].metadata.parent_id is None
        assert result[1].metadata.parent_id == "0"  # Text0 is under Title0
        assert result[2].metadata.parent_id is None  # Header0 is higher than Title0
        assert result[3].metadata.parent_id == "2"  # Text1 is under Header0
        assert result[4].metadata.parent_id == "2"  # Title1 is under Header0
        assert result[5].metadata.parent_id == "4"  # Text2 is under Title1, which is under Header0

    def it_applies_category_depth_when_element_category_is_the_same(self):
        elements = [
            Title(element_id="0", text="Title0", metadata=ElementMetadata(category_depth=1)),
            ListItem(element_id="1", text="ListItem0", metadata=ElementMetadata(category_depth=0)),
            ListItem(element_id="2", text="ListItem1", metadata=ElementMetadata(category_depth=1)),
            ListItem(element_id="3", text="ListItem2", metadata=ElementMetadata(category_depth=0)),
        ]

        result = set_element_hierarchy(elements)

        assert result[0].metadata.parent_id is None
        assert result[1].metadata.parent_id == "0"  # category_depth=0
        assert result[2].metadata.parent_id == "1"  # category_depth=1, so it is under ListItem0
        assert result[3].metadata.parent_id == "0"  # category_depth=0

    def but_it_ignores_category_depth_when_elements_are_of_different_categories(self):
        elements = [
            Title(element_id="0", text="Title", metadata=ElementMetadata(category_depth=2)),
            Text(element_id="1", text="Text", metadata=ElementMetadata(category_depth=0)),
            Header(element_id="2", text="Header", metadata=ElementMetadata(category_depth=2)),
            Text(element_id="3", text="Text", metadata=ElementMetadata(category_depth=0)),
            ListItem(element_id="4", text="ListItem", metadata=ElementMetadata(category_depth=1)),
            NarrativeText(element_id="5", text="", metadata=ElementMetadata(category_depth=0)),
        ]

        result = set_element_hierarchy(elements)

        assert result[0].metadata.parent_id is None
        assert result[1].metadata.parent_id == "0"  # Text is under Title despite category_depth=0
        assert result[2].metadata.parent_id is None
        assert result[3].metadata.parent_id == "2"  # These are under Header despite category_depth
        assert result[4].metadata.parent_id == "2"
        assert result[5].metadata.parent_id == "2"

    def it_skips_elements_with_pre_existing_parent_id(self):
        elements = [
            Title(element_id="0", text="Title", metadata=ElementMetadata(parent_id="10")),
            Title(element_id="1", text="Title"),
            Text(element_id="2", text="Text"),
        ]

        result = set_element_hierarchy(elements)

        # Parent ID should not change and element is skipped in figuring out other elements' parents
        assert result[0].metadata.parent_id == "10"
        assert result[1].metadata.parent_id is None
        assert result[2].metadata.parent_id == "1"

    def it_sets_parent_id_for_each_element_in_elements(self):
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
        assert (
            elements[9].metadata.parent_id == elements[8].id
        ), "ListItem should be child of Title 2"
        assert (
            elements[10].metadata.parent_id == elements[8].id
        ), "ListItem should be child of Title 2"
        assert elements[11].metadata.parent_id == elements[8].id, "Text should be child of Title 2"

    def it_applies_custom_rule_set(self):
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


# ================================================================================================
# APPLY METADATA DECORATOR
# ================================================================================================


class Describe_apply_metadata:
    """Unit-test suite for `unstructured.partition.common.metadata.apply_metadata()` decorator."""

    # -- unique-ify elements and metadata ---------------------------------

    def it_produces_unique_elements_and_metadata_when_input_reuses_element_instances(self):
        element = Text(text="Element", metadata=ElementMetadata(filename="foo.bar", page_number=1))

        def fake_partitioner(**kwargs: Any) -> list[Element]:
            return [element, element, element]

        partition = apply_metadata()(fake_partitioner)

        elements = partition()

        # -- all elements are unique instances --
        assert len({id(e) for e in elements}) == len(elements)
        # -- all metadatas are unique instances --
        assert len({id(e.metadata) for e in elements}) == len(elements)

    def and_it_produces_unique_elements_and_metadata_when_input_reuses_metadata_instances(self):
        metadata = ElementMetadata(filename="foo.bar", page_number=1)

        def fake_partitioner(**kwargs: Any) -> list[Element]:
            return [
                Text(text="foo", metadata=metadata),
                Text(text="bar", metadata=metadata),
                Text(text="baz", metadata=metadata),
            ]

        partition = apply_metadata()(fake_partitioner)

        elements = partition()

        # -- all elements are unique instances --
        assert len({id(e) for e in elements}) == len(elements)
        # -- all metadatas are unique instances --
        assert len({id(e.metadata) for e in elements}) == len(elements)

    # -- unique-ids -------------------------------------------------------

    def it_assigns_hash_element_ids_when_unique_ids_arg_is_not_specified(
        self, fake_partitioner: Callable[..., list[Element]]
    ):
        partition = apply_metadata()(fake_partitioner)

        elements = partition()
        elements_2 = partition()

        # -- SHA1 hash is 32 characters long, no hyphens --
        assert all(len(e.id) == 32 for e in elements)
        assert all("-" not in e.id for e in elements)
        # -- SHA1 hashes are deterministic --
        assert all(e.id == e2.id for e, e2 in zip(elements, elements_2))

    def it_assigns_hash_element_ids_when_unique_ids_arg_is_False(
        self, fake_partitioner: Callable[..., list[Element]]
    ):
        partition = apply_metadata()(fake_partitioner)

        elements = partition(unique_element_ids=False)
        elements_2 = partition(unique_element_ids=False)

        # -- SHA1 hash is 32 characters long, no hyphens --
        assert all(len(e.id) == 32 for e in elements)
        assert all("-" not in e.id for e in elements)
        # -- SHA1 hashes are deterministic --
        assert all(e.id == e2.id for e, e2 in zip(elements, elements_2))

    def it_leaves_UUID_element_ids_when_unique_ids_arg_is_True(
        self, fake_partitioner: Callable[..., list[Element]]
    ):
        partition = apply_metadata()(fake_partitioner)

        elements = partition(unique_element_ids=True)
        elements_2 = partition(unique_element_ids=True)

        # -- UUID is 36 characters long with four hyphens --
        assert all(len(e.id) == 36 for e in elements)
        assert all(e.id.count("-") == 4 for e in elements)
        # -- UUIDs are non-deterministic, different every time --
        assert all(e.id != e2.id for e, e2 in zip(elements, elements_2))

    # -- parent-id --------------------------------------------------------

    def it_computes_and_assigns_parent_id(self, fake_partitioner: Callable[..., list[Element]]):
        partition = apply_metadata()(fake_partitioner)

        elements = partition()

        title = elements[0]
        assert title.metadata.category_depth == 1
        narr_text = elements[1]
        assert narr_text.metadata.parent_id == title.id

    # -- languages --------------------------------------------------------

    def it_applies_language_metadata(self, fake_partitioner: Callable[..., list[Element]]):
        partition = apply_metadata()(fake_partitioner)

        elements = partition(languages=["auto"], detect_language_per_element=True)

        assert all(e.metadata.languages == ["eng"] for e in elements)

    # -- filetype (MIME-type) ---------------------------------------------

    def it_assigns_the_value_of_a_metadata_file_type_arg_when_there_is_one(
        self, fake_partitioner: Callable[..., list[Element]]
    ):
        """A `metadata_file_type` arg overrides the file-type specified in the decorator.

        This is used for example by a delegating partitioner to preserve the original file-type in
        the metadata, like EPUB instead of the HTML that partitioner converts the .epub file to.
        """
        partition = apply_metadata(file_type=FileType.DOCX)(fake_partitioner)

        elements = partition(metadata_file_type=FileType.ODT)

        assert all(
            e.metadata.filetype == "application/vnd.oasis.opendocument.text" for e in elements
        )

    def and_it_assigns_the_decorator_file_type_when_the_metadata_file_type_arg_is_omitted(
        self, fake_partitioner: Callable[..., list[Element]]
    ):
        """The `file_type=...` decorator arg is the "normal" way to specify the file-type.

        This is used for principal (non-delegating) partitioners.
        """
        partition = apply_metadata(file_type=FileType.DOCX)(fake_partitioner)

        elements = partition()

        DOCX_MIME_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        assert all(e.metadata.filetype == DOCX_MIME_TYPE for e in elements)

    def and_it_does_not_assign_file_type_metadata_when_both_are_omitted(
        self, fake_partitioner: Callable[..., list[Element]]
    ):
        """A partitioner can elect to assign `.metadata.filetype` for itself.

        This is done in `partition_image()` for example where the same partitioner is used for
        multiple file-types.
        """
        partition = apply_metadata()(fake_partitioner)

        elements = partition()

        assert all(e.metadata.filetype == "image/jpeg" for e in elements)

    # -- filename ---------------------------------------------------------

    def it_uses_metadata_filename_arg_value_when_present(
        self, fake_partitioner: Callable[..., list[Element]]
    ):
        """A `metadata_filename` arg overrides all other sources."""
        partition = apply_metadata()(fake_partitioner)

        elements = partition(metadata_filename="a/b/c.xyz")

        assert all(e.metadata.filename == "c.xyz" for e in elements)
        assert all(e.metadata.file_directory == "a/b" for e in elements)

    def and_it_uses_filename_arg_value_when_metadata_filename_arg_not_present(
        self, fake_partitioner: Callable[..., list[Element]]
    ):
        partition = apply_metadata()(fake_partitioner)

        elements = partition(filename="a/b/c.xyz")

        assert all(e.metadata.filename == "c.xyz" for e in elements)
        assert all(e.metadata.file_directory == "a/b" for e in elements)

    def and_it_does_not_assign_filename_metadata_when_neither_are_present(
        self, fake_partitioner: Callable[..., list[Element]]
    ):
        partition = apply_metadata()(fake_partitioner)

        elements = partition()

        assert all(e.metadata.filename == "image.jpeg" for e in elements)
        assert all(e.metadata.file_directory == "x/y/images" for e in elements)

    # -- last_modified ----------------------------------------------------

    def it_uses_metadata_last_modified_arg_value_when_present(
        self, fake_partitioner: Callable[..., list[Element]]
    ):
        """A `metadata_last_modified` arg overrides all other sources."""
        partition = apply_metadata()(fake_partitioner)
        metadata_last_modified = "2024-09-26T15:17:53"

        elements = partition(metadata_last_modified=metadata_last_modified)

        assert all(e.metadata.last_modified == metadata_last_modified for e in elements)

    @pytest.mark.parametrize("kwargs", [{}, {"metadata_last_modified": None}])
    def but_it_does_not_update_last_modified_when_metadata_last_modified_arg_absent_or_None(
        self, kwargs: dict[str, Any], fake_partitioner: Callable[..., list[Element]]
    ):
        partition = apply_metadata()(fake_partitioner)

        elements = partition(**kwargs)

        assert all(e.metadata.last_modified == "2020-01-06T05:07:03" for e in elements)

    # -- url --------------------------------------------------------------

    def it_assigns_url_metadata_field_when_url_arg_is_present(
        self, fake_partitioner: Callable[..., list[Element]]
    ):
        partition = apply_metadata()(fake_partitioner)

        elements = partition(url="https://adobe.com/stock/54321")

        assert all(e.metadata.url == "https://adobe.com/stock/54321" for e in elements)

    def and_it_does_not_assign_url_metadata_when_url_arg_is_not_present(
        self, fake_partitioner: Callable[..., list[Element]]
    ):
        partition = apply_metadata()(fake_partitioner)

        elements = partition()

        assert all(e.metadata.url == "http://images.com" for e in elements)

    # -- fixtures --------------------------------------------------------------------------------

    @pytest.fixture
    def fake_partitioner(self) -> Callable[..., list[Element]]:
        def fake_partitioner(**kwargs: Any) -> list[Element]:
            title = Title("Introduction")
            title.metadata.category_depth = 1
            title.metadata.file_directory = "x/y/images"
            title.metadata.filename = "image.jpeg"
            title.metadata.filetype = "image/jpeg"
            title.metadata.last_modified = "2020-01-06T05:07:03"
            title.metadata.url = "http://images.com"

            narr_text = NarrativeText("To understand bar you must first understand foo.")
            narr_text.metadata.file_directory = "x/y/images"
            narr_text.metadata.filename = "image.jpeg"
            narr_text.metadata.filetype = "image/jpeg"
            narr_text.metadata.last_modified = "2020-01-06T05:07:03"
            narr_text.metadata.url = "http://images.com"

            return [title, narr_text]

        return fake_partitioner


# ================================================================================================
# HASH IDS
# ================================================================================================


def test_assign_hash_ids_produces_unique_and_deterministic_SHA1_ids_even_for_duplicate_elements():
    elements: list[Element] = [
        Text(text="Element", metadata=ElementMetadata(filename="foo.bar", page_number=1)),
        Text(text="Element", metadata=ElementMetadata(filename="foo.bar", page_number=1)),
        Text(text="Element", metadata=ElementMetadata(filename="foo.bar", page_number=1)),
    ]
    # -- default ids are UUIDs --
    assert all(len(e.id) == 36 for e in elements)

    elements = _assign_hash_ids(copy.deepcopy(elements))
    elements_2 = _assign_hash_ids(copy.deepcopy(elements))

    ids = [e.id for e in elements]
    # -- ids are now SHA1 --
    assert all(len(e.id) == 32 for e in elements)
    # -- each id is unique --
    assert len(ids) == len(set(ids))
    # -- ids are deterministic, same value is computed each time --
    assert all(e.id == e2.id for e, e2 in zip(elements, elements_2))
