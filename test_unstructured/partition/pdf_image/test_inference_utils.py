from unstructured_inference.inference.elements import TextRegion, TextRegions
from unstructured_inference.inference.layoutelement import LayoutElement, LayoutElements

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
    expected = LayoutElements.from_list(
        [
            LayoutElement.from_coords(
                x1=437.83888888888885,
                y1=317.319341111111,
                x2=1256.334784222222,
                y2=406.9837855555556,
                text="LayoutParser: A Unified Toolkit for Deep Learning Based Document Image",
                type=ElementType.UNCATEGORIZED_TEXT,
            ),
        ]
    )

    elements = build_layout_elements_from_ocr_regions(
        TextRegions.from_list(mock_embedded_text_regions)
    )
    assert elements == expected


def test_build_layout_elements_from_ocr_regions_with_text(mock_embedded_text_regions):
    text = "LayoutParser: A Unified Toolkit for Deep Learning Based Document Image"
    expected = LayoutElements.from_list(
        [
            LayoutElement.from_coords(
                x1=437.83888888888885,
                y1=317.319341111111,
                x2=1256.334784222222,
                y2=406.9837855555556,
                text=text,
                type=ElementType.UNCATEGORIZED_TEXT,
            ),
        ]
    )

    elements = build_layout_elements_from_ocr_regions(
        TextRegions.from_list(mock_embedded_text_regions),
        text,
        group_by_ocr_text=True,
    )
    assert elements == expected


def test_build_layout_elements_from_ocr_regions_with_multi_line_text(mock_embedded_text_regions):
    text = "LayoutParser: \n\nA Unified Toolkit for Deep Learning Based Document Image"
    elements = build_layout_elements_from_ocr_regions(
        TextRegions.from_list(mock_embedded_text_regions),
        text,
        group_by_ocr_text=True,
    )
    assert elements == LayoutElements.from_list(
        [
            LayoutElement.from_coords(
                x1=453.00277777777774,
                y1=317.319341111111,
                x2=711.5338541666665,
                y2=358.28571222222206,
                text="LayoutParser:",
                type=ElementType.UNCATEGORIZED_TEXT,
            ),
            LayoutElement.from_coords(
                x1=437.83888888888885,
                y1=317.319341111111,
                x2=1256.334784222222,
                y2=406.9837855555556,
                text="A Unified Toolkit for Deep Learning Based Document Image",
                type=ElementType.UNCATEGORIZED_TEXT,
            ),
        ]
    )


def test_build_layout_elements_from_ocr_regions_with_repeated_texts(mock_embedded_text_regions):
    mock_embedded_text_regions.extend(
        [
            LayoutElement.from_coords(
                x1=453.00277777777774,
                y1=417.319341111111,
                x2=711.5338541666665,
                y2=458.28571222222206,
                text="LayoutParser",
                type=ElementType.UNCATEGORIZED_TEXT,
            ),
            LayoutElement.from_coords(
                x1=453.00277777777774,
                y1=468.319341111111,
                x2=711.5338541666665,
                y2=478.28571222222206,
                text="for",
                type=ElementType.UNCATEGORIZED_TEXT,
            ),
            LayoutElement.from_coords(
                x1=453.00277777777774,
                y1=488.319341111111,
                x2=711.5338541666665,
                y2=500.28571222222206,
                text="Deep",
                type=ElementType.UNCATEGORIZED_TEXT,
            ),
            LayoutElement.from_coords(
                x1=453.00277777777774,
                y1=510.319341111111,
                x2=711.5338541666665,
                y2=550.28571222222206,
                text="Learning",
                type=ElementType.UNCATEGORIZED_TEXT,
            ),
        ]
    )
    text = (
        "LayoutParser: \n\nA Unified Toolkit for Deep Learning Based Document Image\n\n"
        "LayoutParser for Deep Learning"
    )
    elements = build_layout_elements_from_ocr_regions(
        TextRegions.from_list(mock_embedded_text_regions),
        text,
        group_by_ocr_text=True,
    )
    assert elements == LayoutElements.from_list(
        [
            LayoutElement.from_coords(
                x1=453.00277777777774,
                y1=317.319341111111,
                x2=711.5338541666665,
                y2=358.28571222222206,
                text="LayoutParser:",
                type=ElementType.UNCATEGORIZED_TEXT,
            ),
            LayoutElement.from_coords(
                x1=437.83888888888885,
                y1=317.319341111111,
                x2=1256.334784222222,
                y2=406.9837855555556,
                text="A Unified Toolkit for Deep Learning Based Document Image",
                type=ElementType.UNCATEGORIZED_TEXT,
            ),
            LayoutElement.from_coords(
                x1=453.00277777777774,
                y1=417.319341111111,
                x2=711.5338541666665,
                y2=550.28571222222206,
                text="LayoutParser for Deep Learning",
                type=ElementType.UNCATEGORIZED_TEXT,
            ),
        ]
    )
