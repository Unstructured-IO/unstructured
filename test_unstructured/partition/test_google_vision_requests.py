from unittest.mock import Mock

import pytest
from google.cloud.vision import AnnotateImageResponse, TextAnnotation
from PIL import Image

from unstructured.partition.utils.ocr_models.google_vision_ocr import OCRAgentGoogleVision


def _agent(response):
    agent = object.__new__(OCRAgentGoogleVision)
    agent.language = "en"
    agent.client = Mock()
    agent.client.document_text_detection.return_value = response
    return agent


def test_layout_elements_use_one_annotation_response_for_text_and_regions():
    response = AnnotateImageResponse(full_text_annotation=TextAnnotation(text=""))
    agent = _agent(response)

    layout = agent.get_layout_elements_from_image(Image.new("RGB", (4, 4)))

    assert len(layout) == 0
    assert agent.client.document_text_detection.call_count == 1
    request = agent.client.document_text_detection.call_args.kwargs
    assert list(request["image_context"].language_hints) == ["en"]
    assert request["image"].content.startswith(b"\x89PNG")


@pytest.mark.parametrize(
    "method", ["get_text_from_image", "get_layout_from_image", "get_layout_elements_from_image"]
)
def test_service_errors_are_not_silently_treated_as_empty_documents(method):
    agent = _agent(AnnotateImageResponse(error={"code": 7, "message": "Permission denied"}))

    with pytest.raises(RuntimeError, match=r"Google Vision OCR failed \(7\): Permission denied"):
        getattr(agent, method)(Image.new("RGB", (4, 4)))

    assert agent.client.document_text_detection.call_count == 1
