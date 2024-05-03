from __future__ import annotations

import functools
import importlib
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from unstructured.partition.utils.constants import OCR_AGENT_MODULES_WHITELIST

if TYPE_CHECKING:
    from PIL import Image as PILImage
    from unstructured_inference.inference.elements import TextRegion
    from unstructured_inference.inference.layoutelement import LayoutElement


class OCRAgent(ABC):
    """Defines the interface for an Optical Character Recognition (OCR) service."""

    @staticmethod
    @functools.lru_cache(maxsize=None)
    def get_instance(ocr_agent_module: str) -> "OCRAgent":
        module_name, class_name = ocr_agent_module.rsplit(".", 1)
        if module_name in OCR_AGENT_MODULES_WHITELIST:
            module = importlib.import_module(module_name)
            loaded_class = getattr(module, class_name)
            return loaded_class()
        else:
            raise ValueError(
                f"Environment variable OCR_AGENT module name {module_name}, must be set to a"
                f" whitelisted module part of {OCR_AGENT_MODULES_WHITELIST}.",
            )

    @abstractmethod
    def get_layout_elements_from_image(
        self, image: PILImage.Image, ocr_languages: str = "eng"
    ) -> list[LayoutElement]:
        pass

    @abstractmethod
    def get_layout_from_image(
        self, image: PILImage.Image, ocr_languages: str = "eng"
    ) -> list[TextRegion]:
        pass

    @abstractmethod
    def get_text_from_image(self, image: PILImage.Image, ocr_languages: str = "eng") -> str:
        pass

    @abstractmethod
    def is_text_sorted(self) -> bool:
        pass
