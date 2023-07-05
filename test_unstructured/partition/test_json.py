import os
import pathlib
import tempfile

import pytest

from unstructured.partition.auto import partition
from unstructured.partition.json import partition_json
from unstructured.staging.base import elements_to_json

DIRECTORY = pathlib.Path(__file__).parent.resolve()

is_in_docker = os.path.exists("/.dockerenv")

test_files = [
    "fake-text.txt",
    "layout-parser-paper-fast.pdf",
    "fake-html.html",
    "fake.doc",
    "eml/fake-email.eml",
    pytest.param(
        "fake-power-point.ppt",
        marks=pytest.mark.skipif(is_in_docker, reason="Skipping this test in Docker container"),
    ),
    "fake.docx",
    "fake-power-point.pptx",
]

is_in_docker = os.path.exists("/.dockerenv")


@pytest.mark.parametrize("filename", test_files)
def test_partition_json_from_filename(filename: str):
    path = os.path.join(DIRECTORY, "..", "..", "example-docs", filename)
    elements = partition(filename=path)

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
    elements = partition(filename=path)

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
    elements = partition(filename=path)

    with tempfile.TemporaryDirectory() as tmpdir:
        _filename = os.path.basename(filename)
        test_path = os.path.join(tmpdir, _filename + ".json")
        elements_to_json(elements, filename=test_path, indent=2)
        with open(test_path) as f:
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
    elements = partition(filename=path)

    with tempfile.TemporaryDirectory() as tmpdir:
        _filename = os.path.basename(filename)
        test_path = os.path.join(tmpdir, _filename + ".json")
        elements_to_json(elements, filename=test_path, indent=2)
        with open(test_path) as f:
            test_elements = partition_json(file=f, metadata_filename="test")

    for i in range(len(test_elements)):
        assert test_elements[i].metadata.filename == "test"


@pytest.mark.parametrize("filename", test_files)
def test_partition_json_from_text(filename: str):
    path = os.path.join(DIRECTORY, "..", "..", "example-docs", filename)
    elements = partition(filename=path)

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
    elements = partition(filename=path)

    with tempfile.TemporaryDirectory() as tmpdir:
        test_path = os.path.join(tmpdir, "fake-text.txt.json")
        elements_to_json(elements, filename=test_path, indent=2)
        with open(test_path) as f:
            text = f.read()

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
    elements = partition(filename=path)

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
    elements = partition(filename=path)

    with tempfile.TemporaryDirectory() as tmpdir:
        _filename = os.path.basename(filename)
        test_path = os.path.join(tmpdir, _filename + ".json")
        elements_to_json(elements, filename=test_path, indent=2)
        with open(test_path) as f:
            test_elements = partition_json(file=f, include_metadata=False)

    for i in range(len(test_elements)):
        assert any(test_elements[i].metadata.to_dict()) is False


@pytest.mark.parametrize("filename", test_files)
def test_partition_json_from_text_exclude_metadata(filename: str):
    path = os.path.join(DIRECTORY, "..", "..", "example-docs", filename)
    elements = partition(filename=path)

    with tempfile.TemporaryDirectory() as tmpdir:
        _filename = os.path.basename(filename)
        test_path = os.path.join(tmpdir, _filename + ".json")
        elements_to_json(elements, filename=test_path, indent=2)
        with open(test_path) as f:
            text = f.read()
        test_elements = partition_json(text=text, include_metadata=False)

    for i in range(len(test_elements)):
        assert any(test_elements[i].metadata.to_dict()) is False
