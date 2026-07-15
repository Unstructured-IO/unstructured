from __future__ import annotations

import os
from typing import TYPE_CHECKING, Iterable, List

import numpy as np
from unstructured_inference.config import inference_config
from unstructured_inference.constants import FULL_PAGE_REGION_THRESHOLD, IsExtracted
from unstructured_inference.inference.elements import Rectangle

from unstructured.documents.elements import ElementType
from unstructured.partition.pdf_image.pdf_image_utils import remove_control_characters
from unstructured.partition.utils.config import env_config
from unstructured.partition.utils.constants import SORT_MODE_BASIC, Source
from unstructured.partition.utils.sorting import sort_text_regions
from unstructured.utils import requires_dependencies

if TYPE_CHECKING:
    from unstructured_inference.inference.elements import TextRegions
    from unstructured_inference.inference.layout import DocumentLayout
    from unstructured_inference.inference.layoutelement import LayoutElements


EPSILON_AREA = 0.01
# rounding floating point to nearest machine precision
DEFAULT_ROUND = 15


def _rotate_bboxes(coords: np.ndarray, angle: int, width: float, height: float) -> np.ndarray:
    """Rotate bounding boxes to mirror a rendered page image that was rotated ``angle``
    degrees counter-clockwise (PIL convention) with ``expand=True``.

    ``width``/``height`` are the page-image dimensions in the un-rotated (display) frame.
    unstructured-inference may rotate a page image to make its dominant text upright;
    applying the same rotation here keeps the extracted layer aligned with the
    object-detection layer so the two merge correctly.
    """
    angle %= 360
    if angle == 0 or coords.size == 0:
        return coords
    x1, y1, x2, y2 = coords[:, 0], coords[:, 1], coords[:, 2], coords[:, 3]
    if angle == 90:
        return np.column_stack((y1, width - x2, y2, width - x1))
    if angle == 180:
        return np.column_stack((width - x2, height - y2, width - x1, height - y1))
    if angle == 270:
        return np.column_stack((height - y2, x1, height - y1, x2))
    return coords


def _validate_bbox(bbox: list[int | float]) -> bool:
    return all(x is not None for x in bbox) and (bbox[2] - bbox[0] > 0) and (bbox[3] - bbox[1] > 0)


def _minimum_containing_coords(*regions: TextRegions) -> np.ndarray:
    # TODO: refactor to just use np array as input
    # Optimization: Use np.stack and np.column_stack to build output in a single step
    x1s = np.array([region.x1 for region in regions])
    y1s = np.array([region.y1 for region in regions])
    x2s = np.array([region.x2 for region in regions])
    y2s = np.array([region.y2 for region in regions])
    # Use np.min/max reduction rather than create matrix then operate.
    return np.column_stack(
        (
            np.min(x1s, axis=0),
            np.min(y1s, axis=0),
            np.max(x2s, axis=0),
            np.max(y2s, axis=0),
        )
    )


def _inferred_is_elementtype(
    inferred_layout: LayoutElements, etypes: Iterable[ElementType]
) -> np.ndarry:
    inferred_text_idx = [
        idx
        for idx, class_name in inferred_layout.element_class_id_map.items()
        if class_name in etypes
    ]
    inferred_is_etypes = np.zeros((len(inferred_layout),)).astype(bool)
    for idx in inferred_text_idx:
        inferred_is_etypes = np.logical_or(
            inferred_is_etypes, inferred_layout.element_class_ids == idx
        )
    return inferred_is_etypes


def _inferred_is_text(inferred_layout: LayoutElements) -> np.ndarry:
    """return a boolean array masking for each element if it is non-image type (True) or image like
    type (False); image types are ElementType.FIGURE/IMAGE/PAGE_BREAK/TABLE"""
    return ~_inferred_is_elementtype(
        inferred_layout,
        etypes=(
            ElementType.FIGURE,
            ElementType.IMAGE,
            # NOTE (yao): PICTURE is not in the loop version of the logic in inference library
            # ElementType.PICTURE,
            ElementType.PAGE_BREAK,
            ElementType.TABLE,
        ),
    )


