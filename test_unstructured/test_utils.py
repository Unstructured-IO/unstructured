import json
import os

import pytest

from unstructured import utils


@pytest.fixture()
def input_data():
    return [
        {"text": "This is a sentence."},
        {"text": "This is another sentence.", "meta": {"score": 0.1}},
    ]


@pytest.fixture()
def output_jsonl_file(tmp_path):
    return os.path.join(tmp_path, "output.jsonl")


@pytest.fixture()
def input_jsonl_file(tmp_path, input_data):
    file_path = os.path.join(tmp_path, "input.jsonl")
    with open(file_path, "w+") as input_file:
        input_file.writelines([json.dumps(obj) + "\n" for obj in input_data])
    return file_path


def test_save_as_jsonl(input_data, output_jsonl_file):
    utils.save_as_jsonl(input_data, output_jsonl_file)
    with open(output_jsonl_file) as output_file:
        file_data = [json.loads(line) for line in output_file]
    assert file_data == input_data


def test_read_as_jsonl(input_jsonl_file, input_data):
    file_data = utils.read_from_jsonl(input_jsonl_file)
    assert file_data == input_data


def test_requires_dependencies_decorator():
    @utils.requires_dependencies(dependencies="numpy")
    def test_func():
        import numpy  # noqa: F401

    test_func()


def test_requires_dependencies_decorator_multiple():
    @utils.requires_dependencies(dependencies=["numpy", "pandas"])
    def test_func():
        import numpy  # noqa: F401
        import pandas  # noqa: F401

    test_func()


def test_requires_dependencies_decorator_import_error():
    @utils.requires_dependencies(dependencies="not_a_package")
    def test_func():
        import not_a_package  # noqa: F401

    with pytest.raises(ImportError):
        test_func()


def test_requires_dependencies_decorator_import_error_multiple():
    @utils.requires_dependencies(dependencies=["not_a_package", "numpy"])
    def test_func():
        import not_a_package  # noqa: F401
        import numpy  # noqa: F401

    with pytest.raises(ImportError):
        test_func()


def test_requires_dependencies_decorator_in_class():
    @utils.requires_dependencies(dependencies="numpy")
    class TestClass:
        def __init__(self):
            import numpy  # noqa: F401

    TestClass()


@pytest.mark.parametrize("iterator", [[0, 1], (0, 1), range(10), [0], (0,), range(1)])
def test_first_gives_first(iterator):
    assert utils.first(iterator) == 0


@pytest.mark.parametrize("iterator", [[], ()])
def test_first_raises_if_empty(iterator):
    with pytest.raises(ValueError):
        utils.first(iterator)


@pytest.mark.parametrize("iterator", [[0], (0,), range(1)])
def test_only_gives_only(iterator):
    assert utils.first(iterator) == 0


@pytest.mark.parametrize("iterator", [[0, 1], (0, 1), range(10)])
def test_only_raises_when_len_more_than_1(iterator):
    with pytest.raises(ValueError):
        utils.only(iterator) == 0


@pytest.mark.parametrize("iterator", [[], ()])
def test_only_raises_if_empty(iterator):
    with pytest.raises(ValueError):
        utils.only(iterator)
