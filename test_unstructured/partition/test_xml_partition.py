import os
import pathlib
from tempfile import SpooledTemporaryFile

import pytest

from unstructured.chunking.title import chunk_by_title
from unstructured.documents.elements import NarrativeText, Title
from unstructured.partition.json import partition_json
from unstructured.partition.utils.constants import UNSTRUCTURED_INCLUDE_DEBUG_METADATA
from unstructured.partition.xml import partition_xml
from unstructured.staging.base import elements_to_json

DIRECTORY = pathlib.Path(__file__).parent.resolve()


@pytest.mark.parametrize(
    "filename",
    ["factbook.xml", "factbook-utf-16.xml"],
)
def test_partition_xml_from_filename(filename):
    file_path = os.path.join(DIRECTORY, "..", "..", "example-docs", filename)
    elements = partition_xml(filename=file_path, xml_keep_tags=False)

    assert elements[0].text == "United States"
    assert elements[0].metadata.filename == filename
    if UNSTRUCTURED_INCLUDE_DEBUG_METADATA:
        assert {element.metadata.detection_origin for element in elements} == {"xml"}


def test_partition_xml_from_filename_with_metadata_filename():
    file_path = os.path.join(DIRECTORY, "..", "..", "example-docs", "factbook.xml")
    elements = partition_xml(filename=file_path, xml_keep_tags=False, metadata_filename="test")

    assert elements[0].text == "United States"
    assert elements[0].metadata.filename == "test"


@pytest.mark.parametrize(
    "filename",
    ["factbook.xml", "factbook-utf-16.xml"],
)
def test_partition_xml_from_file(filename):
    file_path = os.path.join(DIRECTORY, "..", "..", "example-docs", filename)
    with open(file_path, "rb") as f:
        elements = partition_xml(file=f, xml_keep_tags=False, metadata_filename=file_path)

    assert elements[0].text == "United States"
    assert elements[0].metadata.filename == filename


def test_partition_xml_from_file_with_metadata_filename():
    file_path = os.path.join(DIRECTORY, "..", "..", "example-docs", "factbook.xml")
    with open(file_path, "rb") as f:
        elements = partition_xml(file=f, xml_keep_tags=False, metadata_filename="test")

    assert elements[0].text == "United States"
    assert elements[0].metadata.filename == "test"


@pytest.mark.parametrize(
    "filename",
    ["factbook.xml", "factbook-utf-16.xml"],
)
def test_partition_xml_from_file_rb(filename):
    file_path = os.path.join(DIRECTORY, "..", "..", "example-docs", filename)
    with open(file_path, "rb") as f:
        elements = partition_xml(file=f, xml_keep_tags=False, metadata_filename=file_path)

    assert elements[0].text == "United States"
    assert elements[0].metadata.filename == filename


@pytest.mark.parametrize(
    "filename",
    ["factbook.xml", "factbook-utf-16.xml"],
)
def test_partition_xml_from_filename_with_tags_default_encoding(filename):
    file_path = os.path.join(DIRECTORY, "..", "..", "example-docs", filename)
    elements = partition_xml(filename=file_path, xml_keep_tags=True)

    assert "<leader>Joe Biden</leader>" in elements[0].text
    assert elements[0].metadata.filename == filename


def test_partition_xml_from_text_with_tags(filename="example-docs/factbook.xml"):
    with open(filename) as f:
        text = f.read()
    elements = partition_xml(text=text, xml_keep_tags=True, metadata_filename=filename)

    assert "<leader>Joe Biden</leader>" in elements[0].text
    assert elements[0].metadata.filename == "factbook.xml"


@pytest.mark.parametrize(
    ("filename", "encoding", "error"),
    [("factbook-utf-16.xml", "utf-8", UnicodeDecodeError)],
)
def test_partition_xml_from_filename_with_tags_raises_encoding_error(filename, encoding, error):
    with pytest.raises(error):
        file_path = os.path.join(DIRECTORY, "..", "..", "example-docs", filename)
        partition_xml(filename=file_path, xml_keep_tags=True, encoding=encoding)