def _merge_extracted_into_inferred_when_almost_the_same(
    extracted_layout: LayoutElements,
    inferred_layout: LayoutElements,
    same_region_threshold: float,
) -> tuple[np.ndarray]:
    """merge exstracted elements that have almost the same bounding box as an inferrred element into
    that inferred element: a) the inferred element bounding box is updated, if needed, to be able to
    bound the merged extracted element; b) the inferred element uses the extracted element's text as
    its text attribute. Return a boolean mask array indicating where (when True) an extracted
    element is merged therefore should be excluded from later analysis"""

    if len(inferred_layout) == 0:
        return np.array([False] * len(extracted_layout))
    if len(extracted_layout) == 0:
        return np.array([])

    boxes_almost_same = boxes_iou(
        extracted_layout.element_coords,
        inferred_layout.element_coords,
        threshold=same_region_threshold,
    )
    extracted_almost_the_same_as_inferred = np.any(boxes_almost_same, axis=1)
    # NOTE: if a row is full of False the argmax returns first index; we use the mask above to
    # distinguish those (they would be False in the mask)
    first_match = np.argmax(boxes_almost_same, axis=1)
    inferred_indices_to_update = first_match[extracted_almost_the_same_as_inferred]
    extracted_to_remove = extracted_layout.slice(extracted_almost_the_same_as_inferred)
    # copy here in case we change the extracted layout later
    inferred_layout.texts[inferred_indices_to_update] = extracted_to_remove.texts.copy()
    inferred_layout.is_extracted_array[inferred_indices_to_update] = (
        extracted_to_remove.is_extracted_array.copy()
    )
    # use coords that can bound BOTH the inferred and extracted region as final bounding box coords
    inferred_layout.element_coords[inferred_indices_to_update] = _minimum_containing_coords(
        inferred_layout.slice(inferred_indices_to_update),
        extracted_to_remove,
    )
    return extracted_almost_the_same_as_inferred


def _merge_extracted_that_are_subregion_of_inferred_text(
    extracted_layout: LayoutElements,
    inferred_layout: LayoutElements,
    extracted_is_subregion_of_inferred: np.ndarray,
    extracted_to_proc: np.ndarray,
    inferred_to_proc: np.ndarray,
) -> LayoutElements:
    """merged extracted elements that are subregions of inferrred elements into those inferred
    elements: the inferred elements' bounding boxes expands, if needed, to include those subregion
    elements. Returns the modified inferred layout where some of its elements' bounding boxes may
    have expanded due to merging.
    """
    # in theory one extracted __should__ only match at most one inferred region, given inferred
    # region can not overlap; so first match here __should__ also be the only match
    inferred_to_iter = inferred_to_proc[inferred_to_proc]
    extracted_to_iter = extracted_to_proc[extracted_to_proc]
    for inferred_index, inferred_row in enumerate(extracted_is_subregion_of_inferred.T):
        matches = np.where(inferred_row)[0]
        if not matches.size:
            continue
        # Technically those two lines below can be vectorized but this loop would still run anyway;
        # it is not clear which one is overall faster so might worth profiling in the future
        extracted_to_iter[matches] = False
        inferred_to_iter[inferred_index] = False
        # then expand inferred box by all the extracted boxes
        # FIXME (yao): this part is broken at the moment
        inferred_layout.element_coords[[inferred_index]] = _minimum_containing_coords(
            inferred_layout.slice([inferred_index]),
            *[extracted_layout.slice([match]) for match in matches],
        )
    inferred_to_proc[inferred_to_proc] = inferred_to_iter
    extracted_to_proc[extracted_to_proc] = extracted_to_iter
    return inferred_layout


