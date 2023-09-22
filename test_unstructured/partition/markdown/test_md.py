import os
import pathlib
from unittest.mock import patch

import pytest
import requests

from unstructured.chunking.title import chunk_by_title
from unstructured.documents.elements import Title
from unstructured.partition.json import partition_json
from unstructured.partition.md import partition_md
from unstructured.staging.base import elements_to_json

DIRECTORY = pathlib.Path(__file__).parent.resolve()


def test_partition_md_from_filename():
    filename = os.path.join(DIRECTORY, "..", "..", "..", "example-docs", "README.md")
    elements = partition_md(filename=filename)
    assert "PageBreak" not in [elem.category for elem in elements]
    assert len(elements) > 0
    for element in elements:
        assert element.metadata.filename == "README.md"


def test_partition_md_from_filename_returns_uns_elements():
    filename = os.path.join(DIRECTORY, "..", "..", "..", "example-docs", "README.md")
    elements = partition_md(filename=filename)
    assert len(elements) > 0
    assert isinstance(elements[0], Title)


def test_partition_md_from_filename_with_metadata_filename():
    filename = os.path.join(DIRECTORY, "..", "..", "..", "example-docs", "README.md")
    elements = partition_md(filename=filename, metadata_filename="test")
    assert "PageBreak" not in [elem.category for elem in elements]
    assert len(elements) > 0
    for element in elements:
        assert element.metadata.filename == "test"


def test_partition_md_from_file():
    filename = os.path.join(DIRECTORY, "..", "..", "..", "example-docs", "README.md")
    with open(filename) as f:
        elements = partition_md(file=f)
    assert len(elements) > 0
    for element in elements:
        assert element.metadata.filename is None


def test_partition_md_from_file_with_metadata_filename():
    filename = os.path.join(DIRECTORY, "..", "..", "..", "example-docs", "README.md")
    with open(filename) as f:
        elements = partition_md(file=f, metadata_filename="test")
    assert len(elements) > 0
    assert all(element.metadata.filename == "test" for element in elements)


def test_partition_md_from_text():
    filename = os.path.join(DIRECTORY, "..", "..", "..", "example-docs", "README.md")
    with open(filename) as f:
        text = f.read()
    elements = partition_md(text=text)
    assert len(elements) > 0
    for element in elements:
        assert element.metadata.filename is None


class MockResponse:
    def __init__(self, text, status_code, headers={}):
        self.text = text
        self.status_code = status_code
        self.ok = status_code < 300
        self.headers = headers


def test_partition_md_from_url():
    filename = os.path.join(DIRECTORY, "..", "..", "..", "example-docs", "README.md")
    with open(filename) as f:
        text = f.read()

    response = MockResponse(
        text=text,
        status_code=200,
        headers={"Content-Type": "text/markdown"},
    )
    with patch.object(requests, "get", return_value=response) as _:
        elements = partition_md(url="https://fake.url")

    assert len(elements) > 0
    for element in elements:
        assert element.metadata.filename is None


def test_partition_md_from_url_raises_with_bad_status_code():
    filename = os.path.join(DIRECTORY, "..", "..", "..", "example-docs", "README.md")
    with open(filename) as f:
        text = f.read()

    response = MockResponse(
        text=text,
        status_code=500,
        headers={"Content-Type": "text/html"},
    )
    with patch.object(requests, "get", return_value=response) as _, pytest.raises(ValueError):
        partition_md(url="https://fake.url")


def test_partition_md_from_url_raises_with_bad_content_type():
    filename = os.path.join(DIRECTORY, "..", "..", "..", "example-docs", "README.md")
    with open(filename) as f:
        text = f.read()

    response = MockResponse(
        text=text,
        status_code=200,
        headers={"Content-Type": "application/json"},
    )
    with patch.object(requests, "get", return_value=response) as _, pytest.raises(ValueError):
        partition_md(url="https://fake.url")


def test_partition_md_raises_with_none_specified():
    with pytest.raises(ValueError):
        partition_md()


def test_partition_md_raises_with_too_many_specified():
    filename = os.path.join(DIRECTORY, "..", "..", "..", "example-docs", "README.md")
    with open(filename) as f:
        text = f.read()

    with pytest.raises(ValueError):
        partition_md(filename=filename, text=text)


