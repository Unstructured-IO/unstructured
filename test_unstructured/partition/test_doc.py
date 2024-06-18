"""Test suite for `unstructured.partition.doc` module."""

from __future__ import annotations

import pathlib
from typing import Any

import pytest
from pytest_mock import MockFixture

from test_unstructured.unit_utils import (
    CaptureFixture,
    FixtureRequest,
    assert_round_trips_through_JSON,
    example_doc_path,
    function_mock,
)
from unstructured.chunking.basic import chunk_elements
from unstructured.documents.elements import (
    Address,
    CompositeElement,
    Element,
    ListItem,
    NarrativeText,
    Table,
    TableChunk,
    Text,
    Title,
)
from unstructured.partition.doc import partition_doc
from unstructured.partition.docx import partition_docx


def test_partition_doc_matches_partition_docx(request: FixtureRequest):
    doc_file_path = example_doc_path("simple.doc")
    docx_file_path = example_doc_path("simple.docx")

    assert partition_doc(doc_file_path) == partition_docx(docx_file_path)


# -- document-source (file or filename) ----------------------------------------------------------


def test_partition_doc_from_filename(expected_elements: list[Element], capsys: CaptureFixture[str]):
    elements = partition_doc(example_doc_path("simple.doc"))

    assert elements == expected_elements
    assert all(e.metadata.filename == "simple.doc" for e in elements)
    assert all(e.metadata.file_directory == example_doc_path("") for e in elements)
    assert capsys.readouterr().out == ""
    assert capsys.readouterr().err == ""


def test_partition_doc_from_file_with_libre_office_filter(
    expected_elements: list[Element], capsys: CaptureFixture[str]
):
    with open(example_doc_path("simple.doc"), "rb") as f:
        elements = partition_doc(file=f, libre_office_filter="MS Word 2007 XML")

    assert elements == expected_elements
    assert capsys.readouterr().out == ""
    assert capsys.readouterr().err == ""
    assert all(e.metadata.filename is None for e in elements)


def test_partition_doc_from_file_with_no_libre_office_filter(
    expected_elements: list[Element], capsys: CaptureFixture[str]
):
    with open(example_doc_path("simple.doc"), "rb") as f:
        elements = partition_doc(file=f, libre_office_filter=None)

    assert elements == expected_elements
    assert capsys.readouterr().out == ""
    assert capsys.readouterr().err == ""
    assert all(e.metadata.filename is None for e in elements)


def test_partition_doc_raises_when_both_a_filename_and_file_are_specified():
    doc_file_path = example_doc_path("simple.doc")

    with open(doc_file_path, "rb") as f:
        with pytest.raises(ValueError, match="Exactly one of filename and file must be specified"):
            partition_doc(filename=doc_file_path, file=f)


def test_partition_doc_raises_when_neither_a_file_path_nor_a_file_like_object_are_provided():
    with pytest.raises(ValueError, match="Exactly one of filename and file must be specified"):
        partition_doc()


def test_partition_raises_with_missing_doc(tmp_path: pathlib.Path):
    doc_filename = str(tmp_path / "asdf.doc")

    with pytest.raises(ValueError, match="asdf.doc does not exist"):
        partition_doc(filename=doc_filename)


# -- `include_metadata` arg ----------------------------------------------------------------------


def test_partition_doc_from_filename_excludes_metadata_when_so_instructed():
    elements = partition_doc(example_doc_path("simple.doc"), include_metadata=False)
    assert all(e.metadata.to_dict() == {} for e in elements)


def test_partition_doc_from_file_excludes_metadata_when_so_instructed():
    with open(example_doc_path("simple.doc"), "rb") as f:
        elements = partition_doc(file=f, include_metadata=False)

    assert all(e.metadata.to_dict() == {} for e in elements)


# -- .metadata.filename --------------------------------------------------------------------------


def test_partition_doc_from_filename_prefers_metadata_filename_when_provided(
    expected_elements: list[Element],
):
    elements = partition_doc(example_doc_path("simple.doc"), metadata_filename="test")

    assert elements == expected_elements
    assert all(element.metadata.filename == "test" for element in elements)


def test_partition_doc_from_file_prefers_metadata_filename_when_provided():
    with open(example_doc_path("simple.doc"), "rb") as f:
        elements = partition_doc(file=f, metadata_filename="test")

    assert all(e.metadata.filename == "test" for e in elements)


# -- .metadata.last_modified ---------------------------------------------------------------------


