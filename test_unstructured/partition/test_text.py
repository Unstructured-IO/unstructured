# pyright: reportPrivateUsage=false

from __future__ import annotations

import json
import os
import pathlib
from typing import Optional, Sequence, Type, cast

import pytest
from pytest_mock import MockerFixture

from test_unstructured.unit_utils import assert_round_trips_through_JSON, example_doc_path
from unstructured.chunking.title import chunk_by_title
from unstructured.cleaners.core import group_broken_paragraphs
from unstructured.documents.elements import Address, ListItem, NarrativeText, Text, Title
from unstructured.partition.text import (
    _combine_paragraphs_less_than_min,
    _split_content_to_fit_max,
    partition_text,
)
from unstructured.partition.utils.constants import UNSTRUCTURED_INCLUDE_DEBUG_METADATA

DIRECTORY = pathlib.Path(__file__).parent.resolve()
EXAMPLE_DOCS_DIRECTORY = os.path.join(DIRECTORY, "..", "..", "example-docs")

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


@pytest.mark.parametrize(
    ("filename", "encoding"),
    [
        ("fake-text.txt", "utf-8"),
        ("fake-text.txt", None),
        ("fake-text-utf-16-be.txt", "utf-16-be"),
    ],
)
def test_partition_text_from_filename(filename: str, encoding: Optional[str]):
    filename_path = os.path.join(EXAMPLE_DOCS_DIRECTORY, filename)
    elements = partition_text(filename=filename_path, encoding=encoding)
    assert len(elements) > 0
    assert elements == EXPECTED_OUTPUT
    for element in elements:
        assert element.metadata.filename == filename
    if UNSTRUCTURED_INCLUDE_DEBUG_METADATA:
        assert {element.metadata.detection_origin for element in elements} == {"text"}


def test_partition_text_from_filename_with_metadata_filename():
    filename_path = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-text.txt")
    elements = partition_text(
        filename=filename_path,
        encoding="utf-8",
        metadata_filename="test",
    )
    assert elements == EXPECTED_OUTPUT
    for element in elements:
        assert element.metadata.filename == "test"


@pytest.mark.parametrize(
    "filename",
    ["fake-text-utf-16.txt", "fake-text-utf-16-le.txt", "fake-text-utf-32.txt"],
)
def test_partition_text_from_filename_default_encoding(filename: str):
    filename_path = os.path.join(EXAMPLE_DOCS_DIRECTORY, filename)
    elements = partition_text(filename=filename_path)
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
        filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, filename)
        partition_text(filename=filename, encoding=encoding)


def test_partition_text_from_file():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-text.txt")
    with open(filename, "rb") as f:
        elements = partition_text(file=f)
    assert len(elements) > 0
    assert elements == EXPECTED_OUTPUT
    for element in elements:
        assert element.metadata.filename is None


def test_partition_text_from_file_with_metadata_filename():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-text.txt")
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
    filename_path = os.path.join(EXAMPLE_DOCS_DIRECTORY, filename)
    with open(filename_path, "rb") as f:
        elements = partition_text(file=f)
    assert len(elements) > 0
    assert elements == EXPECTED_OUTPUT
    for element in elements:
        assert element.metadata.filename is None


def test_partition_text_from_bytes_file():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-text.txt")
    with open(filename, "rb") as f:
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
    filename_path = os.path.join(EXAMPLE_DOCS_DIRECTORY, filename)
    with open(filename_path, "rb") as f:
        elements = partition_text(file=f)
    assert len(elements) > 0
    assert elements == EXPECTED_OUTPUT
    for element in elements:
        assert element.metadata.filename is None


def test_text_partition_element_metadata_user_provided_languages():
    filename = "example-docs/book-war-and-peace-1p.txt"
    elements = partition_text(filename=filename, strategy="fast", languages=["en"])
    assert elements[0].metadata.languages == ["eng"]


def test_partition_text_from_text():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-text.txt")
    with open(filename) as f:
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
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-text.txt")
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
    text = """The big brown fox
was walking down the lane.

At the end of the lane,
the fox met a bear."""

    elements = partition_text(text=text, paragraph_grouper=group_broken_paragraphs)
    assert elements == [
        NarrativeText(text="The big brown fox was walking down the lane."),
        NarrativeText(text="At the end of the lane, the fox met a bear."),
    ]
    for element in elements:
        assert element.metadata.filename is None


def test_partition_text_extract_regex_metadata():
    text = "SPEAKER 1: It is my turn to speak now!"

    elements = partition_text(text=text, regex_metadata={"speaker": r"SPEAKER \d{1,3}"})
    assert elements[0].metadata.regex_metadata == {
        "speaker": [{"text": "SPEAKER 1", "start": 0, "end": 9}],
    }
    for element in elements:
        assert element.metadata.filename is None


