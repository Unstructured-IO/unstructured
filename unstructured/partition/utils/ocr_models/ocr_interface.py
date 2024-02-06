import functools
import importlib
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, List

from unstructured.partition.utils.constants import OCR_AGENT_MODULES_WHITELIST

if TYPE_CHECKING:
    from PIL import PILImage
    from unstructured_inference.inference.elements import TextRegion
    from unstructured_inference.inference.layoutelement import (
        LayoutElement,
    )


class OCRAgent(ABC):
    def __init__(self):
        self.agent = self.load_agent()

    @abstractmethod
    def load_agent(self, language: str) -> Any:
        pass

    @abstractmethod
    def is_text_sorted(self) -> bool:
        pass

    @abstractmethod
    def get_text_from_image(self, image: "PILImage", ocr_languages: str = "eng") -> str:
        pass

    @abstractmethod
    def get_layout_from_image(
        self, image: "PILImage", ocr_languages: str = "eng"
    ) -> List["TextRegion"]:
        pass

    @abstractmethod
    def get_layout_elements_from_image(
        self, image: "PILImage", ocr_languages: str = "eng"
    ) -> List["LayoutElement"]:
        pass

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
                f"Environment variable OCR_AGENT module name {module_name}",
                f" must be set to a whitelisted module part of {OCR_AGENT_MODULES_WHITELIST}.",
            )
