import pytest
from unstructured_inference.inference.elements import EmbeddedTextRegion, TextRegion
from unstructured_inference.inference.layoutelement import (
    LayoutElement,
)

from unstructured.partition import ocr


@pytest.fixture()
def mock_ocr_regions():
    return [
        EmbeddedTextRegion(10, 10, 90, 90, text="0", source=None),
        EmbeddedTextRegion(200, 200, 300, 300, text="1", source=None),
        EmbeddedTextRegion(500, 320, 600, 350, text="3", source=None),
    ]


@pytest.fixture()
def mock_inferred_layout(mock_embedded_text_regions):
    return [
        LayoutElement(
            r.x1,
            r.y1,
            r.x2,
            r.y2,
            text=None,
            source=None,
            type="Text",
        )
        for r in mock_embedded_text_regions
    ]


def test_aggregate_ocr_text_by_block():
    expected = "A Unified Toolkit"
    ocr_layout = [
        TextRegion(0, 0, 20, 20, "A"),
        TextRegion(50, 50, 150, 150, "Unified"),
        TextRegion(150, 150, 300, 250, "Toolkit"),
        TextRegion(200, 250, 300, 350, "Deep"),
    ]
    region = TextRegion(0, 0, 250, 350, "")

    text = ocr.aggregate_ocr_text_by_block(ocr_layout, region, 0.5)
    assert text == expected


def test_merge_text_regions(mock_embedded_text_regions):
    expected = TextRegion(
        x1=437.83888888888885,
        y1=317.319341111111,
        x2=1256.334784222222,
        y2=406.9837855555556,
        text="LayoutParser: A Unified Toolkit for Deep Learning Based Document Image",
    )

    merged_text_region = ocr.merge_text_regions(mock_embedded_text_regions)
    assert merged_text_region == expected


def test_get_elements_from_ocr_regions(mock_embedded_text_regions):
    expected = [
        LayoutElement(
            x1=437.83888888888885,
            y1=317.319341111111,
            x2=1256.334784222222,
            y2=406.9837855555556,
            text="LayoutParser: A Unified Toolkit for Deep Learning Based Document Image",
            type="UncategorizedText",
        ),
    ]

    elements = ocr.get_elements_from_ocr_regions(mock_embedded_text_regions)
    assert elements == expected


@pytest.fixture()
def mock_layout(mock_embedded_text_regions):
    return [
        LayoutElement(
            r.x1,
            r.y1,
            r.x2,
            r.y2,
            text=r.text,
            type="UncategorizedText",
        )
        for r in mock_embedded_text_regions
    ]


@pytest.fixture()
def mock_embedded_text_regions():
    return [
        EmbeddedTextRegion(
            x1=453.00277777777774,
            y1=317.319341111111,
            x2=711.5338541666665,
            y2=358.28571222222206,
            text="LayoutParser:",
        ),
        EmbeddedTextRegion(
            x1=726.4778125,
            y1=317.319341111111,
            x2=760.3308594444444,
            y2=357.1698966666667,
            text="A",
        ),
        EmbeddedTextRegion(
            x1=775.2748177777777,
            y1=317.319341111111,
            x2=917.3579885555555,
            y2=357.1698966666667,
            text="Unified",
        ),
        EmbeddedTextRegion(
            x1=932.3019468888888,
            y1=317.319341111111,
            x2=1071.8426522222221,
            y2=357.1698966666667,
            text="Toolkit",
        ),
        EmbeddedTextRegion(
            x1=1086.7866105555556,
            y1=317.319341111111,
            x2=1141.2105142777777,
            y2=357.1698966666667,
            text="for",
        ),
        EmbeddedTextRegion(
            x1=1156.154472611111,
            y1=317.319341111111,
            x2=1256.334784222222,
            y2=357.1698966666667,
            text="Deep",
        ),
        EmbeddedTextRegion(
            x1=437.83888888888885,
            y1=367.13322999999986,
            x2=610.0171992222222,
            y2=406.9837855555556,
            text="Learning",
        ),
        EmbeddedTextRegion(
            x1=624.9611575555555,
            y1=367.13322999999986,
            x2=741.6754646666665,
            y2=406.9837855555556,
            text="Based",
        ),
        EmbeddedTextRegion(
            x1=756.619423,
            y1=367.13322999999986,
            x2=958.3867708333332,
            y2=406.9837855555556,
            text="Document",
        ),
        EmbeddedTextRegion(
            x1=973.3307291666665,
            y1=367.13322999999986,
            x2=1092.0535042777776,
            y2=406.9837855555556,
            text="Image",
        ),
    ]


def test_supplement_layout_with_ocr_elements(mock_layout, mock_ocr_regions):
    ocr_elements = [
        LayoutElement(
            r.x1,
            r.y1,
            r.x2,
            r.y2,
            text=r.text,
            source=None,
            type="UncategorizedText",
        )
        for r in mock_ocr_regions
    ]

    final_layout = ocr.supplement_layout_with_ocr_elements(mock_layout, mock_ocr_regions)

    # Check if the final layout contains the original layout elements
    for element in mock_layout:
        assert element in final_layout

    # Check if the final layout contains the OCR-derived elements
    assert any(ocr_element in final_layout for ocr_element in ocr_elements)

    # Check if the OCR-derived elements that are subregions of layout elements are removed
    for element in mock_layout:
        for ocr_element in ocr_elements:
            if ocr_element.is_almost_subregion_of(element, ocr.SUBREGION_THRESHOLD_FOR_OCR):
                assert ocr_element not in final_layout


def test_merge_inferred_layout_with_ocr_layout(mock_inferred_layout, mock_ocr_regions):
    ocr_elements = [
        LayoutElement(
            r.x1,
            r.y1,
            r.x2,
            r.y2,
            text=r.text,
            source=None,
            type="UncategorizedText",
        )
        for r in mock_ocr_regions
    ]

    final_layout = ocr.merge_inferred_layout_with_ocr_layout(mock_inferred_layout, mock_ocr_regions)

    # Check if the inferred layout's text attribute is updated with aggregated OCR text
    assert final_layout[0].text == mock_ocr_regions[2].text

    # Check if the final layout contains both original elements and OCR-derived elements
    assert all(element in final_layout for element in mock_inferred_layout)
    assert any(element in final_layout for element in ocr_elements)
