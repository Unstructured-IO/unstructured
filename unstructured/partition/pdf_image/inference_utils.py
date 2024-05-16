from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from unstructured_inference.constants import Source
from unstructured_inference.inference.elements import TextRegion
from unstructured_inference.inference.layoutelement import (
    LayoutElement,
    partition_groups_from_regions,
)

from unstructured.documents.elements import ElementType

if TYPE_CHECKING:
    from unstructured_inference.inference.elements import Rectangle


def build_text_region_from_coords(
    x1: int | float,
    y1: int | float,
    x2: int | float,
    y2: int | float,
    text: Optional[str] = None,
    source: Optional[Source] = None,
) -> TextRegion:
    """"""
    return TextRegion.from_coords(x1, y1, x2, y2, text=text, source=source)


def build_layout_element(
    bbox: "Rectangle",
    text: Optional[str] = None,
    source: Optional[Source] = None,
    element_type: Optional[str] = None,
) -> LayoutElement:
    """"""

    return LayoutElement(bbox=bbox, text=text, source=source, type=element_type)


def build_layout_elements_from_ocr_regions(
    ocr_regions: list[TextRegion],
    ocr_text: Optional[str] = None,
    group_by_ocr_text: bool = False,
) -> list[LayoutElement]:
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
        grouped_regions = partition_groups_from_regions(ocr_regions)

    merged_regions = [merge_text_regions(group) for group in grouped_regions]
    return [
        build_layout_element(
            bbox=r.bbox, text=r.text, source=r.source, element_type=ElementType.UNCATEGORIZED_TEXT
        )
        for r in merged_regions
    ]


def merge_text_regions(regions: list[TextRegion]) -> TextRegion:
    """
    Merge a list of TextRegion objects into a single TextRegion.

    Parameters:
    - group (list[TextRegion]): A list of TextRegion objects to be merged.

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
