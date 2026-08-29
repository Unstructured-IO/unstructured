# pyright: reportPrivateUsage=false

from __future__ import annotations

import json
import uuid
from typing import Optional, Type

import pytest
from pytest_mock import MockerFixture

from test_unstructured.unit_utils import assert_round_trips_through_JSON, example_doc_path
from unstructured.chunking.title import chunk_by_title
from unstructured.cleaners.core import group_broken_paragraphs
from unstructured.documents.elements import Address, ListItem, NarrativeText, Text, Title
from unstructured.file_utils.model import FileType
from unstructured.partition.text import element_from_text, partition_text
from unstructured.partition.utils.constants import UNSTRUCTURED_INCLUDE_DEBUG_METADATA

EXPECTED_OUTPUT = [
    NarrativeText(text="This is a test document to use for unit tests."),
    Address(text="Doylestown, PA 18901"),
    Title(text="Important points:"),
    ListItem(text="Hamburgers are delicious"),
    ListItem(text="Dogs are the best"),
    ListItem(text="I love fuzzy blankets"),
]

MIN_MAX_TEXT = """This is a story. This is a story that doesn't matter
 because it is just being used as an example. Hi. Hello. Howdy. Hola.
 The example is simple and repetitive and long and somewhat boring,
 but it serves a purpose. End.""".replace(
    "\n",
    "",
)

SHORT_PARAGRAPHS = """This is a story.

This is a story that doesn't matter because it is just being used as an example.

Hi.

Hello.

Howdy.

Hola.

The example is simple and repetitive and long and somewhat boring, but it serves a purpose.

End.
"""


def test_element_from_numeric_text_skips_nlp(mocker: MockerFixture):
    narrative = mocker.patch(
        "unstructured.partition.text.is_possible_narrative_text",
        side_effect=AssertionError("numeric text should not reach narrative NLP rules"),
    )
    title = mocker.patch(
        "unstructured.partition.text.is_possible_title",
        side_effect=AssertionError("numeric text should not reach title NLP rules"),
    )

    assert element_from_text("123456") == Text("123456")
    narrative.assert_not_called()
    title.assert_not_called()


@pytest.mark.parametrize(
    ("filename", "encoding"),
    [
        ("fake-text.txt", "utf-8"),
        ("fake-text.txt", None),
        ("fake-text-utf-16-be.txt", "utf-16-be"),
    ],
)
def test_partition_text_from_filename(filename: str, encoding: Optional[str]):
    elements = partition_text(example_doc_path(filename), encoding=encoding)

    assert len(elements) > 0
    assert elements == EXPECTED_OUTPUT
    for element in elements:
        assert element.metadata.filename == filename
    if UNSTRUCTURED_INCLUDE_DEBUG_METADATA:
        assert {element.metadata.detection_origin for element in elements} == {"text"}


def test_partition_text_from_filename_with_metadata_filename():
    elements = partition_text(
        example_doc_path("fake-text.txt"), encoding="utf-8", metadata_filename="test"
    )

    assert elements == EXPECTED_OUTPUT
    for element in elements:
        assert element.metadata.filename == "test"


@pytest.mark.parametrize(
    "filename",
    ["fake-text-utf-16.txt", "fake-text-utf-16-le.txt", "fake-text-utf-32.txt"],
)
def test_partition_text_from_filename_default_encoding(filename: str):
    elements = partition_text(example_doc_path(filename))

    assert len(elements) > 0
    assert elements == EXPECTED_OUTPUT
    for element in elements:
        assert element.metadata.filename == filename


@pytest.mark.parametrize(
    ("filename", "encoding", "error"),
    [
        ("fake-text.txt", "utf-16", UnicodeDecodeError),
        ("fake-text-utf-16-be.txt", "utf-16", UnicodeError),
    ],
)
def test_partition_text_from_filename_raises_econding_error(
    filename: str,
    encoding: Optional[str],
    error: Type[BaseException],
):
    with pytest.raises(error):
        filename = example_doc_path(filename)
        partition_text(filename=filename, encoding=encoding)


def test_partition_text_from_file():
    with open(example_doc_path("fake-text.txt"), "rb") as f:
        elements = partition_text(file=f)

    assert len(elements) > 0
    assert elements == EXPECTED_OUTPUT
    for element in elements:
        assert element.metadata.filename is None


