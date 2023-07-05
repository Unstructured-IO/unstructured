import os
import pathlib

import pytest

from unstructured.partition.xml import partition_xml

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
    with open(file_path) as f:
        elements = partition_xml(file=f, xml_keep_tags=False, metadata_filename=file_path)

    assert elements[0].text == "United States"
    assert elements[0].metadata.filename == filename


def test_partition_xml_from_file_with_metadata_filename():
    file_path = os.path.join(DIRECTORY, "..", "..", "example-docs", "factbook.xml")
    with open(file_path) as f:
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

    assert elements[5].text == "<name>United States</name>"
    assert elements[5].metadata.filename == filename


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

    assert elements[5].text == "<name>United States</name>"
    assert elements[5].metadata.filename == filename


@pytest.mark.parametrize(
    "filename",
    ["factbook.xml", "factbook-utf-16.xml"],
)
def test_partition_xml_from_file_rb_with_tags_default_encoding(filename):
    file_path = os.path.join(DIRECTORY, "..", "..", "example-docs", filename)
    with open(file_path, "rb") as f:
        elements = partition_xml(file=f, xml_keep_tags=True, metadata_filename=file_path)

    assert elements[5].text == "<name>United States</name>"
    assert elements[5].metadata.filename == filename


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
    with open(file_path) as f:
        elements = partition_xml(
            file=f,
            xml_keep_tags=False,
            metadata_filename=file_path,
            include_metadata=False,
        )

    assert elements[0].text == "United States"
    for i in range(len(elements)):
        assert elements[i].metadata.to_dict() == {}
