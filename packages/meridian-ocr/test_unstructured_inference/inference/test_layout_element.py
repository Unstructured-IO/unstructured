from unstructured_inference.constants import IsExtracted, Source
from unstructured_inference.inference.layoutelement import LayoutElement, TextRegion


def test_layout_element_to_dict(mock_layout_element):
    expected = {
        "coordinates": ((100, 100), (100, 300), (300, 300), (300, 100)),
        "text": "Sample text",
        "is_extracted": None,
        "type": "Text",
        "prob": None,
        "source": None,
    }

    assert mock_layout_element.to_dict() == expected


def test_layout_element_from_region(mock_rectangle):
    expected = LayoutElement.from_coords(100, 100, 300, 300)
    region = TextRegion(bbox=mock_rectangle)

    assert LayoutElement.from_region(region) == expected


def test_layoutelement_inheritance_works_correctly():
    """Test that LayoutElement properly inherits from TextRegion without conflicts"""
    from unstructured_inference.inference.elements import TextRegion

    # Create a TextRegion with both source and text_source
    region = TextRegion.from_coords(
        0, 0, 10, 10, text="test", source=Source.YOLOX, is_extracted=IsExtracted.TRUE
    )

    # Convert to LayoutElement
    element = LayoutElement.from_region(region)

    # Check that both properties are preserved
    assert element.source == Source.YOLOX, "LayoutElement should inherit source from TextRegion"
    assert element.is_extracted == IsExtracted.TRUE, (
        "LayoutElement should inherit is_extracted from TextRegion"
    )

    # Check that to_dict() works correctly
    d = element.to_dict()
    assert d["source"] == Source.YOLOX
    assert d["is_extracted"] == IsExtracted.TRUE

    # Check that we can set source directly on LayoutElement
    element.source = Source.DETECTRON2_ONNX
    assert element.source == Source.DETECTRON2_ONNX
