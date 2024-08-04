from unstructured_inference.inference.elements import ImageTextRegion, TextRegion
from unstructured_inference.inference.layoutelement import LayoutElement

from unstructured.documents.elements import ElementType
from unstructured.partition.pdf_image.inference_utils import (
    build_layout_elements_from_ocr_regions,
    merge_embedded_overlapping_regions,
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

    merged_text_region = merge_text_regions(mock_embedded_text_regions)
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


def test_merge_embedded_overlapping_regions():
    # Create some test regions
    region1 = TextRegion.from_coords(10, 10, 30, 30, "Hello")
    region2 = TextRegion.from_coords(15, 15, 25, 25, " World")
    region3 = TextRegion.from_coords(50, 50, 80, 80, "Not overlapping")
    image_region = ImageTextRegion.from_coords(90, 90, 100, 100)
    expected_merged_region = TextRegion.from_coords(10, 10, 30, 30, "Hello World")

    # Test merging
    regions = [region1, region2, region3, image_region]
    merged_regions = merge_embedded_overlapping_regions(regions)

    assert len(merged_regions) == 3
    # Check the merged region
    assert merged_regions[0] == expected_merged_region
    # Check the non-overlapping region
    assert merged_regions[1] == region3


def test_merge_embedded_overlapping_regions_no_overlap():
    region1 = TextRegion.from_coords(10, 10, 20, 20, "Text 1")
    region2 = TextRegion.from_coords(30, 30, 40, 40, "Text 2")

    regions = [region1, region2]
    merged_regions = merge_embedded_overlapping_regions(regions)

    assert len(merged_regions) == 2
    assert merged_regions[0].text == "Text 1"
    assert merged_regions[1].text == "Text 2"


def test_merge_embedded_overlapping_regions_image_text_region_handling():
    regions = [
        ImageTextRegion.from_coords(0, 0, 10, 10, "Image A"),
        ImageTextRegion.from_coords(20, 20, 30, 30, "Image B"),
    ]
    merged = merge_embedded_overlapping_regions(regions)
    assert len(merged) == 2
    assert isinstance(merged[0], ImageTextRegion)
    assert isinstance(merged[1], ImageTextRegion)