def _mark_non_table_inferred_for_removal_if_has_subregion_relationship(
    extracted_layout: LayoutElements,
    inferred_layout: LayoutElements,
    inferred_to_keep: np.ndarray,
    subregion_threshold: float,
) -> np.ndaray:
    """
    Marking elements in inferred layout to remove after merging when:
    - if the inferred element is subregion of an extracted element
    - and/or an extracted element is subregion of this inferred element
    Return updated mask on which inferred indices to keep (when True)
    """
    inferred_is_subregion_of_extracted = bboxes1_is_almost_subregion_of_bboxes2(
        inferred_layout.element_coords,
        extracted_layout.element_coords,
        threshold=subregion_threshold,
    )
    extracted_is_subregion_of_inferred = bboxes1_is_almost_subregion_of_bboxes2(
        extracted_layout.element_coords,
        inferred_layout.element_coords,
        threshold=subregion_threshold,
    )
    inferred_to_remove_mask = (
        np.logical_or(
            inferred_is_subregion_of_extracted,
            extracted_is_subregion_of_inferred.T,
        )
        .sum(axis=1)
        .astype(bool)
    )
    # NOTE (yao): maybe we should expand those matching extracted region to contain the inferred
    # regions it has subregion relationship with? like we did for inferred regions
    inferred_to_keep[inferred_to_remove_mask] = False
    return inferred_to_keep


