from __future__ import annotations

import io
import requests

import pytest

from unstructured.partition.code import partition_code

TEST_FILE_URLS = {
    "c": "https://raw.githubusercontent.com/tree-sitter/tree-sitter-c/master/examples/malloc.c",
    "go": "https://raw.githubusercontent.com/tree-sitter/tree-sitter-go/master/examples/proc.go",
    "python": "https://raw.githubusercontent.com/tree-sitter/tree-sitter-python/master/examples/python2-grammar-crlf.py",
    "cpp": "https://raw.githubusercontent.com/tree-sitter/tree-sitter-cpp/master/examples/rule.cc",
    "javascript": "https://raw.githubusercontent.com/tree-sitter/tree-sitter-javascript/master/examples/text-editor-component.js",
    "typescript": "https://raw.githubusercontent.com/tree-sitter/tree-sitter-typescript/master/examples/parser.ts",
    # Need to find some file for testing eventually
    # "c-sharp": ,
    # "php": ,
    # "ruby": ,
    # "swift":
}


@pytest.fixture(scope="module")
def test_files(tmp_path_factory):
    test_files = {}
    for language, file in TEST_FILE_URLS.items():
        text = requests.get(file).content.decode("utf-8")
        filename = file.split("/")[-1]
        fn = tmp_path_factory.mktemp("data") / filename
        fn.write_text(text)
        test_files[language] = fn

    return test_files


@pytest.mark.parametrize("language", TEST_FILE_URLS.keys())
@pytest.fixture(scope="function")
def test_partition_code_from_filename(language: str, test_files, tmp_path_factory):
    elements = partition_code(filename=test_files[language])
    assert len(elements) > 0
    for el in elements:
        assert el.metadata.languages == [language]

    result = tmp_path_factory.mktemp("data") / "partition_result"
    for el in elements:
        result.write_text(el.text)

    # Sanity check to see if we loose anything during partitioning
    assert test_files[language].read() == result.read()


@pytest.mark.parametrize("language", TEST_FILE_URLS.keys())
def test_partition_code_from_file(language: str, test_files):
    file = io.BytesIO(test_files[language].read_bytes())
    elements = partition_code(file=file)
    assert len(elements) > 0
    for el in elements:
        assert el.metadata.languages == [language]
    pass


@pytest.mark.parametrize("max_partition", [500, 1000, 2000])
@pytest.mark.parametrize("language", TEST_FILE_URLS.keys())
def test_partition_code_max_partition(max_partition: int, language: str, test_files):
    elements = partition_code(filename=test_files[language], max_partition=max_partition)
    assert len(elements) > 0
    for el in elements:
        assert len(el.text) <= max_partition + 50


@pytest.mark.parametrize("min_partition", [50, 100, 200])
@pytest.mark.parametrize("language", TEST_FILE_URLS.keys())
def test_partition_code_min_partition(min_partition: int, language: str, test_files):
    elements = partition_code(filename=test_files[language], min_partition=min_partition)
    assert len(elements) > 0

    # No enforcement is done on the last element
    for el in elements[:-1]:
        assert len(el.text) >= min_partition