@pytest.mark.parametrize(
    "filename",
    ["factbook.xml", "factbook-utf-16.xml"],
)
def test_partition_xml_from_file_with_tags_default_encoding(filename):
    file_path = os.path.join(DIRECTORY, "..", "..", "example-docs", filename)
    with open(file_path) as f:
        elements = partition_xml(file=f, xml_keep_tags=True, metadata_filename=file_path)

    assert "<leader>Joe Biden</leader>" in elements[0].text
    assert elements[0].metadata.filename == filename


@pytest.mark.parametrize(
    "filename",
    ["factbook.xml", "factbook-utf-16.xml"],
)
def test_partition_xml_from_file_rb_with_tags_default_encoding(filename):
    file_path = os.path.join(DIRECTORY, "..", "..", "example-docs", filename)
    with open(file_path, "rb") as f:
        elements = partition_xml(file=f, xml_keep_tags=True, metadata_filename=file_path)

    assert "<leader>Joe Biden</leader>" in elements[0].text
    assert elements[0].metadata.filename == filename


@pytest.mark.parametrize(
    ("filename", "encoding", "error"),
    [("factbook-utf-16.xml", "utf-8", UnicodeDecodeError)],
)
def test_partition_xml_from_file_rb_with_tags_raises_encoding_error(filename, encoding, error):
    file_path = os.path.join(DIRECTORY, "..", "..", "example-docs", filename)
    with pytest.raises(error), open(file_path, "rb") as f:
        partition_xml(
            file=f,
            xml_keep_tags=True,
            metadata_filename=file_path,
            encoding=encoding,
        )


@pytest.mark.parametrize(
    "filename",
    ["factbook.xml", "factbook-utf-16.xml"],
)
def test_partition_xml_from_filename_exclude_metadata(filename):
    file_path = os.path.join(DIRECTORY, "..", "..", "example-docs", filename)
    elements = partition_xml(filename=file_path, xml_keep_tags=False, include_metadata=False)

    assert elements[0].text == "United States"
    for i in range(len(elements)):
        assert elements[i].metadata.to_dict() == {}


@pytest.mark.parametrize(
    "filename",
    ["factbook.xml", "factbook-utf-16.xml"],
)
def test_partition_xml_from_file_exclude_metadata(filename):
    file_path = os.path.join(DIRECTORY, "..", "..", "example-docs", filename)
    with open(file_path, "rb") as f:
        elements = partition_xml(
            file=f,
            xml_keep_tags=False,
            metadata_filename=file_path,
            include_metadata=False,
        )

    assert elements[0].text == "United States"
    for i in range(len(elements)):
        assert elements[i].metadata.to_dict() == {}


def test_partition_xml_metadata_date(
    mocker,
    filename="example-docs/factbook.xml",
):
    mocked_last_modification_date = "2029-07-05T09:24:28"

    mocker.patch(
        "unstructured.partition.xml.get_last_modified_date",
        return_value=mocked_last_modification_date,
    )

    elements = partition_xml(
        filename=filename,
    )

    assert elements[0].metadata.last_modified == mocked_last_modification_date


def test_partition_xml_with_custom_metadata_date(
    mocker,
    filename="example-docs/factbook.xml",
):
    mocked_last_modification_date = "2029-07-05T09:24:28"
    expected_last_modification_date = "2020-07-05T09:24:28"

    mocker.patch(
        "unstructured.partition.xml.get_last_modified_date",
        return_value=mocked_last_modification_date,
    )

    elements = partition_xml(
        filename=filename,
        metadata_last_modified=expected_last_modification_date,
    )

    assert elements[0].metadata.last_modified == expected_last_modification_date