def test_partition_text_from_file_with_metadata_filename():
    filename = example_doc_path("fake-text.txt")
    with open(filename, "rb") as f:
        elements = partition_text(file=f, metadata_filename="test")
    assert len(elements) > 0
    assert elements == EXPECTED_OUTPUT
    for element in elements:
        assert element.metadata.filename == "test"


@pytest.mark.parametrize(
    "filename",
    ["fake-text-utf-16.txt", "fake-text-utf-16-le.txt", "fake-text-utf-32.txt"],
)
def test_partition_text_from_file_default_encoding(filename: str):
    with open(example_doc_path(filename), "rb") as f:
        elements = partition_text(file=f)
    assert len(elements) > 0
    assert elements == EXPECTED_OUTPUT
    for element in elements:
        assert element.metadata.filename is None


def test_partition_text_from_bytes_file():
    with open(example_doc_path("fake-text.txt"), "rb") as f:
        elements = partition_text(file=f)

    assert len(elements) > 0
    assert elements == EXPECTED_OUTPUT
    for element in elements:
        assert element.metadata.filename is None


@pytest.mark.parametrize(
    "filename",
    ["fake-text-utf-16.txt", "fake-text-utf-16-le.txt", "fake-text-utf-32.txt"],
)
def test_partition_text_from_bytes_file_default_encoding(filename: str):
    with open(example_doc_path(filename), "rb") as f:
        elements = partition_text(file=f)

    assert len(elements) > 0
    assert elements == EXPECTED_OUTPUT
    for element in elements:
        assert element.metadata.filename is None


def test_text_partition_element_metadata_user_provided_languages():
    elements = partition_text(
        example_doc_path("book-war-and-peace-1p.txt"), strategy="fast", languages=["en"]
    )
    assert elements[0].metadata.languages == ["eng"]


def test_partition_text_from_text():
    with open(example_doc_path("fake-text.txt")) as f:
        text = f.read()

    elements = partition_text(text=text)

    assert len(elements) > 0
    assert elements == EXPECTED_OUTPUT
    for element in elements:
        assert element.metadata.filename is None


def test_partition_text_from_text_works_with_empty_string():
    assert partition_text(text="") == []


def test_partition_text_raises_with_none_specified():
    with pytest.raises(ValueError):
        partition_text()


def test_partition_text_raises_with_too_many_specified():
    filename = example_doc_path("fake-text.txt")
    with open(filename) as f:
        text = f.read()

    with pytest.raises(ValueError):
        partition_text(filename=filename, text=text)


def test_partition_text_captures_everything_even_with_linebreaks():
    text = """
    VERY IMPORTANT MEMO
    DOYLESTOWN, PA 18901
    """
    elements = partition_text(text=text)
    assert elements == [
        Title(text="VERY IMPORTANT MEMO"),
        Address(text="DOYLESTOWN, PA 18901"),
    ]
    for element in elements:
        assert element.metadata.filename is None


