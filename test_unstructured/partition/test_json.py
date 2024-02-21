"""Test-suite for `unstructured.partition.json` module."""

from __future__ import annotations

import os
import pathlib
import tempfile

import pytest
from pytest_mock import MockFixture

from unstructured.documents.elements import CompositeElement
from unstructured.file_utils.filetype import FileType, detect_filetype
from unstructured.partition.email import partition_email
from unstructured.partition.html import partition_html
from unstructured.partition.json import partition_json
from unstructured.partition.text import partition_text
from unstructured.partition.xml import partition_xml
from unstructured.staging.base import elements_to_json

DIRECTORY = pathlib.Path(__file__).parent.resolve()

is_in_docker = os.path.exists("/.dockerenv")

test_files = [
    "fake-text.txt",
    "fake-html.html",
    "eml/fake-email.eml",
]

is_in_docker = os.path.exists("/.dockerenv")


def test_it_chunks_elements_when_a_chunking_strategy_is_specified():
    chunks = partition_json(
        "example-docs/spring-weather.html.json", chunking_strategy="basic", max_characters=1500
    )

    assert len(chunks) == 10
    assert all(isinstance(ch, CompositeElement) for ch in chunks)


@pytest.mark.parametrize("filename", test_files)
def test_partition_json_from_filename(filename: str):
    path = os.path.join(DIRECTORY, "..", "..", "example-docs", filename)
    elements = []
    filetype = detect_filetype(filename=path)
    if filetype == FileType.TXT:
        elements = partition_text(filename=path)
    if filetype == FileType.HTML:
        elements = partition_html(filename=path)
    if filetype == FileType.XML:
        elements = partition_xml(filename=path)
    if filetype == FileType.EML:
        elements = partition_email(filename=path)

    with tempfile.TemporaryDirectory() as tmpdir:
        _filename = os.path.basename(filename)
        test_path = os.path.join(tmpdir, _filename + ".json")
        elements_to_json(elements, filename=test_path, indent=2)
        test_elements = partition_json(filename=test_path)

    assert len(elements) > 0
    assert len(str(elements[0])) > 0

    assert len(elements) == len(test_elements)
    for i in range(len(elements)):
        assert elements[i] == test_elements[i]
        assert elements[i].metadata.filename == filename.split("/")[-1]


@pytest.mark.parametrize("filename", test_files)
def test_partition_json_from_filename_with_metadata_filename(filename: str):
    path = os.path.join(DIRECTORY, "..", "..", "example-docs", filename)
    elements = []
    filetype = detect_filetype(filename=path)
    if filetype == FileType.TXT:
        elements = partition_text(filename=path)
    if filetype == FileType.HTML:
        elements = partition_html(filename=path)
    if filetype == FileType.XML:
        elements = partition_xml(filename=path)
    if filetype == FileType.EML:
        elements = partition_email(filename=path)

    with tempfile.TemporaryDirectory() as tmpdir:
        _filename = os.path.basename(filename)
        test_path = os.path.join(tmpdir, _filename + ".json")
        elements_to_json(elements, filename=test_path, indent=2)
        test_elements = partition_json(filename=test_path, metadata_filename="test")

    assert len(test_elements) > 0
    assert len(str(test_elements[0])) > 0
    assert all(element.metadata.filename == "test" for element in test_elements)


@pytest.mark.parametrize("filename", test_files)
def test_partition_json_from_file(filename: str):
    path = os.path.join(DIRECTORY, "..", "..", "example-docs", filename)
    elements = []
    filetype = detect_filetype(filename=path)
    if filetype == FileType.TXT:
        elements = partition_text(filename=path)
    if filetype == FileType.HTML:
        elements = partition_html(filename=path)
    if filetype == FileType.XML:
        elements = partition_xml(filename=path)
    if filetype == FileType.EML:
        elements = partition_email(filename=path)

    with tempfile.TemporaryDirectory() as tmpdir:
        _filename = os.path.basename(filename)
        test_path = os.path.join(tmpdir, _filename + ".json")
        elements_to_json(elements, filename=test_path, indent=2)
        with open(test_path, "rb") as f:
            test_elements = partition_json(file=f)

    assert len(elements) > 0
    assert len(str(elements[0])) > 0
    assert len(elements) == len(test_elements)
    for i in range(len(elements)):
        assert elements[i] == test_elements[i]
        assert elements[i].metadata.filename == filename.split("/")[-1]