def test_partition_doc_pulls_last_modified_from_filesystem(mocker: MockFixture):
    filesystem_last_modified = "2029-07-05T09:24:28"
    mocker.patch(
        "unstructured.partition.doc.get_last_modified", return_value=filesystem_last_modified
    )

    elements = partition_doc(example_doc_path("fake.doc"))

    assert all(e.metadata.last_modified == filesystem_last_modified for e in elements)


def test_partition_doc_prefers_metadata_last_modified_when_provided(
    mocker: MockFixture,
):
    filesystem_last_modified = "2029-07-05T09:24:28"
    metadata_last_modified = "2020-07-05T09:24:28"
    mocker.patch(
        "unstructured.partition.doc.get_last_modified", return_value=filesystem_last_modified
    )

    elements = partition_doc(
        example_doc_path("simple.doc"), metadata_last_modified=metadata_last_modified
    )

    assert all(e.metadata.last_modified == metadata_last_modified for e in elements)


# -- language-recognition metadata ---------------------------------------------------------------


def test_partition_doc_adds_languages_metadata():
    elements = partition_doc(example_doc_path("simple.doc"))
    assert all(e.metadata.languages == ["eng"] for e in elements)


def test_partition_doc_respects_detect_language_per_element_arg():
    elements = partition_doc(
        example_doc_path("language-docs/eng_spa_mult.doc"), detect_language_per_element=True
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
def test_partition_doc_forwards_strategy_arg_to_partition_docx(
    request: FixtureRequest, kwargs: dict[str, Any], expected_value: str | None
):
    partition_docx_ = function_mock(request, "unstructured.partition.doc.partition_docx")

    partition_doc(example_doc_path("simple.doc"), **kwargs)

    call_kwargs = partition_docx_.call_args.kwargs
    # -- `strategy` keyword-argument appeared in the call --
    assert "strategy" in call_kwargs
    # -- `strategy` argument was passed with the expected value --
    assert call_kwargs["strategy"] == expected_value


def test_partition_doc_grabs_emphasized_texts():
    expected_emphasized_text_contents = ["bold", "italic", "bold-italic", "bold-italic"]
    expected_emphasized_text_tags = ["b", "i", "b", "i"]

    elements = partition_doc(example_doc_path("fake-doc-emphasized-text.doc"))

    assert isinstance(elements[0], Table)
    assert elements[0].metadata.emphasized_text_contents == expected_emphasized_text_contents
    assert elements[0].metadata.emphasized_text_tags == expected_emphasized_text_tags

    assert elements[1] == NarrativeText("I am a bold italic bold-italic text.")
    assert elements[1].metadata.emphasized_text_contents == expected_emphasized_text_contents
    assert elements[1].metadata.emphasized_text_tags == expected_emphasized_text_tags

    assert elements[2] == NarrativeText("I am a normal text.")
    assert elements[2].metadata.emphasized_text_contents is None
    assert elements[2].metadata.emphasized_text_tags is None


def test_partition_doc_round_trips_through_json():
    """Elements produced can be serialized then deserialized without loss."""
    assert_round_trips_through_JSON(partition_doc(example_doc_path("simple.doc")))


def test_partition_doc_chunks_elements_when_chunking_strategy_is_specified():
    document_path = example_doc_path("simple.doc")
    elements = partition_doc(document_path)
    chunks = partition_doc(document_path, chunking_strategy="basic")

    # -- all chunks are chunk element-types --
    assert all(isinstance(c, (CompositeElement, Table, TableChunk)) for c in chunks)
    # -- chunks from partitioning match those produced by chunking elements in separate step --
    assert chunks == chunk_elements(elements)


def test_partition_doc_assigns_deterministic_and_unique_element_ids():
    document_path = example_doc_path("duplicate-paragraphs.doc")

    ids = [element.id for element in partition_doc(document_path)]
    ids_2 = [element.id for element in partition_doc(document_path)]

    # -- ids should match even though partitioned separately --
    assert ids == ids_2
    # -- ids should be unique --
    assert len(ids) == len(set(ids))


# == module-level fixtures =======================================================================


@pytest.fixture()
def expected_elements() -> list[Element]:
    return [
        Title("These are a few of my favorite things:"),
        ListItem("Parrots"),
        ListItem("Hockey"),
        Title("Analysis"),
        NarrativeText("This is my first thought. This is my second thought."),
        NarrativeText("This is my third thought."),
        Text("2023"),
        Address("DOYLESTOWN, PA 18901"),
    ]
