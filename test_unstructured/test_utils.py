import json
import os

import pytest

from unstructured import utils
from unstructured.documents.coordinates import PixelSpace
from unstructured.documents.elements import ElementMetadata, NarrativeText, Title


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
    ("elements", "nested_error_tolerance_px", "sm_overlap_threshold", "expectation"),
    [
        (
            [
                Title(
                    text="Some lovely title",
                    coordinates=((4, 5), (4, 8), (7, 8), (7, 5)),
                    coordinate_system=PixelSpace(width=20, height=20),
                    metadata=ElementMetadata(page_number=1),
                ),
                NarrativeText(
                    text="Some lovely text",
                    coordinates=((2, 3), (2, 6), (5, 6), (5, 3)),
                    coordinate_system=PixelSpace(width=20, height=20),
                    metadata=ElementMetadata(page_number=1),
                ),
            ],
            5,
            10.0,
            (
                True,
                [
                    {
                        "overlapping_elements": ["Title(ix=0)", "NarrativeText(ix=1)"],
                        "overlapping_case": "nested NarrativeText in Title",
                        "overlap_percentage": "100%",
                        "metadata": {
                            "largest_ngram_percentage": None,
                            "overlap_percentage_total": "5.88%",
                            "max_area": "9pxˆ2",
                            "min_area": "9pxˆ2",
                            "total_area": "18pxˆ2",
                        },
                    },
                ],
            ),
        ),
        (
            [
                Title(
                    text="Some lovely title",
                    coordinates=((4, 5), (4, 8), (7, 8), (7, 5)),
                    coordinate_system=PixelSpace(width=20, height=20),
                    metadata=ElementMetadata(page_number=1),
                ),
                NarrativeText(
                    text="Some lovely text",
                    coordinates=((2, 3), (2, 6), (5, 6), (5, 3)),
                    coordinate_system=PixelSpace(width=20, height=20),
                    metadata=ElementMetadata(page_number=1),
                ),
            ],
            1,
            10.0,
            (
                True,
                [
                    {
                        "overlapping_elements": ["0. Title(ix=0)", "1. NarrativeText(ix=1)"],
                        "overlapping_case": "partial overlap sharing 50.0% of the text from1. "
                        "NarrativeText(2-gram)",
                        "overlap_percentage": "11.11%",
                        "metadata": {
                            "largest_ngram_percentage": 50.0,
                            "overlap_percentage_total": "5.88%",
                            "max_area": "9pxˆ2",
                            "min_area": "9pxˆ2",
                            "total_area": "18pxˆ2",
                        },
                    },
                ],
            ),
        ),
        (
            [
                Title(
                    text="Some lovely title",
                    coordinates=((4, 5), (4, 8), (7, 8), (7, 5)),
                    coordinate_system=PixelSpace(width=20, height=20),
                    metadata=ElementMetadata(page_number=1),
                ),
                NarrativeText(
                    text="Some lovely title",
                    coordinates=((2, 3), (2, 6), (5, 6), (5, 3)),
                    coordinate_system=PixelSpace(width=20, height=20),
                    metadata=ElementMetadata(page_number=1),
                ),
            ],
            1,
            10.0,
            (
                True,
                [
                    {
                        "overlapping_elements": ["0. Title(ix=0)", "1. NarrativeText(ix=1)"],
                        "overlapping_case": "partial overlap with duplicate text",
                        "overlap_percentage": "11.11%",
                        "metadata": {
                            "largest_ngram_percentage": None,
                            "overlap_percentage_total": "5.88%",
                            "max_area": "9pxˆ2",
                            "min_area": "9pxˆ2",
                            "total_area": "18pxˆ2",
                        },
                    },
                ],
            ),
        ),
        (
            [
                Title(
                    text="Some lovely title",
                    coordinates=((4, 5), (4, 8), (7, 8), (7, 5)),
                    coordinate_system=PixelSpace(width=20, height=20),
                    metadata=ElementMetadata(page_number=1),
                ),
                NarrativeText(
                    text="Something totally different here",
                    coordinates=((2, 3), (2, 6), (5, 6), (5, 3)),
                    coordinate_system=PixelSpace(width=20, height=20),
                    metadata=ElementMetadata(page_number=1),
                ),
            ],
            1,
            10.0,
            (
                True,
                [
                    {
                        "overlapping_elements": ["0. Title(ix=0)", "1. NarrativeText(ix=1)"],
                        "overlapping_case": "partial overlap without sharing text",
                        "overlap_percentage": "11.11%",
                        "metadata": {
                            "largest_ngram_percentage": 0,
                            "overlap_percentage_total": "5.88%",
                            "max_area": "9pxˆ2",
                            "min_area": "9pxˆ2",
                            "total_area": "18pxˆ2",
                        },
                    },
                ],
            ),
        ),
        (
            [
                Title(
                    text="Some lovely title",
                    coordinates=((5, 6), (5, 10), (8, 10), (8, 6)),
                    coordinate_system=PixelSpace(width=20, height=20),
                    metadata=ElementMetadata(page_number=1),
                ),
                NarrativeText(
                    text="Some lovely text",
                    coordinates=((1, 3), (2, 7), (6, 7), (5, 3)),
                    coordinate_system=PixelSpace(width=20, height=20),
                    metadata=ElementMetadata(page_number=1),
                ),
            ],
            1,
            10.0,
            (
                True,
                [
                    {
                        "overlapping_elements": ["0. Title(ix=0)", "1. NarrativeText(ix=1)"],
                        "overlapping_case": "Small partial overlap",
                        "overlap_percentage": "8.33%",
                        "metadata": {
                            "largest_ngram_percentage": None,
                            "overlap_percentage_total": "3.23%",
                            "max_area": "20pxˆ2",
                            "min_area": "12pxˆ2",
                            "total_area": "32pxˆ2",
                        },
                    },
                ],
            ),
        ),
        (
            [
                Title(
                    text="Some lovely title",
                    coordinates=((4, 6), (4, 7), (7, 7), (7, 6)),
                    coordinate_system=PixelSpace(width=20, height=20),
                    metadata=ElementMetadata(page_number=1),
                ),
                NarrativeText(
                    text="Some lovely text",
                    coordinates=((6, 8), (6, 9), (9, 9), (9, 8)),
                    coordinate_system=PixelSpace(width=20, height=20),
                    metadata=ElementMetadata(page_number=1),
                ),
            ],
            1,
            10.0,
            (False, []),
        ),
    ],
)
def test_catch_overlapping_and_nested_bboxes(
    elements,
    expectation,
    nested_error_tolerance_px,
    sm_overlap_threshold,
):
    overlapping_flag, overlapping_cases = utils.catch_overlapping_and_nested_bboxes(
        elements,
        nested_error_tolerance_px,
        sm_overlap_threshold,
    )
    assert overlapping_flag == expectation[0]
    assert overlapping_cases == expectation[1]