@pytest.mark.parametrize("filename", test_files)
def test_partition_json_from_file_with_metadata_filename(filename: str):
    path = os.path.join(DIRECTORY, "..", "..", "example-docs", filename)
    elements = []
    filetype = detect_filetype(filename=path)
    if filetype == FileType.TXT:
        elements = partition_text(filename=path)
    if filetype == FileType.HTML:
        elements = partition_html(filename=path)
    if filetype == FileType.XML:
        elements = partition_xml(filename=path)
    if filetype == FileType.EML:
        elements = partition_email(filename=path)
    with tempfile.TemporaryDirectory() as tmpdir:
        _filename = os.path.basename(filename)
        test_path = os.path.join(tmpdir, _filename + ".json")
        elements_to_json(elements, filename=test_path, indent=2)
        with open(test_path, "rb") as f:
            test_elements = partition_json(file=f, metadata_filename="test")

    for i in range(len(test_elements)):
        assert test_elements[i].metadata.filename == "test"


@pytest.mark.parametrize("filename", test_files)
def test_partition_json_from_text(filename: str):
    path = os.path.join(DIRECTORY, "..", "..", "example-docs", filename)
    elements = []
    filetype = detect_filetype(filename=path)
    if filetype == FileType.TXT:
        elements = partition_text(filename=path)
    if filetype == FileType.HTML:
        elements = partition_html(filename=path)
    if filetype == FileType.XML:
        elements = partition_xml(filename=path)
    if filetype == FileType.EML:
        elements = partition_email(filename=path)

    with tempfile.TemporaryDirectory() as tmpdir:
        _filename = os.path.basename(filename)
        test_path = os.path.join(tmpdir, _filename + ".json")
        elements_to_json(elements, filename=test_path, indent=2)
        with open(test_path) as f:
            text = f.read()
        test_elements = partition_json(text=text)

    assert len(elements) > 0
    assert len(str(elements[0])) > 0
    assert len(elements) == len(test_elements)
    for i in range(len(elements)):
        assert elements[i] == test_elements[i]
        assert elements[i].metadata.filename == filename.split("/")[-1]


def test_partition_json_raises_with_none_specified():
    with pytest.raises(ValueError):
        partition_json()


def test_partition_json_works_with_empty_string():
    assert partition_json(text="") == []


def test_partition_json_works_with_empty_list():
    assert partition_json(text="[]") == []


def test_partition_json_raises_with_too_many_specified():
    path = os.path.join(DIRECTORY, "..", "..", "example-docs", "fake-text.txt")
    elements = []
    filetype = detect_filetype(filename=path)
    if filetype == FileType.TXT:
        elements = partition_text(filename=path)
    if filetype == FileType.HTML:
        elements = partition_html(filename=path)
    if filetype == FileType.XML:
        elements = partition_xml(filename=path)
    if filetype == FileType.EML:
        elements = partition_email(filename=path)

    with tempfile.TemporaryDirectory() as tmpdir:
        test_path = os.path.join(tmpdir, "fake-text.txt.json")
        elements_to_json(elements, filename=test_path, indent=2)
        with open(test_path, "rb") as f:
            text = f.read().decode("utf-8")

    with pytest.raises(ValueError):
        partition_json(filename=test_path, file=f)

    with pytest.raises(ValueError):
        partition_json(filename=test_path, text=text)

    with pytest.raises(ValueError):
        partition_json(file=f, text=text)

    with pytest.raises(ValueError):
        partition_json(filename=test_path, file=f, text=text)


@pytest.mark.parametrize("filename", test_files)
def test_partition_json_from_filename_exclude_metadata(filename: str):
    path = os.path.join(DIRECTORY, "..", "..", "example-docs", filename)
    elements = []
    filetype = detect_filetype(filename=path)
    if filetype == FileType.TXT:
        elements = partition_text(filename=path)
    if filetype == FileType.HTML:
        elements = partition_html(filename=path)
    if filetype == FileType.XML:
        elements = partition_xml(filename=path)
    if filetype == FileType.EML:
        elements = partition_email(filename=path)

    with tempfile.TemporaryDirectory() as tmpdir:
        _filename = os.path.basename(filename)
        test_path = os.path.join(tmpdir, _filename + ".json")
        elements_to_json(elements, filename=test_path, indent=2)
        test_elements = partition_json(filename=test_path, include_metadata=False)

    for i in range(len(test_elements)):
        assert any(test_elements[i].metadata.to_dict()) is False


