from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import numpy as np
from unstructured_inference.config import inference_config
from unstructured_inference.constants import FULL_PAGE_REGION_THRESHOLD, Source
from unstructured_inference.inference.elements import TextRegion, TextRegions
from unstructured_inference.inference.layoutelement import (
    LayoutElement,
    LayoutElements,
    partition_groups_from_regions,
)

from unstructured.documents.elements import ElementType
from unstructured.partition.pdf_image.pdfminer_processing import (
    bboxes1_is_almost_subregion_of_bboxes2,
    boxes_iou,
)

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
                    mask[mask][i] = False
                    words.remove(text)

            if not regions:
                continue

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


def array_merge_inferred_layout_with_extracted_layout(
    inferred_layout: LayoutElements,
    extracted_layout: LayoutElements,
    page_image_size: tuple,
    same_region_threshold: float = inference_config.LAYOUT_SAME_REGION_THRESHOLD,
    subregion_threshold: float = inference_config.LAYOUT_SUBREGION_THRESHOLD,
) -> LayoutElements:
    """merge elements using array data structures; it also returns LayoutElements instead of
    collection of LayoutElement"""
    extracted_elements_to_add = []
    inferred_regions_to_remove = []
    w, h = page_image_size
    full_page_region = Rectangle(0, 0, w, h)
    # Full page images are ignored
    # extracted elements to add:
    # - non full-page images
    # - extracted text region that doesn't match an inferred region; with caveats below
    # matching between extracted text and inferred text can result in three different outcomes
    image_indices_to_keep = np.where(extracted_layout.element_class_ids == 1)[0]
    full_page_image_mask = boxes_iou(
        extracted_layout.slice(image_indices_to_keep).element_coords,
        full_page_region,
        threshold=FULL_PAGE_REGION_THRESHOLD,
    ).sum(axis=1)
    image_indices_to_keep = image_indices_to_keep[~full_page_image_mask]

    # rule: any inferred box that is almost the same as an extracted image box is removed
    boxes_almost_same = boxes_iou(
        inferred_layout.element_coords,
        extracted_layout.slice(image_indices_to_keep).element_coords,
        threshold=same_region_threshold,
    ).sum(axis=1).astype(bool)

    inferred_indices_to_proc = np.arange(len(inferred_region))[boxes_almost_same]
    inferred_layout_to_proc = inferred_layout.slice(inferred_indices_to_keep)

    # now merge text regions
    text_element_indices = np.where(extracted_layout.element_class_ids == 0)[0]
    extracted_text_layouts = extracted_layout.slice(text_element_indices)
    boxes_almost_same = boxes_iou(
        extracted_text_layouts.element_coords,
        inferred_layout_to_proc.element_coords,
        threshold=same_region_threshold,
    )
    inferred_is_subregion_of_extracted = bboxes1_is_almost_subregion_of_bboxes2(
        inferred_layout_to_proc.element_coords,
        extracted_text_layouts.element_coords,
        threshold=subregion_threshold,
    )
    # refactor so we only need to compute intersection once
    extracted_is_subregion_of_inferred = bboxes1_is_almost_subregion_of_bboxes2(
        extracted_text_layouts.element_coords,
        inferred_layout_to_proc.element_coords,
        threshold=subregion_threshold,
    )
    inferred_text_idx = [
        idx
        for idx, class_name in inferred_layout_to_proc.element_class_id_map.items()
        if class_name
        not in (
            ElementType.FIGURE,
            ElementType.IMAGE,
            ElementType.PAGE_BREAK,
            ElementType.TABLE,
        )
    ]
    inferred_is_text = np.zeros((len(inferred_layout),))
    for idx in inferred_text_idx:
        inferred_is_text = np.logical_and(
            inferred_is_text, inferred_layout_to_proc.element_class_ids == idx
        )
    # now iterate over same bbox row by row, i.e., one extracted text element at a time
    extracted_indices_to_keep =  []
    inferred_indices_to_remove = []
    for i, extracted_text_row in boxes_almost_same:
        # NOTE (yao): current source algorithm in inference lib does NOT remove an inferred layout
        # from the process even if it is marked as to remove.
        first_same_inferred_region = np.where(extracted_text_row==1)[0]
        if first_same_inferred_region:
            # keep this inferred and remove extracted region
            grow_region_to_match_region(