def test_partition_text_groups_broken_paragraphs():
    text = (
        "The big brown fox\n"
        "was walking down the lane.\n"
        "\n"
        "At the end of the lane,\n"
        "the fox met a bear."
    )

    elements = partition_text(text=text, paragraph_grouper=group_broken_paragraphs)

    assert elements == [
        NarrativeText(text="The big brown fox was walking down the lane."),
        NarrativeText(text="At the end of the lane, the fox met a bear."),
    ]
    for element in elements:
        assert element.metadata.filename is None


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Phone: 555-123-4567\n\nEnd", ["Phone: 555-123-4567", "End"]),
        ("SSN: 123-45-6789\n\nEnd", ["SSN: 123-45-6789", "End"]),
        ("Date: 2026-08-19\n\nEnd", ["Date: 2026-08-19", "End"]),
        ("Card: 4111-1111-1111-1111\n\nEnd", ["Card: 4111-1111-1111-1111", "End"]),
        (
            "IBAN: GB29-NWBK-6016-1331-9268-19\n\nEnd",
            ["IBAN: GB29-NWBK-6016-1331-9268-19", "End"],
        ),
        (
            "trace_id: 550e8400-e29b-41d4-a716-446655440000\n\nEnd",
            ["trace_id: 550e8400-e29b-41d4-a716-446655440000", "End"],
        ),
        ("Contact: Jean-Luc Picard\n\nEnd", ["Contact: Jean-Luc Picard", "End"]),
        ("name: my-service\n\nEnd", ["name: my-service", "End"]),
        (
            "2026-08-19 ERROR conn-pool-3 failed\n\nEnd",
            ["2026-08-19 ERROR conn-pool-3 failed", "End"],
        ),
        # -- CJK text never satisfies the space-separated `all_lines_short` guard --
        ("連絡先：090-1234-5678\n\n住所：東京", ["連絡先：090-1234-5678", "住所：東京"]),
        # -- en-dash (U+2013) is ambiguous in the same way as U+002D --
        ("Range: 10–20\n\nEnd", ["Range: 10–20", "End"]),
    ],
)
def test_partition_text_does_not_split_hyphenated_values(text: str, expected: list[str]):
    """A hyphen is intra-word punctuation, not an unanchored bullet delimiter."""
    assert [e.text for e in partition_text(text=text)] == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        # -- unambiguous bullet glyphs still split inline --
        (
            "Shopping list\n\n• milk • eggs • bread\n\nDone",
            ["Shopping list", "milk", "eggs", "bread", "Done"],
        ),
        # -- dash bullets at line start are still bullets --
        (
            "Agenda\n\n- first item here\n- second item here\n\nDone",
            ["Agenda", "first item here", "second item here", "Done"],
        ),
        # -- ...and a hyphen inside such an item is left alone --
        (
            "Agenda\n\n- deploy my-service now\n- check state-of-the-art\n\nDone",
            ["Agenda", "deploy my-service now", "check state-of-the-art", "Done"],
        ),
        # -- indented/nested dash bullets still split --
        (
            "Agenda\n\n- top one\n  - nested my-service\n\nDone",
            ["Agenda", "top one", "nested my-service", "Done"],
        ),
        # -- indentation in extracted text is not always an ASCII space: NO-BREAK SPACE
        # -- (U+00A0), EM SPACE (U+2003) and a tab must all read as indentation --
        (
            "Agenda\n\n- top one\n\u00a0- nbsp nested\n\u2003- em nested\n\t- tab nested\n\nDone",
            ["Agenda", "top one", "nbsp nested", "em nested", "tab nested", "Done"],
        ),
        # -- en-dash bullets at line start still split --
        (
            "Agenda\n\n– first item here\n– second item here\n\nDone",
            ["Agenda", "first item here", "second item here", "Done"],
        ),
        # -- NOTE: declared behavior change. Inline dash bullets on a single line no
        # -- longer split. Keeping hyphenated identifiers intact is worth the trade.
        ("Agenda\n\n- one - two - three\n\nDone", ["Agenda", "one - two - three", "Done"]),
    ],
)
def test_partition_text_still_recognizes_bullets(text: str, expected: list[str]):
    assert [e.text for e in partition_text(text=text)] == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        # -- a leading minus sign is not a bullet; stripping it flips the value --
        ("-123.45\n\nDone", [("Text", "-123.45"), ("Title", "Done")]),
        ("–10 °C\n\nDone", [("Text", "–10 °C"), ("Title", "Done")]),
        ("-5\n\nDone", [("Text", "-5"), ("Title", "Done")]),
        # -- a bullet is separated from the item it introduces; this is not --
        ("-item\n\nDone", [("Title", "-item"), ("Title", "Done")]),
        # -- ...whereas an unambiguous glyph needs no separator --
        ("•item\n\nDone", [("ListItem", "item"), ("Title", "Done")]),
        # -- a separated dash is still a bullet --
        ("- item\n\nDone", [("ListItem", "item"), ("Title", "Done")]),
        # -- a lone dash is an empty bullet and is dropped entirely; this exercises the
        # -- end-of-text branch of the qualifier and `_is_empty_bullet` --
        ("-\n\nDone", [("Title", "Done")]),
        ("–\n\nDone", [("Title", "Done")]),
    ],
)
def test_partition_text_does_not_mistake_signs_for_bullets(
    text: str, expected: list[tuple[str, str]]
):
    assert [(type(e).__name__, e.text) for e in partition_text(text=text)] == expected


