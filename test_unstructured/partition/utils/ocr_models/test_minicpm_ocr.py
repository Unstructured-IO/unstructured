from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import requests
from PIL import Image

from unstructured.partition.utils.ocr_models.minicpm_ocr import OCRAgentMiniCPM

POST = "unstructured.partition.utils.ocr_models.minicpm_ocr.requests.post"


def _response(content: str = "") -> MagicMock:
    response = MagicMock()
    response.json.return_value = {"choices": [{"message": {"content": content}}]}
    response.raise_for_status.return_value = None
    return response


@pytest.fixture
def agent(monkeypatch) -> OCRAgentMiniCPM:
    monkeypatch.setenv("MINICPM_OCR_BASE_URL", "http://localhost:8000/v1/")
    monkeypatch.setenv("MINICPM_OCR_API_KEY", "secret")
    monkeypatch.setenv("MINICPM_OCR_MODEL", "minicpm-ocr")
    monkeypatch.setenv("MINICPM_OCR_TIMEOUT", "30")
    monkeypatch.delenv("MINICPM_OCR_PROMPT", raising=False)
    return OCRAgentMiniCPM(language="en")


def test_requires_base_url(monkeypatch):
    monkeypatch.delenv("MINICPM_OCR_BASE_URL", raising=False)

    with pytest.raises(ValueError, match="MINICPM_OCR_BASE_URL"):
        OCRAgentMiniCPM()


def test_get_text_from_image_sends_openai_request(agent):
    image = Image.new("RGB", (4, 4), "white")

    with patch(POST, return_value=_response("  Hello\n")) as post:
        assert agent.get_text_from_image(image) == "Hello"

    args, kwargs = post.call_args
    assert args[0] == "http://localhost:8000/v1/chat/completions"
    assert kwargs["timeout"] == 30
    assert kwargs["headers"]["Authorization"] == "Bearer secret"

    payload = kwargs["json"]
    assert payload["model"] == "minicpm-ocr"
    assert payload["temperature"] == 0
    content = payload["messages"][0]["content"]
    assert content[0] == {"type": "text", "text": "Text Recognition:"}
    assert content[1]["type"] == "image_url"
    assert content[1]["image_url"]["url"].startswith("data:image/png;base64,")


def test_custom_prompt_overrides_default(monkeypatch):
    monkeypatch.setenv("MINICPM_OCR_BASE_URL", "http://localhost:8000/v1")
    monkeypatch.setenv("MINICPM_OCR_PROMPT", "Table Recognition:")
    agent = OCRAgentMiniCPM()

    with patch(POST, return_value=_response("ok")) as post:
        agent.get_text_from_image(Image.new("RGB", (2, 2), "white"))

    assert post.call_args.kwargs["json"]["messages"][0]["content"][0]["text"] == (
        "Table Recognition:"
    )


def test_api_key_is_optional(monkeypatch):
    monkeypatch.setenv("MINICPM_OCR_BASE_URL", "http://localhost:8000/v1")
    monkeypatch.delenv("MINICPM_OCR_API_KEY", raising=False)
    agent = OCRAgentMiniCPM()

    with patch(POST, return_value=_response("ok")) as post:
        agent.get_text_from_image(Image.new("RGB", (2, 2), "white"))

    assert "Authorization" not in post.call_args.kwargs["headers"]


def test_http_error_is_wrapped(agent):
    response = MagicMock()
    response.raise_for_status.side_effect = requests.HTTPError("500 Server Error")

    with patch(POST, return_value=response):
        with pytest.raises(RuntimeError, match="MiniCPM OCR request failed"):
            agent.get_text_from_image(Image.new("RGB", (2, 2), "white"))


def test_unexpected_response_is_wrapped(agent):
    response = MagicMock()
    response.json.return_value = {"choices": []}
    response.raise_for_status.return_value = None

    with patch(POST, return_value=response):
        with pytest.raises(RuntimeError, match="unexpected response"):
            agent.get_text_from_image(Image.new("RGB", (2, 2), "white"))


def test_text_is_sorted(agent):
    assert agent.is_text_sorted() is True


def test_layout_covers_the_whole_image(agent):
    pytest.importorskip("unstructured_inference")
    from unstructured.partition.pdf_image.inference_utils import (
        build_text_region_from_coords,  # noqa: F401
    )

    image = Image.new("RGB", (20, 10), "white")
    with patch(POST, return_value=_response("page text")):
        regions = agent.get_layout_from_image(image)

    assert len(regions) == 1
    region = regions[0]
    assert region.text == "page text"
    assert (region.x1, region.y1, region.x2, region.y2) == (0, 0, 20, 10)