@requires_dependencies("unstructured_inference")
def array_merge_inferred_layout_with_extracted_layout(
    inferred_layout: LayoutElements,
    extracted_layout: LayoutElements,
    page_image_size: tuple,
    same_region_threshold: float = inference_config.LAYOUT_SAME_REGION_THRESHOLD,
    subregion_threshold: float = inference_config.LAYOUT_SUBREGION_THRESHOLD,
    max_rounds: int = 5,
) -> LayoutElements:
    """merge elements using array data structures; it also returns LayoutElements instead of
    collection of LayoutElement"""
    from unstructured_inference.inference.layoutelement import LayoutElements

    if len(extracted_layout) == 0:
        return inferred_layout
    if len(inferred_layout) == 0:
        return extracted_layout

    w, h = page_image_size
    full_page_region = Rectangle(0, 0, w, h)
    # ==== RULE 0: Full page extracted images are ignored
    # non full page extracted image regions are kept, except when they match a non-text inferred
    # region then we use the common bounding boxes and keep just one of the two sets (see rules
    # below)
    image_indices_to_keep = np.where(extracted_layout.element_class_ids == 1)[0]
    if len(image_indices_to_keep):
        full_page_image_mask = (
            boxes_iou(
                extracted_layout.slice(image_indices_to_keep).element_coords,
                [full_page_region],
                threshold=FULL_PAGE_REGION_THRESHOLD,
            )
            .sum(axis=1)
            .astype(bool)
        )
        image_indices_to_keep = image_indices_to_keep[~full_page_image_mask]

    # ==== RULE 1: any inferred box that is almost the same as an extracted image box, inferred is
    # removed
    # NOTE (yao): what if od model detects table but extracted layout says image -> we would lose
    # the table
    boxes_almost_same = (
        boxes_iou(
            inferred_layout.element_coords,
            extracted_layout.slice(image_indices_to_keep).element_coords,
            threshold=same_region_threshold,
        )
        .sum(axis=1)
        .astype(bool)
    )

    # drop off those matching inferred from processing
    inferred_layout_to_proc = inferred_layout.slice(~boxes_almost_same)
    inferred_to_keep = np.array([True] * len(inferred_layout_to_proc))

    # TODO (yao): experiment with all regions, not just text region, being potential targets to be
    # merged into inferred elements
    text_element_indices = np.where(extracted_layout.element_class_ids == 0)[0]

    if len(text_element_indices) == 0:
        return LayoutElements.concatenate(
            (
                inferred_layout_to_proc,
                extracted_layout.slice(image_indices_to_keep),
            )
        )

    if len(inferred_layout_to_proc) == 0:
        return extracted_layout.slice(np.concatenate((image_indices_to_keep, text_element_indices)))

    extracted_text_layouts = extracted_layout.slice(text_element_indices)
    # ==== RULE 2. if there is a inferred region almost the same as the extracted text-region ->
    # keep inferred and removed extracted region; here we put more trust in OD model more than
    # extracted layout for bounding box
    extracted_to_remove = _merge_extracted_into_inferred_when_almost_the_same(
        extracted_text_layouts,
        inferred_layout_to_proc,
        same_region_threshold,
    )

    # ==== RULE 3. if extracted is subregion of an inferrred text region:
    # remove extracted and keep inferred;
    # expand inferred bounding box if needed to encompass all subregion extracted boxes
    # NOTE (yao):
    # currently this rule can fail to capture almost overlaps of two text regions when the
    # extracted layout has larger bounding boxes (in area). It might be worth it to use simpler IOU
    # thresholding or use the minimum of the two areas when computing sub regions
    inferred_to_proc = _inferred_is_text(inferred_layout_to_proc)
    extracted_to_proc = ~extracted_to_remove
    rounds = 0

    # because inferred layout sizes can be increased after one pass we may need to run through
    # multiple passes; the original looped version increases layout size when it is processed so
    # order would matter in that version. Here we loop over multiple times to avoid order being a
    # factor -> this is one big difference between the current refactor and the version in inference
    # lib that uses loops
    while rounds < max_rounds and any(inferred_to_proc) and any(extracted_to_proc):
        rounds += 1
        inferred_to_proc_at_start = inferred_to_proc.copy()
        extracted_to_proc_start = extracted_to_proc.copy()

        extracted_is_subregion_of_inferred = bboxes1_is_almost_subregion_of_bboxes2(
            extracted_text_layouts.element_coords,
            inferred_layout_to_proc.element_coords,
            threshold=subregion_threshold,
        )

        updated_inferred = _merge_extracted_that_are_subregion_of_inferred_text(
            extracted_text_layouts.slice(extracted_to_proc),
            inferred_layout_to_proc.slice(inferred_to_proc),
            extracted_is_subregion_of_inferred[extracted_to_proc][:, inferred_to_proc],
            # both those following two are modified in place in the function
            extracted_to_proc,
            inferred_to_proc,
        )
        # unfortunately slice uses "fancy" indexing and it generates a copy instead of a view, which
        # was intentional by design to avoid unintended modification of the original data
        inferred_layout_to_proc.element_coords[inferred_to_proc_at_start] = (
            updated_inferred.element_coords
        )

        if np.array_equal(extracted_to_proc_start, extracted_to_proc) and np.array_equal(
            inferred_to_proc_at_start, inferred_to_proc
        ):
            break

    # ==== RULE 4. if extracted is subregion of an inferred or inferred is subregion of extracted,
    # except for inferrred tables, remove inferred and chose extracted
    extracted_to_keep = np.concatenate(
        (image_indices_to_keep, text_element_indices[extracted_to_proc])
    )
    if extracted_to_keep.size:
        inferred_to_proc = np.logical_or(
            inferred_to_proc,
            _inferred_is_elementtype(
                inferred_layout_to_proc,
                [
                    ElementType.FIGURE,
                    ElementType.IMAGE,
                    ElementType.PICTURE,
                ],
            ),
        )
        inferred_to_keep[inferred_to_proc] = (
            _mark_non_table_inferred_for_removal_if_has_subregion_relationship(
                extracted_layout.slice(extracted_to_keep),
                inferred_layout_to_proc.slice(inferred_to_proc),
                inferred_to_keep[inferred_to_proc],
                subregion_threshold,
            )
        )

    # ==== RULE 5. all else -> keep extracted region; note we also keep extracted image regions
    # that is a subregion of an inferred text region
    extracted_to_keep.sort()

    final_layout = LayoutElements.concatenate(
        (
            extracted_layout.slice(extracted_to_keep),
            inferred_layout_to_proc.slice(inferred_to_keep),
        )
    )
    return final_layout


def get_coords_from_bboxes(bboxes, round_to: int = DEFAULT_ROUND) -> np.ndarray:
    """convert a list of boxes's coords into np array"""
    if isinstance(bboxes, np.ndarray):
        return bboxes.round(round_to)

    # preallocate memory
    coords = np.zeros((len(bboxes), 4), dtype=np.float32)

    for i, bbox in enumerate(bboxes):
        coords[i, :] = [bbox.x1, bbox.y1, bbox.x2, bbox.y2]

    return coords.round(round_to)


