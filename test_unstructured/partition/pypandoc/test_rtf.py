import os
import pathlib

from unstructured.cleaners.core import clean_extra_whitespace
from unstructured.documents.elements import Title
from unstructured.partition.json import partition_json
from unstructured.partition.rtf import partition_rtf
from unstructured.staging.base import elements_to_json

DIRECTORY = pathlib.Path(__file__).parent.resolve()


def test_partition_rtf_from_filename():
    filename = os.path.join(DIRECTORY, "..", "..", "..", "example-docs", "fake-doc.rtf")
    elements = partition_rtf(filename=filename)
    assert len(elements) > 0
    assert elements[0] == Title("My First Heading")
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
    filename = os.path.join(DIRECTORY, "..", "..", "..", "example-docs", "fake-doc.rtf")
    elements = partition_rtf(filename=filename)

    test_elements = partition_json(text=elements_to_json(elements))

    assert len(elements) == len(test_elements)
    assert clean_extra_whitespace(elements[0].text) == clean_extra_whitespace(test_elements[0].text)
    assert elements[0].metadata.filename == test_elements[0].metadata.filename

    for i in range(len(elements)):
        assert elements[i] == test_elements[i]
