import os
import pathlib

from test_unstructured.unit_utils import assert_round_trips_through_JSON, example_doc_path
from unstructured.chunking.title import chunk_by_title
from unstructured.documents.elements import Table, Title
from unstructured.partition.rtf import partition_rtf

DIRECTORY = pathlib.Path(__file__).parent.resolve()


def test_partition_rtf_from_filename():
    filename = os.path.join(DIRECTORY, "..", "..", "..", "example-docs", "fake-doc.rtf")
    elements = partition_rtf(filename=filename)
    assert len(elements) > 0
    assert elements[0] == Title("My First Heading")
    assert elements[-1] == Table(
        text="Column 1 \n Column 2 \n Row 1, Cell 1 \n Row 1, "
        "Cell 2 \n Row 2, Cell 1 \n Row 2, Cell 2",
    )
    for element in elements:
        assert element.metadata.filename == "fake-doc.rtf"


def test_partition_rtf_from_filename_with_metadata_filename():
    filename = os.path.join(DIRECTORY, "..", "..", "..", "example-docs", "fake-doc.rtf")
    elements = partition_rtf(filename=filename, metadata_filename="test")
    assert len(elements) > 0
    assert all(element.metadata.filename == "test" for element in elements)


def test_partition_rtf_from_file():
    filename = os.path.join(DIRECTORY, "..", "..", "..", "example-docs", "fake-doc.rtf")
    with open(filename, "rb") as f:
        elements = partition_rtf(file=f)
    assert len(elements) > 0
    assert elements[0] == Title("My First Heading")
    for element in elements:
        assert element.metadata.filename is None


def test_partition_rtf_from_file_with_metadata_filename():
    filename = os.path.join(DIRECTORY, "..", "..", "..", "example-docs", "fake-doc.rtf")
    with open(filename, "rb") as f:
        elements = partition_rtf(file=f, metadata_filename="test")
    assert elements[0] == Title("My First Heading")
    for element in elements:
        assert element.metadata.filename == "test"


def test_partition_rtf_from_filename_exclude_metadata():
    filename = os.path.join(DIRECTORY, "..", "..", "..", "example-docs", "fake-doc.rtf")
    elements = partition_rtf(filename=filename, include_metadata=False)
    for i in range(len(elements)):
        assert elements[i].metadata.to_dict() == {}


def test_partition_rtf_from_file_exclude_metadata():
    filename = os.path.join(DIRECTORY, "..", "..", "..", "example-docs", "fake-doc.rtf")
    with open(filename, "rb") as f:
        elements = partition_rtf(file=f, include_metadata=False)
    for i in range(len(elements)):
        assert elements[i].metadata.to_dict() == {}


def test_partition_rtf_metadata_date(
    mocker,
    filename="example-docs/fake-doc.rtf",
):
    mocked_last_modification_date = "2029-07-05T09:24:28"

    mocker.patch(
        "unstructured.partition.html.get_last_modified_date",
        return_value=mocked_last_modification_date,
    )

    elements = partition_rtf(
        filename=filename,
    )

    assert elements[0].metadata.last_modified == mocked_last_modification_date


def test_partition_rtf_with_custom_metadata_date(
    mocker,
    filename="example-docs/fake-doc.rtf",
):
    mocked_last_modification_date = "2029-07-05T09:24:28"
    expected_last_modification_date = "2020-07-05T09:24:28"

    mocker.patch(
        "unstructured.partition.html.get_last_modified_date",
        return_value=mocked_last_modification_date,
    )

    elements = partition_rtf(
        filename=filename,
        metadata_last_modified=expected_last_modification_date,
    )

    assert elements[0].metadata.last_modified == expected_last_modification_date


def test_partition_rtf_from_file_metadata_date(
    mocker,
    filename="example-docs/fake-doc.rtf",
):
    mocked_last_modification_date = "2029-07-05T09:24:28"

    mocker.patch(
        "unstructured.partition.html.get_last_modified_date_from_file",
        return_value=mocked_last_modification_date,
    )

    with open(filename, "rb") as f:
        elements = partition_rtf(
            file=f,
        )

    assert elements[0].metadata.last_modified == mocked_last_modification_date


def test_partition_rtf_from_file_with_custom_metadata_date(
    mocker,
    filename="example-docs/fake-doc.rtf",
):
    mocked_last_modification_date = "2029-07-05T09:24:28"
    expected_last_modification_date = "2020-07-05T09:24:28"

    mocker.patch(
        "unstructured.partition.html.get_last_modified_date_from_file",
        return_value=mocked_last_modification_date,
    )

    with open(filename, "rb") as f:
        elements = partition_rtf(file=f, metadata_last_modified=expected_last_modification_date)

    assert elements[0].metadata.last_modified == expected_last_modification_date


def test_partition_rtf_with_json():
    elements = partition_rtf(filename=example_doc_path("fake-doc.rtf"))
    assert_round_trips_through_JSON(elements)


def test_add_chunking_strategy_on_partition_rtf(filename="example-docs/fake-doc.rtf"):
    elements = partition_rtf(filename=filename)
    chunk_elements = partition_rtf(filename, chunking_strategy="by_title")
    chunks = chunk_by_title(elements)
    assert chunk_elements != elements
    assert chunk_elements == chunks


def test_partition_rtf_element_metadata_has_languages():
    filename = "example-docs/fake-doc.rtf"
    elements = partition_rtf(filename=filename)
    assert elements[0].metadata.languages == ["eng"]


def test_partition_rtf_respects_detect_language_per_element():
    filename = "example-docs/language-docs/eng_spa_mult.rtf"
    elements = partition_rtf(filename=filename, detect_language_per_element=True)
    langs = [element.metadata.languages for element in elements]
    assert langs == [["eng"], ["spa", "eng"], ["eng"], ["eng"], ["spa"]]
