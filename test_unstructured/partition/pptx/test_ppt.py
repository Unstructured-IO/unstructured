import os
import pathlib

import pytest

from test_unstructured.unit_utils import assert_round_trips_through_JSON, example_doc_path
from unstructured.chunking.title import chunk_by_title
from unstructured.documents.elements import ListItem, NarrativeText, Title
from unstructured.partition.ppt import partition_ppt
from unstructured.partition.utils.constants import UNSTRUCTURED_INCLUDE_DEBUG_METADATA

DIRECTORY = pathlib.Path(__file__).parent.resolve()
EXAMPLE_DOCS_DIRECTORY = os.path.join(DIRECTORY, "..", "..", "..", "example-docs")

EXPECTED_PPT_OUTPUT = [
    Title(text="Adding a Bullet Slide"),
    ListItem(text="Find the bullet slide layout"),
    ListItem(text="Use _TextFrame.text for first bullet"),
    ListItem(text="Use _TextFrame.add_paragraph() for subsequent bullets"),
    NarrativeText(text="Here is a lot of text!"),
    NarrativeText(text="Here is some text in a text box!"),
]


def test_partition_ppt_from_filename():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-power-point.ppt")
    elements = partition_ppt(filename=filename)
    assert elements == EXPECTED_PPT_OUTPUT
    for element in elements:
        assert element.metadata.filename == "fake-power-point.ppt"
    if UNSTRUCTURED_INCLUDE_DEBUG_METADATA:
        assert {element.metadata.detection_origin for element in elements} == {"pptx"}


def test_partition_ppt_from_filename_with_metadata_filename():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-power-point.ppt")
    elements = partition_ppt(filename=filename, metadata_filename="test")
    assert all(element.metadata.filename == "test" for element in elements)


def test_partition_ppt_raises_with_missing_file():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "doesnt-exist.ppt")
    with pytest.raises(ValueError):
        partition_ppt(filename=filename)


def test_partition_ppt_from_file():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-power-point.ppt")
    with open(filename, "rb") as f:
        elements = partition_ppt(file=f)
    assert elements == EXPECTED_PPT_OUTPUT
    for element in elements:
        assert element.metadata.filename is None


def test_partition_ppt_from_file_with_metadata_filename():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-power-point.ppt")
    with open(filename, "rb") as f:
        elements = partition_ppt(file=f, metadata_filename="test")
    assert elements == EXPECTED_PPT_OUTPUT
    for element in elements:
        assert element.metadata.filename == "test"


def test_partition_ppt_raises_with_both_specified():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-power-point.ppt")
    with open(filename, "rb") as f, pytest.raises(ValueError):
        partition_ppt(filename=filename, file=f)


def test_partition_ppt_raises_with_neither():
    with pytest.raises(ValueError):
        partition_ppt()


def test_partition_ppt_from_filename_exclude_metadata():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-power-point.ppt")
    elements = partition_ppt(filename=filename, include_metadata=False)
    for i in range(len(elements)):
        assert elements[i].metadata.to_dict() == {}


def test_partition_ppt_from_file_exclude_metadata():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-power-point.ppt")
    with open(filename, "rb") as f:
        elements = partition_ppt(file=f, include_metadata=False)
    for i in range(len(elements)):
        assert elements[i].metadata.to_dict() == {}


def test_partition_ppt_metadata_date(
    mocker,
    filename="example-docs/fake-power-point.ppt",
):
    mocked_last_modification_date = "2029-07-05T09:24:28"

    mocker.patch(
        "unstructured.partition.ppt.get_last_modified_date",
        return_value=mocked_last_modification_date,
    )

    elements = partition_ppt(
        filename=filename,
    )

    assert elements[0].metadata.last_modified == mocked_last_modification_date


def test_partition_ppt_with_custom_metadata_date(
    mocker,
    filename="example-docs/fake-power-point.ppt",
):
    mocked_last_modification_date = "2029-07-05T09:24:28"
    expected_last_modification_date = "2020-07-05T09:24:28"

    mocker.patch(
        "unstructured.partition.ppt.get_last_modified_date",
        return_value=mocked_last_modification_date,
    )

    elements = partition_ppt(
        filename=filename,
        metadata_last_modified=expected_last_modification_date,
    )

    assert elements[0].metadata.last_modified == expected_last_modification_date


def test_partition_ppt_from_file_metadata_date(
    mocker,
    filename="example-docs/fake-power-point.ppt",
):
    mocked_last_modification_date = "2029-07-05T09:24:28"

    mocker.patch(
        "unstructured.partition.ppt.get_last_modified_date_from_file",
        return_value=mocked_last_modification_date,
    )

    with open(filename, "rb") as f:
        elements = partition_ppt(
            file=f,
        )

    assert elements[0].metadata.last_modified == mocked_last_modification_date


def test_partition_ppt_from_file_with_custom_metadata_date(
    mocker,
    filename="example-docs/fake-power-point.ppt",
):
    mocked_last_modification_date = "2029-07-05T09:24:28"
    expected_last_modification_date = "2020-07-05T09:24:28"

    mocker.patch(
        "unstructured.partition.ppt.get_last_modified_date_from_file",
        return_value=mocked_last_modification_date,
    )

    with open(filename, "rb") as f:
        elements = partition_ppt(file=f, metadata_last_modified=expected_last_modification_date)

    assert elements[0].metadata.last_modified == expected_last_modification_date


def test_partition_ppt_with_json():
    elements = partition_ppt(example_doc_path("fake-power-point.ppt"))
    assert_round_trips_through_JSON(elements)


def test_add_chunking_strategy_by_title_on_partition_ppt(
    filename=os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-power-point.ppt"),
):
    elements = partition_ppt(filename=filename)
    chunk_elements = partition_ppt(filename, chunking_strategy="by_title")
    chunks = chunk_by_title(elements)
    assert chunk_elements != elements
    assert chunk_elements == chunks


def test_partition_ppt_element_metadata_has_languages():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-power-point.ppt")
    elements = partition_ppt(filename=filename)
    assert elements[0].metadata.languages == ["eng"]


def test_partition_ppt_respects_detect_language_per_element():
    filename = "example-docs/language-docs/eng_spa_mult.ppt"
    elements = partition_ppt(filename=filename, detect_language_per_element=True)
    langs = [element.metadata.languages for element in elements]
    # languages other than English and Spanish are detected by this partitioner,
    # so this test is slightly different from the other partition tests
    langs = {element.metadata.languages[0] for element in elements if element.metadata.languages}
    assert "eng" in langs
    assert "spa" in langs
