from __future__ import annotations

import base64
from io import BytesIO
from typing import TYPE_CHECKING, Optional

import requests

from unstructured.logger import logger, trace_logger
from unstructured.partition.utils.config import env_config
from unstructured.partition.utils.constants import Source
from unstructured.partition.utils.ocr_models.ocr_interface import OCRAgent

if TYPE_CHECKING:
    from PIL import Image as PILImage
    from unstructured_inference.inference.elements import TextRegions
    from unstructured_inference.inference.layoutelement import LayoutElements


class OCRAgentMiniCPM(OCRAgent):
    """OCR service implementation for a MiniCPM-OCR OpenAI-compatible endpoint.

    MiniCPM-OCR is a block-level recognition model: the ``hi_res`` strategy crops
    each layout element and calls ``get_text_from_image`` on the crop, which is
    the shape this service expects. Set ``OCR_AGENT`` to
    ``unstructured.partition.utils.ocr_models.minicpm_ocr.OCRAgentMiniCPM`` and
    ``MINICPM_OCR_BASE_URL`` to the service's OpenAI-compatible base URL.
    """

    def __init__(self, language: Optional[str] = None) -> None:
        self.language = language
        self.base_url = env_config.MINICPM_OCR_BASE_URL.rstrip("/")
        if not self.base_url:
            raise ValueError(
                "MINICPM_OCR_BASE_URL is not set. Point it at an OpenAI-compatible "
                "MiniCPM-OCR endpoint, for example http://localhost:8000/v1."
            )
        self.model = env_config.MINICPM_OCR_MODEL
        self.api_key = env_config.MINICPM_OCR_API_KEY
        self.timeout = env_config.MINICPM_OCR_TIMEOUT
        self.prompt = env_config.MINICPM_OCR_PROMPT
        logger.info(f"Using MiniCPM-OCR at {self.base_url} with model {self.model}")

    def is_text_sorted(self) -> bool:
        return True

    def get_text_from_image(self, image: PILImage.Image) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": self.prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": self._encode_image(image)},
                        },
                    ],
                }
            ],
            "temperature": 0,
            "stream": False,
        }
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
            body = response.json()
        except (requests.RequestException, ValueError) as exc:
            raise RuntimeError(f"MiniCPM OCR request failed: {exc}") from exc

        try:
            content = body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(f"MiniCPM OCR returned an unexpected response: {body!r}") from exc
        return (content or "").strip()

    def get_layout_from_image(self, image: PILImage.Image) -> TextRegions:
        trace_logger.detail("Processing entire page OCR with MiniCPM-OCR...")
        from unstructured_inference.inference.elements import TextRegions

        from unstructured.partition.pdf_image.inference_utils import (
            build_text_region_from_coords,
        )

        text = self.get_text_from_image(image)
        width, height = image.size
        region = build_text_region_from_coords(
            0,
            0,
            width,
            height,
            text=text,
            source=Source.OCR_MINICPM,
        )
        return TextRegions.from_list([region])

    def get_layout_elements_from_image(self, image: PILImage.Image) -> LayoutElements:
        from unstructured.partition.pdf_image.inference_utils import (
            build_layout_elements_from_ocr_regions,
        )

        ocr_regions = self.get_layout_from_image(image)
        ocr_text = self.get_text_from_image(image)
        return build_layout_elements_from_ocr_regions(
            ocr_regions=ocr_regions,
            ocr_text=ocr_text,
            group_by_ocr_text=False,
        )

    @staticmethod
    def _encode_image(image: PILImage.Image) -> str:
        with BytesIO() as buffer:
            image.save(buffer, format="PNG")
            encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
        return f"data:image/png;base64,{encoded}"
