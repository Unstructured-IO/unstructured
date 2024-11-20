"""Test-suite for `unstructured.partition.ppt` module."""

from __future__ import annotations

import pytest
from pytest_mock import MockFixture

from test_unstructured.unit_utils import assert_round_trips_through_JSON, example_doc_path
from unstructured.chunking.title import chunk_by_title
from unstructured.documents.elements import ListItem, NarrativeText, PageBreak, Title
from unstructured.partition.ppt import partition_ppt
from unstructured.partition.utils.constants import UNSTRUCTURED_INCLUDE_DEBUG_METADATA

EXPECTED_PPT_OUTPUT = [
    Title(text="Adding a Bullet Slide"),
    ListItem(text="Find the bullet slide layout"),
    ListItem(text="Use _TextFrame.text for first bullet"),
    ListItem(text="Use _TextFrame.add_paragraph() for subsequent bullets"),
    NarrativeText(text="Here is a lot of text!"),
    NarrativeText(text="Here is some text in a text box!"),
]


def test_partition_ppt_from_filename():
    elements = partition_ppt(example_doc_path("fake-power-point.ppt"))
    assert elements == EXPECTED_PPT_OUTPUT
    for element in elements:
        assert element.metadata.filename == "fake-power-point.ppt"
    if UNSTRUCTURED_INCLUDE_DEBUG_METADATA:
        assert {element.metadata.detection_origin for element in elements} == {"pptx"}


def test_partition_ppt_raises_with_missing_file():
    with pytest.raises(ValueError):
        partition_ppt(example_doc_path("doesnt-exist.ppt"))


def test_partition_ppt_from_file():
    with open(example_doc_path("fake-power-point.ppt"), "rb") as f:
        elements = partition_ppt(file=f)
    assert elements == EXPECTED_PPT_OUTPUT
    for element in elements:
        assert element.metadata.filename is None


def test_partition_ppt_from_file_with_metadata_filename():
    with open(example_doc_path("fake-power-point.ppt"), "rb") as f:
        elements = partition_ppt(file=f, metadata_filename="test")
    assert elements == EXPECTED_PPT_OUTPUT
    for element in elements:
        assert element.metadata.filename == "test"


def test_partition_ppt_raises_with_both_specified():
    filename = example_doc_path("fake-power-point.ppt")
    with open(filename, "rb") as f, pytest.raises(ValueError):
        partition_ppt(filename=filename, file=f)


def test_partition_ppt_raises_when_neither_file_path_or_file_is_provided():
    with pytest.raises(ValueError):
        partition_ppt()


# -- .metadata.filename --------------------------------------------------------------------------


def test_partition_ppt_from_filename_gets_filename_from_filename_arg():
    elements = partition_ppt(example_doc_path("fake-power-point.ppt"))

    assert len(elements) > 0
    assert all(e.metadata.filename == "fake-power-point.ppt" for e in elements)


def test_partition_ppt_from_file_gets_filename_None():
    with open(example_doc_path("fake-power-point.ppt"), "rb") as f:
        elements = partition_ppt(file=f)

    assert len(elements) > 0
    assert all(e.metadata.filename is None for e in elements)


def test_partition_ppt_from_filename_prefers_metadata_filename():
    elements = partition_ppt(example_doc_path("fake-power-point.ppt"), metadata_filename="test")

    assert len(elements) > 0
    assert all(element.metadata.filename == "test" for element in elements)


def test_partition_ppt_from_file_prefers_metadata_filename():
    with open(example_doc_path("fake-power-point.ppt"), "rb") as f:
        elements = partition_ppt(file=f, metadata_filename="test")

    assert all(e.metadata.filename == "test" for e in elements)


# -- .metadata.last_modified ---------------------------------------------------------------------


def test_partition_ppt_from_file_path_gets_last_modified_from_filesystem(mocker: MockFixture):
    filesystem_last_modified = "2024-05-01T15:37:28"
    mocker.patch(
        "unstructured.partition.ppt.get_last_modified_date", return_value=filesystem_last_modified
    )

    elements = partition_ppt(example_doc_path("fake-power-point.ppt"))

    assert all(e.metadata.last_modified == filesystem_last_modified for e in elements)


def test_partition_ppt_from_file_gets_last_modified_None():
    with open(example_doc_path("fake-power-point.ppt"), "rb") as f:
        elements = partition_ppt(file=f)

    assert all(e.metadata.last_modified is None for e in elements)


def test_partition_ppt_from_file_path_prefers_metadata_last_modified(mocker: MockFixture):
    filesystem_last_modified = "2024-05-01T15:37:28"
    metadata_last_modified = "2020-07-05T09:24:28"
    mocker.patch(
        "unstructured.partition.ppt.get_last_modified_date", return_value=filesystem_last_modified
    )

    elements = partition_ppt(
        example_doc_path("fake-power-point.ppt"), metadata_last_modified=metadata_last_modified
    )

    assert all(e.metadata.last_modified == metadata_last_modified for e in elements)


def test_partition_ppt_from_file_prefers_metadata_last_modified():
    metadata_last_modified = "2020-07-05T09:24:28"

    with open(example_doc_path("fake-power-point.ppt"), "rb") as f:
        elements = partition_ppt(file=f, metadata_last_modified=metadata_last_modified)

    assert elements[0].metadata.last_modified == metadata_last_modified


# ------------------------------------------------------------------------------------------------


def test_partition_ppt_with_json():
    elements = partition_ppt(example_doc_path("fake-power-point.ppt"))
    assert_round_trips_through_JSON(elements)


def test_add_chunking_strategy_by_title_on_partition_ppt():
    file_path = example_doc_path("fake-power-point.ppt")
    elements = partition_ppt(file_path)
    chunk_elements = partition_ppt(file_path, chunking_strategy="by_title")
    chunks = chunk_by_title(elements)
    assert chunk_elements != elements
    assert chunk_elements == chunks


def test_partition_ppt_params():
    """Integration test of params: languages, include_page_break, and include_slide_notes."""
    elements = partition_ppt(
        example_doc_path("language-docs/eng_spa_mult.ppt"),
        include_page_breaks=True,
        include_slide_notes=True,
    )
    assert elements[0].metadata.languages == ["eng"]
    assert any(isinstance(element, PageBreak) for element in elements)
    # The example doc contains a slide note with the text "This is a slide note."
    assert any(element.text == "This is a slide note." for element in elements)


def test_partition_ppt_respects_detect_language_per_element():
    elements = partition_ppt(
        example_doc_path("language-docs/eng_spa_mult.ppt"), detect_language_per_element=True
    )
    langs = [element.metadata.languages for element in elements]
    # languages other than English and Spanish are detected by this partitioner,
    # so this test is slightly different from the other partition tests
    langs = {element.metadata.languages[0] for element in elements if element.metadata.languages}
    assert "eng" in langs
    assert "spa" in langs