def test_partition_md_from_filename_exclude_metadata():
    filename = os.path.join(DIRECTORY, "..", "..", "..", "example-docs", "README.md")
    elements = partition_md(filename=filename, include_metadata=False)
    for i in range(len(elements)):
        assert elements[i].metadata.to_dict() == {}


def test_partition_md_from_file_exclude_metadata():
    filename = os.path.join(DIRECTORY, "..", "..", "..", "example-docs", "README.md")
    with open(filename) as f:
        elements = partition_md(file=f, include_metadata=False)
    for i in range(len(elements)):
        assert elements[i].metadata.to_dict() == {}


def test_partition_md_from_text_exclude_metadata():
    filename = os.path.join(DIRECTORY, "..", "..", "..", "example-docs", "README.md")
    with open(filename) as f:
        text = f.read()
    elements = partition_md(text=text, include_metadata=False)
    for i in range(len(elements)):
        assert elements[i].metadata.to_dict() == {}


def test_partition_md_metadata_date(
    mocker,
    filename="example-docs/README.md",
):
    mocked_last_modification_date = "2029-07-05T09:24:28"

    mocker.patch(
        "unstructured.partition.md.get_last_modified_date",
        return_value=mocked_last_modification_date,
    )

    elements = partition_md(
        filename=filename,
    )

    assert elements[0].metadata.last_modified == mocked_last_modification_date


def test_partition_md_with_custom_metadata_date(
    mocker,
    filename="example-docs/README.md",
):
    mocked_last_modification_date = "2029-07-05T09:24:28"
    expected_last_modification_date = "2020-07-05T09:24:28"

    mocker.patch(
        "unstructured.partition.md.get_last_modified_date",
        return_value=mocked_last_modification_date,
    )

    elements = partition_md(
        filename=filename,
        metadata_last_modified=expected_last_modification_date,
    )

    assert elements[0].metadata.last_modified == expected_last_modification_date


def test_partition_md_from_file_metadata_date(
    mocker,
    filename="example-docs/README.md",
):
    mocked_last_modification_date = "2029-07-05T09:24:28"

    mocker.patch(
        "unstructured.partition.md.get_last_modified_date_from_file",
        return_value=mocked_last_modification_date,
    )

    with open(filename, "rb") as f:
        elements = partition_md(
            file=f,
        )

    assert elements[0].metadata.last_modified == mocked_last_modification_date


def test_partition_md_from_file_with_custom_metadata_date(
    mocker,
    filename="example-docs/README.md",
):
    mocked_last_modification_date = "2029-07-05T09:24:28"
    expected_last_modification_date = "2020-07-05T09:24:28"

    mocker.patch(
        "unstructured.partition.md.get_last_modified_date_from_file",
        return_value=mocked_last_modification_date,
    )

    with open(filename, "rb") as f:
        elements = partition_md(file=f, metadata_last_modified=expected_last_modification_date)

    assert elements[0].metadata.last_modified == expected_last_modification_date


def test_partition_md_from_text_metadata_date(
    filename="example-docs/README.md",
):
    with open(filename) as f:
        text = f.read()

    elements = partition_md(
        text=text,
    )

    assert elements[0].metadata.last_modified is None


def test_partition_md_from_text_with_custom_metadata_date(
    filename="example-docs/README.md",
):
    expected_last_modification_date = "2020-07-05T09:24:28"

    with open(filename) as f:
        text = f.read()

    elements = partition_md(text=text, metadata_last_modified=expected_last_modification_date)

    assert elements[0].metadata.last_modified == expected_last_modification_date


def test_partition_md_with_json(
    filename="example-docs/README.md",
):
    with open(filename) as f:
        text = f.read()

    elements = partition_md(
        text=text,
    )
    test_elements = partition_json(text=elements_to_json(elements))

    assert len(elements) == len(test_elements)
    assert elements[0].metadata.filename == test_elements[0].metadata.filename
    for i in range(len(elements)):
        assert elements[i] == test_elements[i]


def test_add_chunking_strategy_on_partition_md(
    filename="example-docs/README.md",
):
    elements = partition_md(filename=filename)
    chunk_elements = partition_md(filename, chunking_strategy="by_title")
    chunks = chunk_by_title(elements)
    assert chunk_elements != elements
    assert chunk_elements == chunks
