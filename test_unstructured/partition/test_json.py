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
    "fake-email.eml",
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
        test_path = os.path.join(tmpdir, filename + ".json")
        elements_to_json(elements, filename=test_path, indent=2)
        test_elements = partition_json(filename=test_path)

    assert len(elements) > 0
    assert len(str(elements[0])) > 0

    assert len(elements) == len(test_elements)
    for i in range(len(elements)):
        print(elements[i].coordinates)
        print(test_elements[i].coordinates)
        assert elements[i] == test_elements[i]


@pytest.mark.parametrize("filename", test_files)
def test_partition_json_from_file(filename: str):
    path = os.path.join(DIRECTORY, "..", "..", "example-docs", filename)
    elements = partition(filename=path)

    with tempfile.TemporaryDirectory() as tmpdir:
        test_path = os.path.join(tmpdir, filename + ".json")
        elements_to_json(elements, filename=test_path, indent=2)
        with open(test_path) as f:
            test_elements = partition_json(file=f)

    assert len(elements) > 0
    assert len(str(elements[0])) > 0

    assert len(elements) == len(test_elements)
    for i in range(len(elements)):
        assert elements[i] == test_elements[i]


@pytest.mark.parametrize("filename", test_files)
def test_partition_json_from_text(filename: str):
    path = os.path.join(DIRECTORY, "..", "..", "example-docs", filename)
    elements = partition(filename=path)

    with tempfile.TemporaryDirectory() as tmpdir:
        test_path = os.path.join(tmpdir, filename + ".json")
        elements_to_json(elements, filename=test_path, indent=2)
        with open(test_path) as f:
            text = f.read()
        test_elements = partition_json(text=text)

    assert len(elements) > 0
    assert len(str(elements[0])) > 0

    assert len(elements) == len(test_elements)
    for i in range(len(elements)):
        assert elements[i] == test_elements[i]


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
