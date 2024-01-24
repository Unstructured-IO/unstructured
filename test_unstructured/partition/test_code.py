from __future__ import annotations

import io
import pytest

from unstructured.partition.code import partition_code
from unstructured.partition.auto import partition
from unstructured.utils import get_homedir


TEST_FILE_PATH = {
    "c": get_homedir() + ".unstructured_treesitter/tree-sitter-c/examples/malloc.c",
    "go": get_homedir() + ".unstructured_treesitter/tree-sitter-go/examples/proc.go",
    "python": (
        get_homedir()
        + ".unstructured_treesitter/tree-sitter-python/examples/python2-grammar-crlf.py"
    ),
    "cpp": get_homedir() + ".unstructured_treesitter/tree-sitter-cpp/examples/rule.cc",
    "javascript": (
        get_homedir()
        + ".unstructured_treesitter/tree-sitter-javascript/examples/text-editor-component.js"
    ),
    "typescript": (
        get_homedir() + ".unstructured_treesitter/tree-sitter-typescript/examples/parser.ts"
    ),
    # Need to find some file for testing eventually
    # "c-sharp": ,
    # "php": ,
    # "ruby": ,
    # "swift":
}

LANGUAGE_TO_EXT = {
    "python": ".py",
    "javascript": ".js",
    "typescript": ".ts",
    "cpp": ".cpp",
    "c": ".c",
    "go": ".go",
}


@pytest.mark.parametrize("language", TEST_FILE_PATH.keys())
@pytest.fixture(scope="function")
def test_partition_code_from_filename(language: str, tmp_path_factory):
    elements = partition_code(filename=TEST_FILE_PATH[language])
    assert len(elements) > 0
    for el in elements:
        assert el.metadata.languages == [language]

    result = tmp_path_factory.mktemp("data") / "partition_result"
    for el in elements:
        result.write_text(el.text)

    # Sanity check to see if we loose anything during partitioning
    assert open(TEST_FILE_PATH[language], "r").read() == result.read()


@pytest.mark.parametrize("language", TEST_FILE_PATH.keys())
def test_partition_code_from_file(language: str):
    file = io.BytesIO(open(TEST_FILE_PATH[language], "rb").read())
    elements = partition_code(file=file, programming_language=language)
    assert len(elements) > 0
    for el in elements:
        assert el.metadata.languages == [language]
    pass


def test_programming_language_enforced():
    with pytest.raises(ValueError):
        partition_code(filename=TEST_FILE_PATH["python"], programming_language="go")


@pytest.mark.parametrize("language", TEST_FILE_PATH.keys())
def test_partition_auto_for_code(language: str):
    file = io.BytesIO(open(TEST_FILE_PATH[language], "rb").read())
    partition(
        file=file, programming_language=language, file_filename="test" + LANGUAGE_TO_EXT[language]
    )


@pytest.mark.parametrize("max_partition", [500, 1000, 2000])
@pytest.mark.parametrize("language", TEST_FILE_PATH.keys())
def test_partition_code_max_partition(max_partition: int, language: str):
    elements = partition_code(filename=TEST_FILE_PATH[language], max_partition=max_partition)
    assert len(elements) > 0
    for el in elements:
        # The minimum is enforced, so there is a maximum spillage of 200
        assert len(el.text) <= max_partition + 200


@pytest.mark.parametrize("min_partition", [50, 100, 200])
@pytest.mark.parametrize("language", TEST_FILE_PATH.keys())
def test_partition_code_min_partition(min_partition: int, language: str):
    elements = partition_code(filename=TEST_FILE_PATH[language], min_partition=min_partition)
    assert len(elements) > 0

    # No enforcement is done on the last element
    for el in elements[:-1]:
        assert len(el.text) >= min_partition
