from io import BytesIO
from unittest.mock import Mock

import pytest
from google.cloud.vision import AnnotateImageResponse, TextAnnotation
from PIL import Image

from unstructured.partition.utils.ocr_models.google_vision_ocr import OCRAgentGoogleVision


@pytest.mark.parametrize(
    "method",
    ["get_text_from_image", "get_layout_from_image", "get_layout_elements_from_image"],
)
@pytest.mark.parametrize(
    ("mode", "color"),
    [
        ("CMYK", (0, 255, 255, 0)),
        ("RGBX", (12, 34, 56, 255)),
        ("YCbCr", (120, 90, 160)),
        ("HSV", (90, 200, 210)),
    ],
)
def test_non_png_color_modes_are_converted_without_mutating_the_callers_image(method, mode, color):
    image = Image.new(mode, (3, 2), color)
    original = image.tobytes()
    agent = object.__new__(OCRAgentGoogleVision)
    agent.language = "en"
    agent.client = Mock()
    agent.client.document_text_detection.return_value = AnnotateImageResponse(
        full_text_annotation=TextAnnotation(text="recognized")
    )

    getattr(agent, method)(image)

    for call in agent.client.document_text_detection.call_args_list:
        with Image.open(BytesIO(call.kwargs["image"].content)) as encoded:
            assert encoded.format == "PNG"
            assert encoded.mode == "RGB"
            assert encoded.size == image.size
            assert encoded.tobytes() == image.convert("RGB").tobytes()
        assert list(call.kwargs["image_context"].language_hints) == ["en"]
    assert image.mode == mode
    assert image.tobytes() == original


@pytest.mark.parametrize("mode", ["L", "P", "RGBA"])
@pytest.mark.parametrize(
    "method",
    ["get_text_from_image", "get_layout_from_image", "get_layout_elements_from_image"],
)
def test_png_native_modes_keep_their_pixels_and_alpha(mode, method):
    image = Image.new(mode, (3, 2))
    if mode == "RGBA":
        image.putpixel((0, 0), (12, 34, 56, 78))
    agent = object.__new__(OCRAgentGoogleVision)
    agent.language = None
    agent.client = Mock()
    agent.client.document_text_detection.return_value = AnnotateImageResponse(
        full_text_annotation=TextAnnotation()
    )

    getattr(agent, method)(image)

    with Image.open(
        BytesIO(agent.client.document_text_detection.call_args.kwargs["image"].content)
    ) as encoded:
        assert encoded.mode == mode
        assert encoded.tobytes() == image.tobytes()
