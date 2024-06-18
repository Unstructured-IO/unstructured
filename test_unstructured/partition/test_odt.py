"""Test suite for `unstructured.partition.odt` module."""

from __future__ import annotations

from typing import Any

import pytest
from pytest_mock import MockFixture

from test_unstructured.unit_utils import (
    FixtureRequest,
    assert_round_trips_through_JSON,
    example_doc_path,
    function_mock,
)
from unstructured.chunking.basic import chunk_elements
from unstructured.documents.elements import CompositeElement, Table, TableChunk, Title
from unstructured.partition.docx import partition_docx
from unstructured.partition.odt import partition_odt
from unstructured.partition.utils.constants import UNSTRUCTURED_INCLUDE_DEBUG_METADATA


def test_partition_odt_matches_partition_docx():
    odt_file_path = example_doc_path("simple.odt")
    docx_file_path = example_doc_path("simple.docx")

    assert partition_odt(odt_file_path) == partition_docx(docx_file_path)


# -- document-source (file or filename) ----------------------------------------------------------


def test_partition_odt_from_filename():
    elements = partition_odt(example_doc_path("fake.odt"))

    assert elements == [
        Title("Lorem ipsum dolor sit amet."),
        Table(
            "Header row Mon Wed Fri"
            " Color Blue Red Green"
            " Time 1pm 2pm 3pm"
            " Leader Sarah Mark Ryan"
        ),
    ]
    assert all(e.metadata.filename == "fake.odt" for e in elements)
    if UNSTRUCTURED_INCLUDE_DEBUG_METADATA:
        # -- document is ultimately partitioned by partition_docx() --
        assert {e.metadata.detection_origin for e in elements} == {"docx"}


def test_partition_odt_from_file():
    with open(example_doc_path("fake.odt"), "rb") as f:
        elements = partition_odt(file=f)

    assert elements == [
        Title("Lorem ipsum dolor sit amet."),
        Table(
            "Header row Mon Wed Fri"
            " Color Blue Red Green"
            " Time 1pm 2pm 3pm"
            " Leader Sarah Mark Ryan"
        ),
    ]


# -- `include_metadata` arg ----------------------------------------------------------------------


def test_partition_odt_from_filename_exclude_metadata():
    elements = partition_odt(example_doc_path("fake.odt"), include_metadata=False)
    assert all(e.metadata.to_dict() == {} for e in elements)


def test_partition_odt_from_file_exclude_metadata():
    with open(example_doc_path("fake.odt"), "rb") as f:
        elements = partition_odt(file=f, include_metadata=False)
    assert all(e.metadata.to_dict() == {} for e in elements)


# -- .metadata.filename --------------------------------------------------------------------------


def test_partition_odt_from_filename_with_metadata_filename():
    elements = partition_odt(example_doc_path("fake.odt"), metadata_filename="test")
    assert all(element.metadata.filename == "test" for element in elements)


def test_partition_odt_from_file_with_metadata_filename():
    with open(example_doc_path("fake.odt"), "rb") as f:
        elements = partition_odt(file=f, metadata_filename="test")
    assert all(element.metadata.filename == "test" for element in elements)


# -- .metadata.text_as_html ----------------------------------------------------------------------


@pytest.mark.parametrize("kwargs", [{}, {"infer_table_structure": True}])
def test_partition_odt_adds_text_as_html_when_infer_table_structure_is_omitted_or_True(
    kwargs: dict[str, Any]
):
    with open(example_doc_path("fake.odt"), "rb") as f:
        elements = partition_odt(file=f, **kwargs)

    table = elements[1]
    assert isinstance(table, Table)
    assert table.metadata.text_as_html is not None
    assert table.metadata.text_as_html.startswith("<table>")


def test_partition_odt_suppresses_text_as_html_when_infer_table_structure_is_False():
    with open(example_doc_path("fake.odt"), "rb") as f:
        elements = partition_odt(file=f, infer_table_structure=False)

    table = elements[1]
    assert isinstance(table, Table)
    assert table.metadata.text_as_html is None


# -- .metadata.last_modified ---------------------------------------------------------------------


def test_partition_odt_pulls_last_modified_from_filesystem(mocker: MockFixture):
    filesystem_last_modified = "2029-07-05T09:24:28"
    mocker.patch(
        "unstructured.partition.odt.get_last_modified", return_value=filesystem_last_modified
    )

    elements = partition_odt(example_doc_path("fake.odt"))

    assert all(e.metadata.last_modified == filesystem_last_modified for e in elements)


def test_partition_odt_prefers_metadata_last_modified_when_provided(mocker: MockFixture):
    filesystem_last_modified = "2029-07-05T09:24:28"
    metadata_last_modified = "2020-07-05T09:24:28"
    mocker.patch(
        "unstructured.partition.odt.get_last_modified", return_value=filesystem_last_modified
    )

    elements = partition_odt(
        example_doc_path("simple.odt"), metadata_last_modified=metadata_last_modified
    )

    assert all(e.metadata.last_modified == metadata_last_modified for e in elements)


# -- language-recognition metadata ---------------------------------------------------------------


def test_partition_odt_adds_languages_metadata():
    elements = partition_odt(example_doc_path("simple.odt"))
    assert all(e.metadata.languages == ["eng"] for e in elements)


def test_partition_odt_respects_detect_language_per_element_arg():
    elements = partition_odt(
        example_doc_path("language-docs/eng_spa_mult.odt"), detect_language_per_element=True
    )
    assert [e.metadata.languages for e in elements] == [
        ["eng"],
        ["spa", "eng"],
        ["eng"],
        ["eng"],
        ["spa"],
    ]


# -- miscellaneous -------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("kwargs", "expected_value"),
    [({}, None), ({"strategy": None}, None), ({"strategy": "hi_res"}, "hi_res")],
)
def test_partition_odt_forwards_strategy_arg_to_partition_docx(
    request: FixtureRequest, kwargs: dict[str, Any], expected_value: str | None
):
    partition_docx_ = function_mock(request, "unstructured.partition.odt.partition_docx")

    partition_odt(example_doc_path("simple.odt"), **kwargs)

    call_kwargs = partition_docx_.call_args.kwargs
    # -- `strategy` keyword-argument appeared in the call --
    assert "strategy" in call_kwargs
    # -- `strategy` argument was passed with the expected value --
    assert call_kwargs["strategy"] == expected_value


def test_partition_odt_round_trips_through_json():
    """Elements produced can be serialized then deserialized without loss."""
    assert_round_trips_through_JSON(partition_odt(example_doc_path("simple.odt")))


def test_partition_odt_chunks_elements_when_chunking_strategy_is_specified():
    document_path = example_doc_path("simple.odt")
    elements = partition_odt(document_path)
    chunks = partition_odt(document_path, chunking_strategy="basic")

    # -- all chunks are chunk element-types --
    assert all(isinstance(c, (CompositeElement, Table, TableChunk)) for c in chunks)
    # -- chunks from partitioning match those produced by chunking elements in separate step --
    assert chunks == chunk_elements(elements)
