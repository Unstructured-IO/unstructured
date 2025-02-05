from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import numpy as np
from unstructured_inference.constants import Source
from unstructured_inference.inference.elements import TextRegion, TextRegions
from unstructured_inference.inference.layoutelement import (
    LayoutElement,
    LayoutElements,
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
    ocr_regions: TextRegions,
    ocr_text: Optional[str] = None,
    group_by_ocr_text: bool = False,
) -> LayoutElements:
    """
    Get layout elements from OCR regions
    """

    grouped_regions = []
    if group_by_ocr_text:
        text_sections = ocr_text.split("\n\n")
        mask = np.ones(ocr_regions.texts.shape).astype(bool)
        indices = np.arange(len(mask))
        for text_section in text_sections:
            regions = []
            words = text_section.replace("\n", " ").split()
            for i, text in enumerate(ocr_regions.texts[mask]):
                if not words:
                    break
                if text in words:
                    regions.append(indices[mask][i])
                    words.remove(text)

            if not regions:
                continue

            mask[regions] = False
            grouped_regions.append(ocr_regions.slice(regions))
    else:
        grouped_regions = partition_groups_from_regions(ocr_regions)

    merged_regions = TextRegions.from_list([merge_text_regions(group) for group in grouped_regions])
    return LayoutElements(
        element_coords=merged_regions.element_coords,
        texts=merged_regions.texts,
        sources=merged_regions.sources,
        element_class_ids=np.zeros(merged_regions.texts.shape),
        element_class_id_map={0: ElementType.UNCATEGORIZED_TEXT},
    )


def merge_text_regions(regions: TextRegions) -> TextRegion:
    """
    Merge a list of TextRegion objects into a single TextRegion.

    Parameters:
    - group (TextRegions): A group of TextRegion objects to be merged.

    Returns:
    - TextRegion: A single merged TextRegion object.
    """

    if not regions:
        raise ValueError("The text regions to be merged must be provided.")

    min_x1 = regions.x1.min().astype(float)
    min_y1 = regions.y1.min().astype(float)
    max_x2 = regions.x2.max().astype(float)
    max_y2 = regions.y2.max().astype(float)

    merged_text = " ".join([text for text in regions.texts if text])
    # assumption is the regions has the same source
    source = regions.sources[0]

    return TextRegion.from_coords(min_x1, min_y1, max_x2, max_y2, merged_text, source)