def test_partition_text_keeps_signs_on_lines_wrapped_under_a_bullet():
    """Continuation lines starting with a negative number keep their sign.

    They are folded into the bullet item above rather than each becoming a bullet whose
    minus sign is stripped.
    """
    text = "- readings\n-5 °C\n-10 °C\n\nDone"

    assert [(type(e).__name__, e.text) for e in partition_text(text=text)] == [
        ("ListItem", "readings -5 °C -10 °C"),
        ("Title", "Done"),
    ]


def test_partition_text_keeps_short_unrelated_lines_separate():
    """The Apache-License case the comment in `group_broken_paragraphs` cites."""
    text = "Apache License\nVersion 2.0, January 2004\nhttp://www.apache.org/licenses/\n\nEnd"

    assert [e.text for e in partition_text(text=text)] == [
        "Apache License",
        "Version 2.0, January 2004",
        "http://www.apache.org/licenses/",
        "End",
    ]


def test_partition_text_splits_long_text():
    elements = partition_text(example_doc_path("norwich-city.txt"))
    assert len(elements) > 0
    assert elements[0].text.startswith("Iwan Roberts")
    assert elements[-1].text.endswith("External links")


def test_partition_text_doesnt_get_page_breaks():
    text = "--------------------"
    elements = partition_text(text=text)
    assert len(elements) == 1
    assert elements[0].text == text
    assert not isinstance(elements[0], ListItem)


# -- .metadata.filename --------------------------------------------------------------------------


def test_partition_text_from_filename_gets_filename_metadata_from_file_path():
    elements = partition_text(example_doc_path("fake-text.txt"))

    assert all(e.metadata.filename == "fake-text.txt" for e in elements)
    assert all(e.metadata.file_directory == example_doc_path("") for e in elements)


def test_partition_text_from_file_gets_filename_metadata_None():
    with open(example_doc_path("fake-text.txt"), "rb") as f:
        elements = partition_text(file=f)

    assert all(e.metadata.filename is None for e in elements)
    assert all(e.metadata.file_directory is None for e in elements)


def test_partition_text_from_filename_prefers_metadata_filename():
    elements = partition_text(example_doc_path("fake-text.txt"), metadata_filename="a/b/c.txt")

    assert all(e.metadata.filename == "c.txt" for e in elements)
    assert all(e.metadata.file_directory == "a/b" for e in elements)


def test_partition_text_from_file_prefers_metadata_filename():
    with open(example_doc_path("fake-text.txt"), "rb") as f:
        elements = partition_text(file=f, metadata_filename="d/e/f.txt")

    assert all(e.metadata.filename == "f.txt" for e in elements)
    assert all(e.metadata.file_directory == "d/e" for e in elements)


# -- .metadata.filetype --------------------------------------------------------------------------


def test_partition_text_gets_the_TXT_MIME_type_in_metadata_filetype():
    TXT_MIME_TYPE = "text/plain"
    elements = partition_text(example_doc_path("fake-text.txt"))
    assert all(e.metadata.filetype == TXT_MIME_TYPE for e in elements), (
        f"Expected all elements to have '{TXT_MIME_TYPE}' as their filetype, but got:"
        f" {repr(elements[0].metadata.filetype)}"
    )


def test_partition_text_prefers_metadata_file_type():
    elements = partition_text(example_doc_path("README.md"), metadata_file_type=FileType.MD)
    assert all(e.metadata.filetype == "text/markdown" for e in elements), (
        f"Expected all elements to have 'text/markdown' as their filetype, but got:"
        f" {repr(elements[0].metadata.filetype)}"
    )


# -- .metadata.last_modified ---------------------------------------------------------------------


def test_partition_text_from_file_path_gets_last_modified_from_filesystem(mocker: MockerFixture):
    filesystem_last_modified = "2029-07-05T09:24:28"
    mocker.patch(
        "unstructured.partition.text.get_last_modified_date", return_value=filesystem_last_modified
    )

    elements = partition_text(example_doc_path("fake-text.txt"))

    assert all(e.metadata.last_modified == filesystem_last_modified for e in elements)


def test_partition_text_from_file_gets_last_modified_None():
    with open(example_doc_path("fake-text.txt"), "rb") as f:
        elements = partition_text(file=f)

    assert all(e.metadata.last_modified is None for e in elements)


