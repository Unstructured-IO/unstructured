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
    from unstructured_inference.inference.elements import TextRegions
    from unstructured_inference.inference.layoutelement import LayoutElements


class OCRAgent(ABC):
    """Defines the interface for an Optical Character Recognition (OCR) service."""

    @classmethod
    def get_agent(cls, language: str) -> OCRAgent:
        """Get the configured OCRAgent instance.

        The OCR package used by the agent is determined by the `OCR_AGENT` environment variable.
        """
        ocr_agent_cls_qname = cls._get_ocr_agent_cls_qname()
        return cls.get_instance(ocr_agent_cls_qname, language)

    @staticmethod
    @functools.lru_cache(maxsize=env_config.OCR_AGENT_CACHE_SIZE)
    def get_instance(ocr_agent_module: str, language: str) -> "OCRAgent":
        module_name, class_name = ocr_agent_module.rsplit(".", 1)
        if module_name not in OCR_AGENT_MODULES_WHITELIST:
            raise ValueError(
                f"Environment variable OCR_AGENT module name {module_name} must be set to a "
                f"whitelisted module part of {OCR_AGENT_MODULES_WHITELIST}."
            )

        try:
            module = importlib.import_module(module_name)
            loaded_class = getattr(module, class_name)
            return loaded_class(language)
        except (ImportError, AttributeError) as e:
            logger.error(f"Failed to get OCRAgent instance: {e}")
            raise RuntimeError(
                "Could not get the OCRAgent instance. Please check the OCR package and the "
                "OCR_AGENT environment variable."
            )

    @abstractmethod
    def get_layout_elements_from_image(self, image: PILImage.Image) -> LayoutElements:
        pass

    @abstractmethod
    def get_layout_from_image(self, image: PILImage.Image) -> TextRegions:
        pass

    @abstractmethod
    def get_text_from_image(self, image: PILImage.Image) -> str:
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
