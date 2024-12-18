"""Test-suite for `unstructured.partition.ndjson` module."""

from __future__ import annotations

import os
import pathlib
import tempfile

import pytest
from pytest_mock import MockFixture

from test_unstructured.unit_utils import example_doc_path
from unstructured.documents.elements import CompositeElement
from unstructured.file_utils.model import FileType
from unstructured.partition.email import partition_email
from unstructured.partition.html import partition_html
from unstructured.partition.ndjson import partition_ndjson
from unstructured.partition.text import partition_text
from unstructured.partition.xml import partition_xml
from unstructured.staging.base import elements_to_ndjson

DIRECTORY = pathlib.Path(__file__).parent.resolve()

is_in_docker = os.path.exists("/.dockerenv")

test_files = [
    "fake-text.txt",
    "fake-html.html",
    "eml/fake-email.eml",
]

is_in_docker = os.path.exists("/.dockerenv")


def test_it_chunks_elements_when_a_chunking_strategy_is_specified():
    chunks = partition_ndjson(
        example_doc_path("spring-weather.html.ndjson"),
        chunking_strategy="basic",
        max_characters=1500,
    )

    assert len(chunks) == 9
    assert all(isinstance(ch, CompositeElement) for ch in chunks)


@pytest.mark.parametrize("filename", test_files)
def test_partition_ndjson_from_filename(filename: str):
    path = example_doc_path(filename)
    elements = []
    filetype = FileType.from_extension(os.path.splitext(path)[1])
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
        test_path = os.path.join(tmpdir, _filename + ".ndjson")
        elements_to_ndjson(elements, filename=test_path)
        test_elements = partition_ndjson(filename=test_path)

    assert len(elements) > 0
    assert len(str(elements[0])) > 0

    assert len(elements) == len(test_elements)
    for i in range(len(elements)):
        assert elements[i] == test_elements[i]
        assert elements[i].metadata.filename == filename.split("/")[-1]


@pytest.mark.parametrize("filename", test_files)
def test_partition_ndjson_from_filename_with_metadata_filename(filename: str):
    path = example_doc_path(filename)
    elements = []
    filetype = FileType.from_extension(os.path.splitext(path)[1])
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
        test_path = os.path.join(tmpdir, _filename + ".ndjson")
        elements_to_ndjson(elements, filename=test_path)
        test_elements = partition_ndjson(filename=test_path, metadata_filename="test")

    assert len(test_elements) > 0
    assert len(str(test_elements[0])) > 0
    assert all(element.metadata.filename == "test" for element in test_elements)


@pytest.mark.parametrize("filename", test_files)
def test_partition_ndjson_from_file(filename: str):
    path = example_doc_path(filename)
    elements = []
    filetype = FileType.from_extension(os.path.splitext(path)[1])
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
        test_path = os.path.join(tmpdir, _filename + ".ndjson")
        elements_to_ndjson(elements, filename=test_path)
        with open(test_path, "rb") as f:
            test_elements = partition_ndjson(file=f)

    assert len(elements) > 0
    assert len(str(elements[0])) > 0
    assert len(elements) == len(test_elements)
    for i in range(len(elements)):
        assert elements[i] == test_elements[i]
        assert elements[i].metadata.filename == filename.split("/")[-1]


@pytest.mark.parametrize("filename", test_files)
def test_partition_ndjson_from_file_with_metadata_filename(filename: str):
    path = example_doc_path(filename)
    elements = []
    filetype = FileType.from_extension(os.path.splitext(path)[1])
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
        test_path = os.path.join(tmpdir, _filename + ".ndjson")
        elements_to_ndjson(elements, filename=test_path)
        with open(test_path, "rb") as f:
            test_elements = partition_ndjson(file=f, metadata_filename="test")

    for i in range(len(test_elements)):
        assert test_elements[i].metadata.filename == "test"


@pytest.mark.parametrize("filename", test_files)
def test_partition_ndjson_from_text(filename: str):
    path = example_doc_path(filename)
    elements = []
    filetype = FileType.from_extension(os.path.splitext(path)[1])
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
        test_path = os.path.join(tmpdir, _filename + ".ndjson")
        elements_to_ndjson(elements, filename=test_path)
        with open(test_path) as f:
            text = f.read()
        test_elements = partition_ndjson(text=text)

    assert len(elements) > 0
    assert len(str(elements[0])) > 0
    assert len(elements) == len(test_elements)
    for i in range(len(elements)):
        assert elements[i] == test_elements[i]
        assert elements[i].metadata.filename == filename.split("/")[-1]


