import functools
import importlib
from abc import ABC, abstractmethod
from typing import Any, List, Optional, cast

from PIL import Image as PILImage
from unstructured_inference.inference.elements import TextRegion
from unstructured_inference.inference.layoutelement import (
    LayoutElement,
    partition_groups_from_regions,
)

from unstructured.documents.elements import ElementType
from unstructured.partition.utils.constants import OCR_AGENT_MODULES_WHITELIST


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
    def get_text_from_image(self, image: PILImage, ocr_languages: str = "eng") -> str:
        pass

    @abstractmethod
    def get_layout_from_image(
        self, image: PILImage, ocr_languages: str = "eng"
    ) -> List[TextRegion]:
        pass

    @abstractmethod
    def get_layout_elements_from_image(
        self, image: PILImage, ocr_languages: str = "eng"
    ) -> List[LayoutElement]:
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


def get_elements_from_ocr_regions(
    ocr_regions: List[TextRegion],
    ocr_text: Optional[str] = None,
    group_by_ocr_text: bool = False,
) -> List[LayoutElement]:
    """
    Get layout elements from OCR regions
    """

    if group_by_ocr_text:
        text_sections = ocr_text.split("\n\n")
        grouped_regions = []
        for text_section in text_sections:
            regions = []
            words = text_section.replace("\n", " ").split()
            for ocr_region in ocr_regions:
                if not words:
                    break
                if ocr_region.text in words:
                    regions.append(ocr_region)
                    words.remove(ocr_region.text)

            if not regions:
                continue

            for r in regions:
                ocr_regions.remove(r)

            grouped_regions.append(regions)
    else:
        grouped_regions = cast(
            List[List[TextRegion]],
            partition_groups_from_regions(ocr_regions),
        )

    merged_regions = [merge_text_regions(group) for group in grouped_regions]
    return [
        LayoutElement(
            text=r.text, source=r.source, type=ElementType.UNCATEGORIZED_TEXT, bbox=r.bbox
        )
        for r in merged_regions
    ]


def merge_text_regions(regions: List[TextRegion]) -> TextRegion:
    """
    Merge a list of TextRegion objects into a single TextRegion.

    Parameters:
    - group (List[TextRegion]): A list of TextRegion objects to be merged.

    Returns:
    - TextRegion: A single merged TextRegion object.
    """

    if not regions:
        raise ValueError("The text regions to be merged must be provided.")

    min_x1 = min([tr.bbox.x1 for tr in regions])
    min_y1 = min([tr.bbox.y1 for tr in regions])
    max_x2 = max([tr.bbox.x2 for tr in regions])
    max_y2 = max([tr.bbox.y2 for tr in regions])

    merged_text = " ".join([tr.text for tr in regions if tr.text])
    sources = [tr.source for tr in regions]
    source = sources[0] if all(s == sources[0] for s in sources) else None

    return TextRegion.from_coords(min_x1, min_y1, max_x2, max_y2, merged_text, source)