def areas_of_boxes_and_intersection_area(
    coords1: np.ndarray, coords2: np.ndarray, round_to: int = DEFAULT_ROUND
):
    """compute intersection area and own areas for two groups of bounding boxes"""
    x11, y11, x12, y12 = np.split(coords1, 4, axis=1)
    x21, y21, x22, y22 = np.split(coords2, 4, axis=1)

    inter_area = np.maximum(
        (np.minimum(x12, np.transpose(x22)) - np.maximum(x11, np.transpose(x21)) + 1), 0
    ) * np.maximum((np.minimum(y12, np.transpose(y22)) - np.maximum(y11, np.transpose(y21)) + 1), 0)
    boxa_area = (x12 - x11 + 1) * (y12 - y11 + 1)
    boxb_area = (x22 - x21 + 1) * (y22 - y21 + 1)

    return inter_area.round(round_to), boxa_area.round(round_to), boxb_area.round(round_to)


def bboxes1_is_almost_subregion_of_bboxes2(
    bboxes1, bboxes2, threshold: float = 0.5, round_to: int = DEFAULT_ROUND
) -> np.ndarray:
    """compute if each element from bboxes1 is almost a subregion of one or more elements in
    bboxes2"""
    coords1 = get_coords_from_bboxes(bboxes1, round_to=round_to)
    coords2 = get_coords_from_bboxes(bboxes2, round_to=round_to)

    inter_area, boxa_area, boxb_area = areas_of_boxes_and_intersection_area(
        coords1, coords2, round_to=round_to
    )

    return (inter_area / np.maximum(boxa_area, EPSILON_AREA) > threshold) & (
        boxa_area <= boxb_area.T
    )


def boxes_self_iou(bboxes, threshold: float = 0.5, round_to: int = DEFAULT_ROUND) -> np.ndarray:
    """compute iou for a group of elements"""
    # only store one copy of coords in memory instead of calling get coords twice
    coords = get_coords_from_bboxes(bboxes, round_to=round_to)

    return boxes_iou(coords, coords, threshold, round_to)


# TODO (yao): move those vector math utils into a separated sub module to void import issues
def boxes_iou(
    bboxes1, bboxes2, threshold: float = 0.75, round_to: int = DEFAULT_ROUND
) -> np.ndarray:
    """compute iou between two groups of elements"""
    coords1 = get_coords_from_bboxes(bboxes1, round_to=round_to)
    coords2 = get_coords_from_bboxes(bboxes2, round_to=round_to)

    inter_area, boxa_area, boxb_area = areas_of_boxes_and_intersection_area(
        coords1, coords2, round_to=round_to
    )
    denom = np.maximum(EPSILON_AREA, boxa_area + boxb_area.T - inter_area)
    # Instead of (x/y) > t, use x > t*y for memory & speed with same result
    return inter_area > (threshold * denom)


