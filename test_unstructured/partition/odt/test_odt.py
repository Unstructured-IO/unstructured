import os
import pathlib

from test_unstructured.unit_utils import assert_round_trips_through_JSON, example_doc_path
from unstructured.chunking.title import chunk_by_title
from unstructured.documents.elements import Table, TableChunk, Title
from unstructured.partition.odt import partition_odt
from unstructured.partition.utils.constants import UNSTRUCTURED_INCLUDE_DEBUG_METADATA

DIRECTORY = pathlib.Path(__file__).parent.resolve()
EXAMPLE_DOCS_DIRECTORY = os.path.join(DIRECTORY, "..", "..", "..", "example-docs")


def test_partition_odt_from_filename():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake.odt")
    elements = partition_odt(filename=filename)
    assert elements == [
        Title("Lorem ipsum dolor sit amet."),
        Table(
            text="\nHeader row  Mon    Wed"
            "   Fri\nColor       Blue"
            "   Red   Green\nTime        1pm"
            "    2pm   3pm\nLeader      "
            "Sarah  Mark  Ryan",
        ),
    ]
    for element in elements:
        assert element.metadata.filename == "fake.odt"
    if UNSTRUCTURED_INCLUDE_DEBUG_METADATA:
        assert {element.metadata.detection_origin for element in elements} == {
            "docx",
        }  # this file is processed by docx backend


def test_partition_odt_from_filename_with_metadata_filename():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake.odt")
    elements = partition_odt(filename=filename, metadata_filename="test")
    assert all(element.metadata.filename == "test" for element in elements)


def test_partition_odt_from_file():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake.odt")
    with open(filename, "rb") as f:
        elements = partition_odt(file=f)
    assert elements == [
        Title("Lorem ipsum dolor sit amet."),
        Table(
            text="\nHeader row  Mon    Wed"
            "   Fri\nColor       Blue"
            "   Red   Green\nTime        1pm"
            "    2pm   3pm\nLeader      "
            "Sarah  Mark  Ryan",
        ),
    ]


def test_partition_odt_from_file_with_metadata_filename():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake.odt")
    with open(filename, "rb") as f:
        elements = partition_odt(file=f, metadata_filename="test")

    assert all(element.metadata.filename == "test" for element in elements)


def test_partition_odt_from_filename_exclude_metadata():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake.odt")
    elements = partition_odt(filename=filename, include_metadata=False)

    for i in range(len(elements)):
        assert elements[i].metadata.to_dict() == {}


def test_partition_odt_from_file_exclude_metadata():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake.odt")
    with open(filename, "rb") as f:
        elements = partition_odt(file=f, include_metadata=False)

    for i in range(len(elements)):
        assert elements[i].metadata.to_dict() == {}


def test_partition_odt_metadata_date(
    mocker,
    filename="example-docs/fake.odt",
):
    mocked_last_modification_date = "2029-07-05T09:24:28"

    mocker.patch(
        "unstructured.partition.odt.get_last_modified_date",
        return_value=mocked_last_modification_date,
    )

    elements = partition_odt(
        filename=filename,
    )

    assert elements[0].metadata.last_modified == mocked_last_modification_date


def test_partition_odt_with_custom_metadata_date(
    mocker,
    filename="example-docs/fake.odt",
):
    mocked_last_modification_date = "2029-07-05T09:24:28"
    expected_last_modification_date = "2020-07-05T09:24:28"

    mocker.patch(
        "unstructured.partition.odt.get_last_modified_date",
        return_value=mocked_last_modification_date,
    )

    elements = partition_odt(
        filename=filename,
        metadata_last_modified=expected_last_modification_date,
    )

    assert elements[0].metadata.last_modified == expected_last_modification_date


def test_partition_odt_from_file_metadata_date(
    mocker,
    filename="example-docs/fake.odt",
):
    mocked_last_modification_date = "2029-07-05T09:24:28"

    mocker.patch(
        "unstructured.partition.odt.get_last_modified_date_from_file",
        return_value=mocked_last_modification_date,
    )

    with open(filename, "rb") as f:
        elements = partition_odt(
            file=f,
        )

    assert elements[0].metadata.last_modified == mocked_last_modification_date


def test_partition_odt_from_file_with_custom_metadata_date(
    mocker,
    filename="example-docs/fake.odt",
):
    mocked_last_modification_date = "2029-07-05T09:24:28"
    expected_last_modification_date = "2020-07-05T09:24:28"

    mocker.patch(
        "unstructured.partition.odt.get_last_modified_date_from_file",
        return_value=mocked_last_modification_date,
    )

    with open(filename, "rb") as f:
        elements = partition_odt(file=f, metadata_last_modified=expected_last_modification_date)

    assert elements[0].metadata.last_modified == expected_last_modification_date


def test_partition_odt_with_json():
    elements = partition_odt(example_doc_path("fake.odt"), include_metadata=True)
    assert_round_trips_through_JSON(elements)


def test_add_chunking_strategy_on_partition_odt(
    filename="example-docs/fake.odt",
):
    elements = partition_odt(filename=filename)
    chunk_elements = partition_odt(filename, chunking_strategy="by_title")
    chunks = chunk_by_title(elements)
    assert chunk_elements != elements
    assert chunk_elements == chunks


def test_add_chunking_strategy_on_partition_odt_non_default():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake.odt")
    elements = partition_odt(filename=filename)
    chunk_elements = partition_odt(
        filename,
        chunking_strategy="by_title",
        max_characters=7,
        combine_text_under_n_chars=5,
    )
    chunks = chunk_by_title(
        elements,
        max_characters=7,
        combine_text_under_n_chars=5,
    )
    for chunk in chunk_elements:
        if isinstance(chunk, TableChunk):
            assert len(chunk.text) <= 7
    assert chunk_elements != elements
    assert chunk_elements == chunks


def test_partition_odt_element_metadata_has_languages():
    filename = "example-docs/fake.odt"
    elements = partition_odt(filename=filename)
    assert elements[0].metadata.languages == ["eng"]


def test_partition_odt_respects_detect_language_per_element():
    filename = "example-docs/language-docs/eng_spa_mult.odt"
    elements = partition_odt(filename=filename, detect_language_per_element=True)
    langs = [element.metadata.languages for element in elements]
    assert langs == [["eng"], ["spa", "eng"], ["eng"], ["eng"], ["spa"]]