def test_partition_text_splits_long_text():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "norwich-city.txt")
    elements = cast(Sequence[Text], partition_text(filename=filename))
    assert len(elements) > 0
    assert elements[0].text.startswith("Iwan Roberts")
    assert elements[-1].text.endswith("External links")


def test_partition_text_splits_long_text_max_partition():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "norwich-city.txt")
    elements = cast(Sequence[Text], partition_text(filename=filename))
    elements_max_part = cast(Sequence[Text], partition_text(filename=filename, max_partition=500))
    # NOTE(klaijan) - I edited the operation here from < to <=
    # Please revert back if this does not make sense
    assert len(elements) <= len(elements_max_part)
    for element in elements_max_part:
        assert len(element.text) <= 500

    # Make sure combined text is all the same
    assert " ".join([el.text for el in elements]) == " ".join([el.text for el in elements_max_part])


def test_partition_text_splits_max_min_partition():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "norwich-city.txt")
    elements = cast(Sequence[Text], partition_text(filename=filename))
    elements_max_part = cast(
        Sequence[Text],
        partition_text(filename=filename, min_partition=1000, max_partition=1500),
    )
    for i, element in enumerate(elements_max_part):
        # NOTE(robinson) - the last element does not have a next element to merge with,
        # so it can be short
        if i < len(elements_max_part) - 1:
            assert len(element.text) <= 1500
            assert len(element.text) >= 1000

    import re

    from unstructured.nlp.patterns import BULLETS_PATTERN

    # NOTE(klaijan) - clean the asterik out of both text.
    # The `elements` was partitioned by new line and thus makes line 56 (shown below)
    # "*Club domestic league appearances and goals"
    # be considered as a bullet point by the function is_bulleted_text
    # and so the asterik was removed from the paragraph
    # whereas `elements_max_part` was partitioned differently and thus none of the line
    # starts with any of the BULLETS_PATTERN.

    # TODO(klaijan) - when edit the function partition_text to support non-bullet paragraph
    # that starts with bullet-like BULLETS_PATTERN, remove the re.sub part from the assert below.

    # Make sure combined text is all the same
    assert re.sub(BULLETS_PATTERN, "", " ".join([el.text for el in elements])) == re.sub(
        BULLETS_PATTERN,
        "",
        " ".join([el.text for el in elements_max_part]),
    )


def test_partition_text_min_max():
    segments = cast(
        Sequence[Text],
        partition_text(
            text=SHORT_PARAGRAPHS,
            min_partition=6,
        ),
    )
    for i, segment in enumerate(segments):
        # NOTE(robinson) - the last element does not have a next element to merge with,
        # so it can be short
        if i < len(segments) - 1:
            assert len(segment.text) >= 6

    segments = cast(
        Sequence[Text],
        partition_text(
            text=SHORT_PARAGRAPHS,
            max_partition=20,
            min_partition=7,
        ),
    )
    for i, segment in enumerate(segments):
        # NOTE(robinson) - the last element does not have a next element to merge with,
        # so it can be short
        if i < len(segments) - 1:
            assert len(segment.text) >= 7
            assert len(segment.text) <= 20


def test_split_content_to_fit_max():
    segments = _split_content_to_fit_max(
        content=MIN_MAX_TEXT,
        max_partition=75,
    )
    assert segments == [
        "This is a story.",
        "This is a story that doesn't matter because",
        "it is just being used as an example. Hi. Hello. Howdy. Hola.",
        "The example is simple and repetitive and long",
        "and somewhat boring, but it serves a purpose. End.",
    ]


def test_combine_paragraphs_less_than_min():
    segments = _combine_paragraphs_less_than_min(
        SHORT_PARAGRAPHS.split("\n\n"),
        max_partition=1500,
        min_partition=7,
    )
    assert len(segments) < len(SHORT_PARAGRAPHS)


def test_partition_text_doesnt_get_page_breaks():
    text = "--------------------"
    elements = cast(Sequence[Text], partition_text(text=text))
    assert len(elements) == 1
    assert elements[0].text == text
    assert not isinstance(elements[0], ListItem)


@pytest.mark.parametrize(
    ("filename", "encoding"),
    [
        ("fake-text.txt", "utf-8"),
        ("fake-text.txt", None),
        ("fake-text-utf-16-be.txt", "utf-16-be"),
    ],
)
def test_partition_text_from_filename_exclude_metadata(filename: str, encoding: Optional[str]):
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, filename)
    elements = partition_text(
        filename=filename,
        encoding=encoding,
        include_metadata=False,
    )
    for i in range(len(elements)):
        assert elements[i].metadata.to_dict() == {}