@requires_dependencies("unstructured_inference")
def merge_inferred_with_extracted_layout(
    inferred_document_layout: "DocumentLayout",
    extracted_layout: List[TextRegions],
    hi_res_model_name: str,
) -> "DocumentLayout":
    """Merge an inferred layout with an extracted layout"""

    from unstructured_inference.models.detectron2onnx import UnstructuredDetectronONNXModel

    inferred_pages = inferred_document_layout.pages
    for i, (inferred_page, extracted_page_layout) in enumerate(
        zip(inferred_pages, extracted_layout)
    ):
        image_metadata = inferred_page.image_metadata
        w = image_metadata.get("width")
        h = image_metadata.get("height")
        image_size = (w, h)

        threshold_kwargs = {}
        # NOTE(Benjamin): With this the thresholds are only changed for detextron2_mask_rcnn
        # In other case the default values for the functions are used
        if (
            isinstance(inferred_page.detection_model, UnstructuredDetectronONNXModel)
            and "R_50" not in inferred_page.detection_model.model_path
        ):
            threshold_kwargs = {"same_region_threshold": 0.5, "subregion_threshold": 0.5}

        # NOTE (yao): after refactoring the algorithm to be vectorized we can then pass in the
        # vectorized data structure into the merge function

        merged_layout = array_merge_inferred_layout_with_extracted_layout(
            inferred_page.elements_array,
            extracted_page_layout,
            page_image_size=image_size,
            **threshold_kwargs,
        )

        merged_layout = sort_text_regions(merged_layout, SORT_MODE_BASIC)
        # so that we can modify the text without worrying about hitting length limit
        merged_layout.texts = merged_layout.texts.astype(object)
        merged_layout.is_extracted_array = merged_layout.is_extracted_array.astype(object)
        for i, text in enumerate(merged_layout.texts):
            if text is None:
                text, is_extracted = aggregate_embedded_text_by_block(
                    target_region=merged_layout.slice([i]),
                    source_regions=extracted_page_layout,
                )
                if merged_layout.element_class_id_map[merged_layout.element_class_ids[i]] not in (
                    "Image",
                    "Picture",
                ):
                    merged_layout.is_extracted_array[i] = is_extracted
            merged_layout.texts[i] = remove_control_characters(text)

        inferred_page.elements_array = merged_layout

    return inferred_document_layout


def clean_pdf_extracted_inner_elements(document: "DocumentLayout") -> "DocumentLayout":
    """Clean extracted PDF elements from inside tables.

    This function removes elements sourced from PDF extraction that are subregions within table
    elements.
    """

    for page in document.pages:
        extracted_mask = np.isin(
            page.elements_array.sources,
            [Source.CORE_PDF],
        )
        non_extracted_element_boxes = page.elements_array.slice(~extracted_mask).element_coords
        extracted_element_boxes = page.elements_array.slice(extracted_mask).element_coords

        if len(extracted_element_boxes) == 0 or len(non_extracted_element_boxes) == 0:
            continue

        is_element_subregion_of_other_elements = (
            bboxes1_is_almost_subregion_of_bboxes2(
                extracted_element_boxes,
                non_extracted_element_boxes,
                env_config.EMBEDDED_TEXT_AGGREGATION_SUBREGION_THRESHOLD,
            ).sum(axis=1)
            == 1
        )

        extracted_to_keep = np.where(extracted_mask)[0][~is_element_subregion_of_other_elements]
        page.elements_array = page.elements_array.slice(
            np.sort(np.concatenate((np.where(~extracted_mask)[0], extracted_to_keep)))
        )

    return document


@requires_dependencies("unstructured_inference")
def remove_duplicate_elements(
    elements: TextRegions,
    threshold: float = 0.5,
) -> TextRegions:
    """Removes duplicate extracted text elements from a document layout."""

    coords = elements.element_coords
    # experiments show 2e3 is the block size that constrains the peak memory around 1Gb for this
    # function; that accounts for all the intermediate matricies allocated and memory for storing
    # final results
    memory_cap_in_gb = float(os.getenv("UNST_MATMUL_MEMORY_CAP_IN_GB", 1))
    if memory_cap_in_gb <= 0:
        raise ValueError("UNST_MATMUL_MEMORY_CAP_IN_GB must be > 0")
    n_split = np.ceil(coords.shape[0] / 2e3 / memory_cap_in_gb)
    splits = np.array_split(coords, n_split, axis=0)

    # A box is dropped only when it near-duplicates a *later* box (higher global index) -- the
    # strict upper triangle of the full IoU matrix. Each split is a contiguous block of rows
    # compared against all coords, so the triangle's diagonal must be offset by the split's
    # global start index; otherwise rows in later splits match themselves (and earlier boxes)
    # and get wrongly removed, decimating dense pages (> 2000 elements).
    keep_masks = []
    offset = 0
    for split in splits:
        iou = boxes_iou(split, coords, threshold)
        keep_masks.append(~np.triu(iou, k=1 + offset).any(axis=1))
        offset += split.shape[0]
    return elements.slice(np.concatenate(keep_masks))


