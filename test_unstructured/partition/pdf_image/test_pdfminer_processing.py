from unittest.mock import patch

import numpy as np
import pytest
from pdfminer.layout import LAParams
from PIL import Image
from unstructured_inference.constants import Source as InferenceSource
from unstructured_inference.inference.elements import (
    EmbeddedTextRegion,
    Rectangle,
    TextRegion,
    TextRegions,
)
from unstructured_inference.inference.layout import DocumentLayout, LayoutElement, PageLayout
from unstructured_inference.inference.layoutelement import LayoutElements

from test_unstructured.unit_utils import example_doc_path
from unstructured.partition.auto import partition
from unstructured.partition.pdf_image.pdfminer_processing import (
    _validate_bbox,
    aggregate_embedded_text_by_block,
    bboxes1_is_almost_subregion_of_bboxes2,
    boxes_self_iou,
    clean_pdfminer_inner_elements,
    process_file_with_pdfminer,
    remove_duplicate_elements,
)
from unstructured.partition.utils.constants import Source

# A set of elements with pdfminer elements inside tables
deletable_elements_inside_table = [
    LayoutElement(
        bbox=Rectangle(0, 0, 100, 100),
        text="Table with inner elements",
        type="Table",
    ),
    LayoutElement(bbox=Rectangle(50, 50, 70, 70), text="text1", source=Source.PDFMINER),
    LayoutElement(bbox=Rectangle(70, 70, 80, 80), text="text2", source=Source.PDFMINER),
]

# A set of elements without pdfminer elements inside
# tables (no elements with source=Source.PDFMINER)
no_deletable_elements_inside_table = [
    LayoutElement(
        bbox=Rectangle(0, 0, 100, 100),
        text="Table with inner elements",
        type="Table",
        source=InferenceSource.YOLOX,
    ),
    LayoutElement(bbox=Rectangle(50, 50, 70, 70), text="text1", source=InferenceSource.YOLOX),
    LayoutElement(bbox=Rectangle(70, 70, 80, 80), text="text2", source=InferenceSource.YOLOX),
]
# A set of elements with pdfminer elements inside tables and other
# elements with source=Source.PDFMINER
# Note: there is some elements with source=Source.PDFMINER are not inside tables
mix_elements_inside_table = [
    LayoutElement(
        bbox=Rectangle(0, 0, 100, 100),
        text="Table1 with inner elements",
        type="Table",
        source=InferenceSource.YOLOX,
    ),
    LayoutElement(bbox=Rectangle(50, 50, 70, 70), text="Inside table1"),
    LayoutElement(bbox=Rectangle(70, 70, 80, 80), text="Inside table1", source=Source.PDFMINER),
    LayoutElement(
        bbox=Rectangle(150, 150, 170, 170),
        text="Outside tables",
        source=Source.PDFMINER,
    ),
    LayoutElement(
        bbox=Rectangle(180, 180, 200, 200),
        text="Outside tables",
        source=Source.PDFMINER,
    ),
    LayoutElement(
        bbox=Rectangle(0, 500, 100, 700),
        text="Table2 with inner elements",
        type="Table",
        source=InferenceSource.YOLOX,
    ),
    LayoutElement(bbox=Rectangle(0, 510, 50, 600), text="Inside table2", source=Source.PDFMINER),
    LayoutElement(bbox=Rectangle(0, 550, 70, 650), text="Inside table2", source=Source.PDFMINER),
]


@pytest.mark.parametrize(
    ("bbox", "is_valid"),
    [
        ([0, 1, 0, 1], False),
        ([0, 1, 1, 2], True),
        ([0, 1, 1, None], False),
        ([0, 1, 1, np.nan], False),
        ([0, 1, -1, 0], False),
        ([0, 1, -1, 2], False),
    ],
)
def test_valid_bbox(bbox, is_valid):
    assert _validate_bbox(bbox) is is_valid


@pytest.mark.parametrize(
    ("elements", "length_extra_info", "expected_document_length"),
    [
        (deletable_elements_inside_table, 1, 1),
        (no_deletable_elements_inside_table, 0, 3),
        (mix_elements_inside_table, 2, 5),
    ],
)
def test_clean_pdfminer_inner_elements(elements, length_extra_info, expected_document_length):
    # create a sample document with pdfminer elements inside tables
    page = PageLayout(number=1, image=Image.new("1", (1, 1)))
    page.elements_array = LayoutElements.from_list(elements)
    document_with_table = DocumentLayout(pages=[page])
    document = document_with_table

    # call the function to clean the pdfminer inner elements
    cleaned_doc = clean_pdfminer_inner_elements(document)

    # check that the pdfminer elements were stored in the extra_info dictionary
    assert len(cleaned_doc.pages[0].elements_array) == expected_document_length


elements_with_duplicate_images = [
    LayoutElement(
        bbox=Rectangle(0, 0, 100, 100),
        text="Image1",
        type="Image",
        source=Source.PDFMINER,
    ),
    LayoutElement(
        bbox=Rectangle(10, 10, 110, 110), text="Image1", type="Image", source=Source.PDFMINER
    ),
    LayoutElement(bbox=Rectangle(150, 150, 170, 170), text="Title1", type="Title"),
]

