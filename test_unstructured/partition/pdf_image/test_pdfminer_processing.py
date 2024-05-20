import pytest
from PIL import Image
from unstructured_inference.constants import Source as InferenceSource
from unstructured_inference.inference.elements import Rectangle, TextRegion
from unstructured_inference.inference.layout import DocumentLayout, LayoutElement, PageLayout

from unstructured.partition.pdf_image.pdfminer_processing import (
    aggregate_embedded_text_by_block,
    clean_pdfminer_duplicate_image_elements,
    clean_pdfminer_inner_elements,
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
    page.elements = elements
    document_with_table = DocumentLayout(pages=[page])
    document = document_with_table

    # call the function to clean the pdfminer inner elements
    cleaned_doc = clean_pdfminer_inner_elements(document)

    # check that the pdfminer elements were stored in the extra_info dictionary
    assert len(cleaned_doc.pages[0].elements) == expected_document_length


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


@pytest.mark.parametrize(
    ("elements", "expected_document_length"),
    [
        (elements_with_duplicate_images, 2),
        (elements_without_duplicate_images, 4),
    ],
)
def test_clean_pdfminer_duplicate_image_elements(elements, expected_document_length):
    page = PageLayout(number=1, image=Image.new("1", (1, 1)))
    page.elements = elements
    document = DocumentLayout(pages=[page])

    cleaned_doc = clean_pdfminer_duplicate_image_elements(document)

    assert len(cleaned_doc.pages[0].elements) == expected_document_length


def test_aggregate_by_block():
    expected = "Inside region1 Inside region2"
    embedded_regions = [
        TextRegion.from_coords(0, 0, 20, 20, "Inside region1"),
        TextRegion.from_coords(50, 50, 150, 150, "Inside region2"),
        TextRegion.from_coords(250, 250, 350, 350, "Outside region"),
    ]
    target_region = TextRegion.from_coords(0, 0, 300, 300)

    text = aggregate_embedded_text_by_block(target_region, embedded_regions)
    assert text == expected
