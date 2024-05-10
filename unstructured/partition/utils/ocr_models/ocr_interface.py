from __future__ import annotations

import functools
import importlib
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from unstructured.logger import logger
from unstructured.partition.utils.config import env_config
from unstructured.partition.utils.constants import (
    OCR_AGENT_MODULES_WHITELIST,
    OCR_AGENT_PADDLE,
    OCR_AGENT_PADDLE_OLD,
    OCR_AGENT_TESSERACT,
    OCR_AGENT_TESSERACT_OLD,
)

if TYPE_CHECKING:
    from PIL import Image as PILImage
    from unstructured_inference.inference.elements import TextRegion
    from unstructured_inference.inference.layoutelement import LayoutElement


class OCRAgent(ABC):
    """Defines the interface for an Optical Character Recognition (OCR) service."""

    @classmethod
    def get_agent(cls) -> OCRAgent:
        """Get the configured OCRAgent instance.

        The OCR package used by the agent is determined by the `OCR_AGENT` environment variable.
        """
        ocr_agent_cls_qname = cls._get_ocr_agent_cls_qname()
        try:
            return cls.get_instance(ocr_agent_cls_qname)
        except (ImportError, AttributeError):
            raise ValueError(
                f"Environment variable OCR_AGENT must be set to an existing OCR agent module,"
                f" not {ocr_agent_cls_qname}."
            )

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

    @staticmethod
    def _get_ocr_agent_cls_qname() -> str:
        """Get the fully-qualified class name of the configured OCR agent.

        The qualified name (qname) looks like:
            "unstructured.partition.utils.ocr_models.tesseract_ocr.OCRAgentTesseract"

        The qname provides the full module address and class name of the OCR agent.
        """
        ocr_agent_qname = env_config.OCR_AGENT

        # -- map legacy method of setting OCR agent by key-name to full qname --
        qnames_by_keyname = {
            OCR_AGENT_TESSERACT_OLD: OCR_AGENT_TESSERACT,
            OCR_AGENT_PADDLE_OLD: OCR_AGENT_PADDLE,
        }
        if qname_mapped_from_keyname := qnames_by_keyname.get(ocr_agent_qname.lower()):
            logger.warning(
                f"OCR agent name {ocr_agent_qname} is outdated and will be removed in a future"
                f" release; please use {qname_mapped_from_keyname} instead"
            )
            return qname_mapped_from_keyname

        return ocr_agent_qname
