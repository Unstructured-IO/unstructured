import json
import os

import pytest

from unstructured import utils
from unstructured.documents.elements import NarrativeText, Title, ElementMetadata
from unstructured.documents.coordinates import PixelSpace
from contextlib import nullcontext as does_not_raise


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


@pytest.mark.parametrize(
    "filename, file, elements, expectation",
    [
        ("example-docs/layout-parser-paper-fast.jpg", None,
         [
             Title(
                 text="Some lovely title",
                 coordinates=((4, 5), (4, 8), (7, 8), (7, 5)),
                 coordinate_system=PixelSpace(width=10, height=20),
                 metadata=ElementMetadata(page_number=1)
             ),
             NarrativeText(
                 text="Some lovely text",
                 coordinates=((2, 3), (2, 6), (5, 6), (5, 3)),
                 coordinate_system=PixelSpace(width=10, height=20),
                 metadata=ElementMetadata(page_number=1)
             )
         ],
         does_not_raise()),
        ("example-docs/loremipsum-flat.pdf", None,
         [
             Title(
                 text="Some lovely title",
                 coordinates=((4, 5), (4, 8), (7, 8), (7, 5)),
                 coordinate_system=PixelSpace(width=10, height=20),
                 metadata=ElementMetadata(page_number=1)
             ),
             NarrativeText(
                 text="Some lovely text",
                 coordinates=((2, 3), (2, 6), (5, 6), (5, 3)),
                 coordinate_system=PixelSpace(width=10, height=20),
                 metadata=ElementMetadata(page_number=1)
             )
         ],
         does_not_raise())
    ]
)
def test_draw_bboxes_on_pdf_or_image(filename, file, elements, expectation):
    with expectation:
        utils.draw_bboxes_on_pdf_or_image(
            filename,
            elements,
            save_images=False,
            save_coordinates=False,
            output_folder=None,
            plot=False
        )