elements_without_duplicate_images = [
    LayoutElement(
        bbox=Rectangle(0, 0, 100, 100),
        text="Sample image",
        type="Image",
        source=Source.PDFMINER,
    ),
    LayoutElement(
        bbox=Rectangle(10, 10, 110, 110),
        text="Sample image with similar bbox",
        type="Image",
        source=Source.PDFMINER,
    ),
    LayoutElement(
        bbox=Rectangle(200, 200, 250, 250),
        text="Sample image",
        type="Image",
        source=Source.PDFMINER,
    ),
    LayoutElement(bbox=Rectangle(150, 150, 170, 170), text="Title1", type="Title"),
]


def test_aggregate_by_block():
    expected = "Inside region1 Inside region2"
    embedded_regions = TextRegions.from_list(
        [
            TextRegion.from_coords(0, 0, 20, 20, "Inside region1"),
            TextRegion.from_coords(20, 20, 80, 80, None),
            TextRegion.from_coords(50, 50, 150, 150, "Inside region2"),
            TextRegion.from_coords(250, 250, 350, 350, "Outside region"),
        ]
    )
    target_region = TextRegions.from_list([TextRegion.from_coords(0, 0, 300, 300)])

    text = aggregate_embedded_text_by_block(target_region, embedded_regions)
    assert text == expected


@pytest.mark.parametrize(
    ("coords1", "coords2", "expected"),
    [
        (
            [[0, 0, 10, 10], [10, 0, 20, 10], [10, 10, 20, 20]],
            [[0, 0, 10, 10], [0, 0, 12, 12]],
            [[True, True], [False, False], [False, False]],
        ),
        (
            [[0, 0, 10, 10], [10, 0, 20, 10], [10, 10, 20, 20]],
            [[0, 0, 10, 10], [10, 10, 22, 22], [0, 0, 5, 5]],
            [[True, False, False], [False, False, False], [False, True, False]],
        ),
        (
            [[0, 0, 10, 10], [10, 10, 10, 10]],
            [[0, 0, 10, 10], [10, 10, 22, 22], [0, 0, 5, 5]],
            [[True, False, False], [True, True, False]],
        ),
    ],
)
def test_bboxes1_is_almost_subregion_of_bboxes2(coords1, coords2, expected):
    bboxes1 = [Rectangle(*row) for row in coords1]
    bboxes2 = [Rectangle(*row) for row in coords2]
    np.testing.assert_array_equal(
        bboxes1_is_almost_subregion_of_bboxes2(bboxes1, bboxes2), expected
    )


@pytest.mark.parametrize(
    ("coords", "threshold", "expected"),
    [
        (
            [[0, 0, 10, 10], [2, 2, 12, 12], [10, 10, 20, 20]],
            0.5,
            [[True, True, False], [True, True, False], [False, False, True]],
        ),
        (
            [[0, 0, 10, 10], [2, 2, 12, 12], [10, 10, 20, 20]],
            0.9,
            [[True, False, False], [False, True, False], [False, False, True]],
        ),
        (
            [[0, 0, 10, 10], [10, 10, 10, 10]],
            0.5,
            [[True, False], [False, True]],
        ),
    ],
)
def test_boxes_self_iou(coords, threshold, expected):
    bboxes = [Rectangle(*row) for row in coords]
    np.testing.assert_array_equal(boxes_self_iou(bboxes, threshold), expected)


def test_remove_duplicate_elements():
    sample_elements = TextRegions.from_list(
        [
            EmbeddedTextRegion(bbox=Rectangle(0, 0, 10, 10), text="Text 1"),
            EmbeddedTextRegion(bbox=Rectangle(0, 0, 10, 10), text="Text 2"),
            EmbeddedTextRegion(bbox=Rectangle(20, 20, 30, 30), text="Text 3"),
        ]
    )

    result = remove_duplicate_elements(sample_elements)

    # Check that duplicates were removed and only 2 unique elements remain
    assert len(result) == 2
    assert result.texts.tolist() == ["Text 2", "Text 3"]
    assert result.element_coords.tolist() == [[0, 0, 10, 10], [20, 20, 30, 30]]


def test_process_file_with_pdfminer():
    layout, links = process_file_with_pdfminer(example_doc_path("pdf/layout-parser-paper-fast.pdf"))
    assert len(layout)
    assert "LayoutParser: A Uniﬁed Toolkit for Deep\n" in layout[0].texts
    assert links[0][0]["url"] == "https://layout-parser.github.io"


@patch("unstructured.partition.pdf_image.pdfminer_utils.LAParams", return_value=LAParams())
def test_laprams_are_passed_from_partition_to_pdfminer(pdfminer_mock):
    partition(
        filename=example_doc_path("pdf/layout-parser-paper-fast.pdf"),
        pdfminer_line_margin=1.123,
        pdfminer_char_margin=None,
        pdfminer_line_overlap=0.0123,
        pdfminer_word_margin=3.21,
    )
    assert pdfminer_mock.call_args.kwargs == {
        "line_margin": 1.123,
        "line_overlap": 0.0123,
        "word_margin": 3.21,
    }