def test_partition_text_from_file_exclude_metadata():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-text.txt")
    with open(filename, "rb") as f:
        elements = partition_text(file=f, include_metadata=False)
    for i in range(len(elements)):
        assert elements[i].metadata.to_dict() == {}


def test_partition_text_metadata_date(mocker: MockerFixture):
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-text.txt")
    mocked_last_modification_date = "2029-07-05T09:24:28"

    mocker.patch(
        "unstructured.partition.text.get_last_modified_date",
        return_value=mocked_last_modification_date,
    )

    elements = partition_text(
        filename=filename,
    )

    assert elements[0].metadata.last_modified == mocked_last_modification_date


def test_partition_text_with_custom_metadata_date(mocker: MockerFixture):
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-text.txt")
    mocked_last_modification_date = "2029-07-05T09:24:28"
    expected_last_modification_date = "2020-07-05T09:24:28"

    mocker.patch(
        "unstructured.partition.text.get_last_modified_date",
        return_value=mocked_last_modification_date,
    )

    elements = partition_text(
        filename=filename,
        metadata_last_modified=expected_last_modification_date,
    )

    assert elements[0].metadata.last_modified == expected_last_modification_date


def test_partition_text_from_file_metadata_date(mocker: MockerFixture):
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-text.txt")
    mocked_last_modification_date = "2029-07-05T09:24:28"

    mocker.patch(
        "unstructured.partition.text.get_last_modified_date_from_file",
        return_value=mocked_last_modification_date,
    )

    with open(filename, "rb") as f:
        elements = partition_text(
            file=f,
        )

    assert elements[0].metadata.last_modified == mocked_last_modification_date


def test_partition_text_from_file_with_custom_metadata_date(mocker: MockerFixture):
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-text.txt")
    mocked_last_modification_date = "2029-07-05T09:24:28"
    expected_last_modification_date = "2020-07-05T09:24:28"

    mocker.patch(
        "unstructured.partition.text.get_last_modified_date_from_file",
        return_value=mocked_last_modification_date,
    )

    with open(filename, "rb") as f:
        elements = partition_text(file=f, metadata_last_modified=expected_last_modification_date)

    assert elements[0].metadata.last_modified == expected_last_modification_date


def test_partition_text_from_text_metadata_date():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-text.txt")
    with open(filename) as f:
        text = f.read()

    elements = partition_text(
        text=text,
    )
    assert elements[0].metadata.last_modified is None


def test_partition_text_from_text_with_custom_metadata_date():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-text.txt")
    expected_last_modification_date = "2020-07-05T09:24:28"

    with open(filename) as f:
        text = f.read()

    elements = partition_text(text=text, metadata_last_modified=expected_last_modification_date)

    assert elements[0].metadata.last_modified == expected_last_modification_date


def test_partition_text_with_unique_ids():
    elements = partition_text(text="hello there!")
    assert elements[0].id == "c69509590d81db2f37f9d75480c8efed"
    # Test that the element is JSON serializable. This should run without an error
    json.dumps(elements[0].to_dict())

    elements = partition_text(text="hello there!", unique_element_ids=True)
    id = elements[0].id
    assert isinstance(id, str)  # included for type-narrowing
    assert len(id) == 36
    assert id.count("-") == 4
    # Test that the element is JSON serializable. This should run without an error
    json.dumps(elements[0].to_dict())


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
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "norwich-city.txt")
    elements = partition_text(filename=filename)
    chunk_elements = partition_text(filename, chunking_strategy="by_title")
    chunks = chunk_by_title(elements)
    assert chunk_elements != elements
    assert chunk_elements == chunks


def test_partition_text_element_metadata_has_languages():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "norwich-city.txt")
    elements = partition_text(filename=filename)
    assert elements[0].metadata.languages == ["eng"]


def test_partition_text_respects_detect_language_per_element():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "language-docs", "eng_spa_mult.txt")
    elements = partition_text(filename=filename, detect_language_per_element=True)
    langs = [element.metadata.languages for element in elements]
    assert langs == [["eng"], ["spa", "eng"], ["eng"], ["eng"], ["spa"]]


def test_partition_text_respects_languages_arg():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "norwich-city.txt")
    elements = partition_text(filename=filename, languages=["deu"])
    assert elements[0].metadata.languages == ["deu"]


def test_partition_text_element_metadata_raises_TypeError():
    with pytest.raises(TypeError):
        filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "norwich-city.txt")
        partition_text(filename=filename, languages="eng")  # type: ignore


def test_partition_text_detects_more_than_3_languages():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "language-docs", "UDHR_first_article_all.txt")
    elements = partition_text(filename=filename, detect_language_per_element=True)
    langs = list(
        {element.metadata.languages[0] for element in elements if element.metadata.languages},
    )
    assert len(langs) > 10