@pytest.mark.parametrize("filename", test_files)
def test_partition_json_from_file_exclude_metadata(filename: str):
    path = os.path.join(DIRECTORY, "..", "..", "example-docs", filename)
    elements = []
    filetype = detect_filetype(filename=path)
    if filetype == FileType.TXT:
        elements = partition_text(filename=path)
    if filetype == FileType.HTML:
        elements = partition_html(filename=path)
    if filetype == FileType.XML:
        elements = partition_xml(filename=path)
    if filetype == FileType.EML:
        elements = partition_email(filename=path)

    with tempfile.TemporaryDirectory() as tmpdir:
        _filename = os.path.basename(filename)
        test_path = os.path.join(tmpdir, _filename + ".json")
        elements_to_json(elements, filename=test_path, indent=2)
        with open(test_path, "rb") as f:
            test_elements = partition_json(file=f, include_metadata=False)

    for i in range(len(test_elements)):
        assert any(test_elements[i].metadata.to_dict()) is False


@pytest.mark.parametrize("filename", test_files)
def test_partition_json_from_text_exclude_metadata(filename: str):
    path = os.path.join(DIRECTORY, "..", "..", "example-docs", filename)
    elements = []
    filetype = detect_filetype(filename=path)
    if filetype == FileType.TXT:
        elements = partition_text(filename=path)
    if filetype == FileType.HTML:
        elements = partition_html(filename=path)
    if filetype == FileType.XML:
        elements = partition_xml(filename=path)
    if filetype == FileType.EML:
        elements = partition_email(filename=path)

    with tempfile.TemporaryDirectory() as tmpdir:
        _filename = os.path.basename(filename)
        test_path = os.path.join(tmpdir, _filename + ".json")
        elements_to_json(elements, filename=test_path, indent=2)
        with open(test_path) as f:
            text = f.read()
        test_elements = partition_json(text=text, include_metadata=False)

    for i in range(len(test_elements)):
        assert any(test_elements[i].metadata.to_dict()) is False


def test_partition_json_metadata_date(mocker: MockFixture):
    mocked_last_modification_date = "2029-07-05T09:24:28"
    mocker.patch(
        "unstructured.partition.json.get_last_modified_date",
        return_value=mocked_last_modification_date,
    )

    elements = partition_json("example-docs/spring-weather.html.json")

    assert elements[0].metadata.last_modified == mocked_last_modification_date


def test_partition_json_with_custom_metadata_date(mocker: MockFixture):
    mocked_last_modification_date = "2029-07-05T09:24:28"
    expected_last_modification_date = "2020-07-05T09:24:28"
    mocker.patch(
        "unstructured.partition.json.get_last_modified_date",
        return_value=mocked_last_modification_date,
    )

    elements = partition_json(
        "example-docs/spring-weather.html.json",
        metadata_last_modified=expected_last_modification_date,
    )

    assert elements[0].metadata.last_modified == expected_last_modification_date


def test_partition_json_from_file_metadata_date(mocker: MockFixture):
    mocked_last_modification_date = "2029-07-05T09:24:28"
    mocker.patch(
        "unstructured.partition.json.get_last_modified_date_from_file",
        return_value=mocked_last_modification_date,
    )

    with open("example-docs/spring-weather.html.json", "rb") as f:
        elements = partition_json(file=f)

    assert elements[0].metadata.last_modified == mocked_last_modification_date


def test_partition_json_from_file_with_custom_metadata_date(mocker: MockFixture):
    mocked_last_modification_date = "2029-07-05T09:24:28"
    expected_last_modification_date = "2020-07-05T09:24:28"
    mocker.patch(
        "unstructured.partition.json.get_last_modified_date_from_file",
        return_value=mocked_last_modification_date,
    )

    with open("example-docs/spring-weather.html.json", "rb") as f:
        elements = partition_json(file=f, metadata_last_modified=expected_last_modification_date)

    assert elements[0].metadata.last_modified == expected_last_modification_date


def test_partition_json_from_text_metadata_date():
    with open("example-docs/spring-weather.html.json") as f:
        text = f.read()

    elements = partition_json(text=text)

    assert elements[0].metadata.last_modified is None


def test_partition_json_from_text_with_custom_metadata_date():
    expected_last_modification_date = "2020-07-05T09:24:28"
    with open("example-docs/spring-weather.html.json") as f:
        text = f.read()

    elements = partition_json(text=text, metadata_last_modified=expected_last_modification_date)

    assert elements[0].metadata.last_modified == expected_last_modification_date


def test_partition_json_raises_with_unprocessable_json():
    # NOTE(robinson) - This is unprocessable because it is not a list of dicts,
    # per the Unstructured ISD format
    text = '{"hi": "there"}'
    with pytest.raises(ValueError):
        partition_json(text=text)


def test_partition_json_raises_with_invalid_json():
    text = '[{"hi": "there"}]]'
    with pytest.raises(ValueError):
        partition_json(text=text)