def _aggregated_iou(box1s, box2):
    intersection = 0.0
    sum_areas = calculate_bbox_area(box2)

    for i in range(box1s.shape[0]):
        intersection += calculate_intersection_area(box1s[i, :], box2)
        sum_areas += calculate_bbox_area(box1s[i, :])

    union = sum_areas - intersection

    if union == 0:
        return 1.0
    return intersection / union


def aggregate_embedded_text_by_block(
    target_region: TextRegions,
    source_regions: TextRegions,
    subregion_threshold: float = env_config.EMBEDDED_TEXT_AGGREGATION_SUBREGION_THRESHOLD,
    text_coverage_threshold: float = env_config.TEXT_COVERAGE_THRESHOLD,
) -> tuple[str, IsExtracted | None]:
    """Extracts the text aggregated from the elements of the given layout that lie within the given
    block."""

    if len(source_regions) == 0 or len(target_region) == 0:
        return "", None

    mask = (
        bboxes1_is_almost_subregion_of_bboxes2(
            source_regions.element_coords,
            target_region.element_coords,
            subregion_threshold,
        )
        .sum(axis=1)
        .astype(bool)
    )

    text = " ".join([text for text in source_regions.slice(mask).texts if text])

    if sum(mask):
        source_bboxes = source_regions.slice(mask).element_coords
        target_bboxes = target_region.element_coords

        iou = _aggregated_iou(source_bboxes, target_bboxes[0, :])

        fully_filled = (
            all(flag == IsExtracted.TRUE for flag in source_regions.slice(mask).is_extracted_array)
            and iou > text_coverage_threshold
        )
        is_extracted = IsExtracted.TRUE if fully_filled else IsExtracted.PARTIAL
    else:
        # if nothing is sliced then it is not extracted
        is_extracted = IsExtracted.FALSE
    return text, is_extracted


def get_links_in_element(page_links: list, region: Rectangle) -> list:
    links_bboxes = [Rectangle(*link.get("bbox")) for link in page_links]
    results = bboxes1_is_almost_subregion_of_bboxes2(links_bboxes, [region])
    links = [
        {
            "text": page_links[idx].get("text"),
            "url": page_links[idx].get("url"),
            "start_index": page_links[idx].get("start_index"),
        }
        for idx, result in enumerate(results)
        if any(result)
    ]

    return links


def calculate_intersection_area(
    bbox1: tuple[float, float, float, float],
    bbox2: tuple[float, float, float, float],
) -> float:
    """
    Calculate the area of intersection between two bounding boxes.

    Args:
        bbox1 (tuple[float, float, float, float]): The coordinates of the first bounding box
            in the format (x1, y1, x2, y2).
        bbox2 (tuple[float, float, float, float]): The coordinates of the second bounding box
            in the format (x1, y1, x2, y2).

    Returns:
        float: The area of intersection between the two bounding boxes. If there is no
        intersection, the function returns 0.0.
    """
    x1_1, y1_1, x2_1, y2_1 = bbox1
    x1_2, y1_2, x2_2, y2_2 = bbox2

    x_intersection = max(x1_1, x1_2)
    y_intersection = max(y1_1, y1_2)
    x2_intersection = min(x2_1, x2_2)
    y2_intersection = min(y2_1, y2_2)

    if x_intersection < x2_intersection and y_intersection < y2_intersection:
        intersection_area = calculate_bbox_area(
            (x_intersection, y_intersection, x2_intersection, y2_intersection),
        )
        return intersection_area
    else:
        return 0.0


def calculate_bbox_area(bbox: tuple[float, float, float, float]) -> float:
    """
    Calculate the area of a bounding box.

    Args:
        bbox (tuple[float, float, float, float]): The coordinates of the bounding box
            in the format (x1, y1, x2, y2).

    Returns:
        float: The area of the bounding box, computed as the product of its width and height.
    """
    x1, y1, x2, y2 = bbox
    area = (x2 - x1) * (y2 - y1)
    return area