def test_partition_json_raises_with_none_specified():
    with pytest.raises(ValueError):
        partition_ndjson()


def test_partition_ndjson_works_with_empty_string():
    assert partition_ndjson(text="") == []


def test_partition_ndjson_works_with_empty_list():
    assert partition_ndjson(text="{}") == []


def test_partition_ndjson_raises_with_too_many_specified():
    path = example_doc_path("fake-text.txt")
    elements = []
    filetype = FileType.from_extension(os.path.splitext(path)[1])
    if filetype == FileType.TXT:
        elements = partition_text(filename=path)
    if filetype == FileType.HTML:
        elements = partition_html(filename=path)
    if filetype == FileType.XML:
        elements = partition_xml(filename=path)
    if filetype == FileType.EML:
        elements = partition_email(filename=path)

    with tempfile.TemporaryDirectory() as tmpdir:
        test_path = os.path.join(tmpdir, "fake-text.txt.ndjson")
        elements_to_ndjson(elements, filename=test_path)
        with open(test_path, "rb") as f:
            text = f.read().decode("utf-8")

    with pytest.raises(ValueError):
        partition_ndjson(filename=test_path, file=f)

    with pytest.raises(ValueError):
        partition_ndjson(filename=test_path, text=text)

    with pytest.raises(ValueError):
        partition_ndjson(file=f, text=text)

    with pytest.raises(ValueError):
        partition_ndjson(filename=test_path, file=f, text=text)


# -- .metadata.last_modified ---------------------------------------------------------------------


def test_partition_ndjson_from_file_path_gets_last_modified_from_filesystem(mocker: MockFixture):
    filesystem_last_modified = "2029-07-05T09:24:28"
    mocker.patch(
        "unstructured.partition.ndjson.get_last_modified_date",
        return_value=filesystem_last_modified,
    )

    elements = partition_ndjson(example_doc_path("spring-weather.html.ndjson"))

    assert all(e.metadata.last_modified == filesystem_last_modified for e in elements)


def test_partition_ndjson_from_file_gets_last_modified_None():
    with open(example_doc_path("spring-weather.html.ndjson"), "rb") as f:
        elements = partition_ndjson(file=f)

    assert all(e.metadata.last_modified is None for e in elements)


def test_partition_ndjson_from_text_gets_last_modified_None():
    with open(example_doc_path("spring-weather.html.ndjson")) as f:
        text = f.read()

    elements = partition_ndjson(text=text)

    assert all(e.metadata.last_modified is None for e in elements)


def test_partition_ndjson_from_file_path_prefers_metadata_last_modified(mocker: MockFixture):
    filesystem_last_modified = "2029-07-05T09:24:28"
    metadata_last_modified = "2020-07-05T09:24:28"
    mocker.patch(
        "unstructured.partition.ndjson.get_last_modified_date",
        return_value=filesystem_last_modified,
    )

    elements = partition_ndjson(
        example_doc_path("spring-weather.html.ndjson"),
        metadata_last_modified=metadata_last_modified,
    )

    assert all(e.metadata.last_modified == metadata_last_modified for e in elements)


def test_partition_ndjson_from_file_prefers_metadata_last_modified():
    metadata_last_modified = "2020-07-05T09:24:28"
    with open(example_doc_path("spring-weather.html.ndjson"), "rb") as f:
        elements = partition_ndjson(file=f, metadata_last_modified=metadata_last_modified)

    assert all(e.metadata.last_modified == metadata_last_modified for e in elements)


def test_partition_ndjson_from_text_prefers_metadata_last_modified():
    metadata_last_modified = "2020-07-05T09:24:28"
    with open(example_doc_path("spring-weather.html.ndjson")) as f:
        text = f.read()

    elements = partition_ndjson(text=text, metadata_last_modified=metadata_last_modified)

    assert all(e.metadata.last_modified == metadata_last_modified for e in elements)


# ------------------------------------------------------------------------------------------------


def test_partition_json_raises_with_invalid_json():
    text = '[{"hi": "there"}]]'
    with pytest.raises(ValueError):
        partition_ndjson(text=text)