def test_partition_xml_from_file_metadata_date(
    mocker,
    filename="example-docs/factbook.xml",
):
    mocked_last_modification_date = "2029-07-05T09:24:28"

    mocker.patch(
        "unstructured.partition.xml.get_last_modified_date_from_file",
        return_value=mocked_last_modification_date,
    )

    with open(filename, "rb") as f:
        elements = partition_xml(
            file=f,
        )

    assert elements[0].metadata.last_modified is None


def test_partition_xml_from_file_explicit_get_metadata_date(
    mocker,
    filename="example-docs/factbook.xml",
):
    mocked_last_modification_date = "2029-07-05T09:24:28"

    mocker.patch(
        "unstructured.partition.xml.get_last_modified_date_from_file",
        return_value=mocked_last_modification_date,
    )

    with open(filename, "rb") as f:
        elements = partition_xml(file=f, date_from_file_object=True)

    assert elements[0].metadata.last_modified == mocked_last_modification_date


def test_partition_xml_from_file_with_custom_metadata_date(
    mocker,
    filename="example-docs/factbook.xml",
):
    mocked_last_modification_date = "2029-07-05T09:24:28"
    expected_last_modification_date = "2020-07-05T09:24:28"

    mocker.patch(
        "unstructured.partition.xml.get_last_modified_date_from_file",
        return_value=mocked_last_modification_date,
    )

    with open(filename, "rb") as f:
        elements = partition_xml(file=f, metadata_last_modified=expected_last_modification_date)

    assert elements[0].metadata.last_modified == expected_last_modification_date


def test_partition_xml_from_file_without_metadata_date(
    filename="example-docs/factbook.xml",
):
    """Test partition_xml() with file that are not possible to get last modified date"""
    with open(filename, "rb") as f:
        sf = SpooledTemporaryFile()
        sf.write(f.read())
        sf.seek(0)
        elements = partition_xml(file=sf, date_from_file_object=True)

    assert elements[0].metadata.last_modified is None


@pytest.mark.parametrize(
    "filename",
    ["factbook.xml", "factbook-utf-16.xml"],
)
def test_partition_xml_with_json(filename):
    file_path = os.path.join(DIRECTORY, "..", "..", "example-docs", filename)
    elements = partition_xml(filename=file_path, xml_keep_tags=False)
    test_elements = partition_json(text=elements_to_json(elements))

    assert len(elements) == len(test_elements)
    assert elements[0].metadata.page_number == test_elements[0].metadata.page_number
    assert elements[0].metadata.filename == test_elements[0].metadata.filename

    for i in range(len(elements)):
        assert elements[i] == test_elements[i]


def test_partition_xml_with_narrative_line_breaks():
    xml_text = """<xml>
        <parrot>
            <name>Conure</name>
            <description>A conure is a very friendly bird.
            Conures are feathery and like to dance.
            </description>
        </parrot>
    </xml>"""

    elements = partition_xml(text=xml_text)
    assert elements[0] == Title("Conure")
    assert isinstance(elements[1], NarrativeText)
    assert str(elements[1]).startswith("A conure is a very friendly bird.")
    assert str(elements[1]).strip().endswith("Conures are feathery and like to dance.")


def test_add_chunking_strategy_on_partition_xml(
    filename="example-docs/factbook.xml",
):
    elements = partition_xml(filename=filename)
    chunk_elements = partition_xml(filename, chunking_strategy="by_title")
    chunks = chunk_by_title(elements)
    assert chunk_elements != elements
    assert chunk_elements == chunks


def test_partition_xml_element_metadata_has_languages():
    filename = "example-docs/factbook.xml"
    elements = partition_xml(filename=filename)
    assert elements[0].metadata.languages == ["eng"]


def test_partition_xml_respects_detect_language_per_element():
    filename = "example-docs/language-docs/eng_spa_mult.xml"
    elements = partition_xml(filename=filename, detect_language_per_element=True)
    langs = [element.metadata.languages for element in elements]
    assert langs == [["eng"], ["spa", "eng"], ["eng"], ["eng"], ["spa"]]