def test_partition_text_from_text_gets_last_modified_None():
    with open(example_doc_path("fake-text.txt")) as f:
        text = f.read()

    elements = partition_text(text=text)

    assert all(e.metadata.last_modified is None for e in elements)


def test_partition_text_from_file_path_prefers_metadata_last_modified(mocker: MockerFixture):
    filesystem_last_modified = "2029-07-05T09:24:28"
    metadata_last_modified = "2020-07-05T09:24:28"
    mocker.patch(
        "unstructured.partition.text.get_last_modified_date", return_value=filesystem_last_modified
    )

    elements = partition_text(
        example_doc_path("fake-text.txt"), metadata_last_modified=metadata_last_modified
    )

    assert all(e.metadata.last_modified == metadata_last_modified for e in elements)


def test_partition_text_from_file_prefers_metadata_last_modified():
    metadata_last_modified = "2020-07-05T09:24:28"
    with open(example_doc_path("fake-text.txt"), "rb") as f:
        elements = partition_text(file=f, metadata_last_modified=metadata_last_modified)

    assert all(e.metadata.last_modified == metadata_last_modified for e in elements)


def test_partition_text_from_text_prefers_metadata_last_modified():
    metadata_last_modified = "2020-07-05T09:24:28"
    with open(example_doc_path("fake-text.txt")) as f:
        text = f.read()

    elements = partition_text(text=text, metadata_last_modified=metadata_last_modified)

    assert all(e.metadata.last_modified == metadata_last_modified for e in elements)


# ------------------------------------------------------------------------------------------------


def test_Text_element_assigns_id_hashes_that_are_unique_and_deterministic():
    ids = [element.id for element in partition_text(text="hello\nhello\nhello")]
    assert ids == [
        "8657c0ec31a4cfc822f6cd4a5684cafd",
        "72aefb4a12be063ad160931fdb380163",
        "ba8c1a216ca585aecdd365a72e6124f1",
    ]


def test_Text_element_assings_UUID_when_unique_element_ids_is_True():
    elements = partition_text(text="hello\nhello\nhello", unique_element_ids=True)

    for element in elements:
        assert uuid.UUID(element.id, version=4)

        # Test that the element is JSON serializable. This should run without an error
        json.dumps(element.to_dict())


@pytest.mark.parametrize(
    ("file_name", "encoding"),
    [
        ("fake-text.txt", "utf-8"),
        ("fake-text.txt", None),
        ("fake-text-utf-16-be.txt", "utf-16-be"),
    ],
)
def test_partition_text_with_json(file_name: str, encoding: str | None):
    elements = partition_text(example_doc_path(file_name), encoding=encoding)
    assert_round_trips_through_JSON(elements)


def test_add_chunking_strategy_on_partition_text():
    filename = example_doc_path("book-war-and-peace-1p.txt")
    elements = partition_text(filename=filename)
    chunk_elements = partition_text(filename, chunking_strategy="by_title")
    chunks = chunk_by_title(elements)
    assert chunk_elements != elements
    assert chunk_elements == chunks


def test_partition_text_element_metadata_has_languages():
    elements = partition_text(example_doc_path("norwich-city.txt"))
    assert elements[0].metadata.languages == ["eng"]


def test_partition_text_respects_detect_language_per_element():
    elements = partition_text(
        example_doc_path("language-docs/eng_spa_mult.txt"), detect_language_per_element=True
    )

    langs = [element.metadata.languages for element in elements]

    assert langs == [["eng"], ["spa", "eng"], ["eng"], ["eng"], ["spa"]]


def test_partition_text_respects_languages_arg():
    elements = partition_text(example_doc_path("norwich-city.txt"), languages=["deu"])
    assert elements[0].metadata.languages == ["deu"]


def test_partition_text_element_metadata_raises_TypeError():
    with pytest.raises(TypeError):
        partition_text(example_doc_path("norwich-city.txt"), languages="eng")


def test_partition_text_detects_more_than_3_languages():
    elements = partition_text(
        example_doc_path("language-docs/UDHR_first_article_all.txt"),
        detect_language_per_element=True,
    )
    langs = [e.metadata.languages[0] for e in elements if e.metadata.languages]
    assert len(langs) > 10
