from unstructured_inference.inference.elements import TextRegion, TextRegions
from unstructured_inference.inference.layoutelement import LayoutElement

from unstructured.documents.elements import ElementType
from unstructured.partition.pdf_image.inference_utils import (
    build_layout_elements_from_ocr_regions,
    merge_text_regions,
)


def test_merge_text_regions(mock_embedded_text_regions):
    expected = TextRegion.from_coords(
        x1=437.83888888888885,
        y1=317.319341111111,
        x2=1256.334784222222,
        y2=406.9837855555556,
        text="LayoutParser: A Unified Toolkit for Deep Learning Based Document Image",
    )

    merged_text_region = merge_text_regions(TextRegions.from_list(mock_embedded_text_regions))
    assert merged_text_region == expected


def test_build_layout_elements_from_ocr_regions(mock_embedded_text_regions):
    expected = [
        LayoutElement.from_coords(
            x1=437.83888888888885,
            y1=317.319341111111,
            x2=1256.334784222222,
            y2=406.9837855555556,
            text="LayoutParser: A Unified Toolkit for Deep Learning Based Document Image",
            type=ElementType.UNCATEGORIZED_TEXT,
        ),
    ]

    elements = build_layout_elements_from_ocr_regions(mock_embedded_text_regions)
    assert elements == expected
