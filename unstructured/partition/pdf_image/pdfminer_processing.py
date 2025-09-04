from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any, BinaryIO, Iterable, List, Optional, Union, cast

import numpy as np
from pdfminer.layout import LTChar, LTTextBox
from pdfminer.pdftypes import PDFObjRef
from pdfminer.utils import open_filename
from unstructured_inference.config import inference_config
from unstructured_inference.constants import FULL_PAGE_REGION_THRESHOLD
from unstructured_inference.inference.elements import Rectangle

from unstructured.documents.coordinates import PixelSpace, PointSpace
from unstructured.documents.elements import CoordinatesMetadata, ElementType
from unstructured.partition.pdf_image.pdf_image_utils import remove_control_characters
from unstructured.partition.pdf_image.pdfminer_utils import (
    PDFMinerConfig,
    extract_image_objects,
    extract_text_objects,
    open_pdfminer_pages_generator,
    rect_to_bbox,
)
from unstructured.partition.utils.config import env_config
from unstructured.partition.utils.constants import SORT_MODE_BASIC, Source
from unstructured.partition.utils.sorting import sort_text_regions
from unstructured.utils import requires_dependencies

if TYPE_CHECKING:
    from unstructured_inference.inference.elements import TextRegion, TextRegions
    from unstructured_inference.inference.layout import DocumentLayout
    from unstructured_inference.inference.layoutelement import LayoutElements


EPSILON_AREA = 0.01
# rounding floating point to nearest machine precision
DEFAULT_ROUND = 15


def process_file_with_pdfminer(
    filename: str = "",
    dpi: int = 200,
    password: Optional[str] = None,
    pdfminer_config: Optional[PDFMinerConfig] = None,
) -> tuple[List[List["TextRegion"]], List[List]]:
    with open_filename(filename, "rb") as fp:
        fp = cast(BinaryIO, fp)
        extracted_layout, layouts_links = process_data_with_pdfminer(
            file=fp, dpi=dpi, password=password, pdfminer_config=pdfminer_config
        )
        return extracted_layout, layouts_links


def _validate_bbox(bbox: list[int | float]) -> bool:
    return all(x is not None for x in bbox) and (bbox[2] - bbox[0] > 0) and (bbox[3] - bbox[1] > 0)


def _minimum_containing_coords(*regions: TextRegions) -> np.ndarray:
    # TODO: refactor to just use np array as input
    return np.vstack(
        (
            np.min([region.x1 for region in regions], axis=0),
            np.min([region.y1 for region in regions], axis=0),
            np.max([region.x2 for region in regions], axis=0),
            np.max([region.y2 for region in regions], axis=0),
        )
    ).T


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
    extracted_almost_the_same_as_inferred = boxes_almost_same.sum(axis=1).astype(bool)
    # NOTE: if a row is full of False the argmax returns first index; we use the mask above to
    # distinguish those (they would be False in the mask)
    first_match = np.argmax(boxes_almost_same, axis=1)
    inferred_indices_to_update = first_match[extracted_almost_the_same_as_inferred]
    extracted_to_remove = extracted_layout.slice(extracted_almost_the_same_as_inferred)
    # copy here in case we change the extracted layout later
    inferred_layout.texts[inferred_indices_to_update] = extracted_to_remove.texts.copy()
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
    # NOTE (yao): what if od model detects table but pdfminer says image -> we would lose the table
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
    # pdfminer for bounding box
    extracted_to_remove = _merge_extracted_into_inferred_when_almost_the_same(
        extracted_text_layouts,
        inferred_layout_to_proc,
        same_region_threshold,
    )

    # ==== RULE 3. if extracted is subregion of an inferrred text region:
    # remove extracted and keep inferred;
    # expand inferred bounding box if needed to encompass all subregion extracted boxes
    # NOTE (yao):
    # currently this rule can fail to capture almost overlaps of two text regions when the pdfminer
    # has larger bounding boxes (in area). It might be worth it to use simpler IOU thresholding or
    # use the minimum of the two areas when computing sub regions
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
    if any(extracted_to_keep):
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


@requires_dependencies("unstructured_inference")
def process_page_layout_from_pdfminer(
    annotation_list: list,
    page_layout,
    page_height: int | float,
    page_number: int,
    coord_coef: float,
) -> tuple[LayoutElements, list]:
    from unstructured_inference.inference.layoutelement import LayoutElements

    urls_metadata: list[dict[str, Any]] = []
    element_coords, texts, element_class = [], [], []
    annotation_threshold = env_config.PDF_ANNOTATION_THRESHOLD

    for obj in page_layout:
        x1, y1, x2, y2 = rect_to_bbox(obj.bbox, page_height)
        bbox = (x1, y1, x2, y2)

        if len(annotation_list) > 0 and isinstance(obj, LTTextBox):
            annotations_within_element = check_annotations_within_element(
                annotation_list,
                bbox,
                page_number,
                annotation_threshold,
            )
            _, words = get_words_from_obj(obj, page_height)
            for annot in annotations_within_element:
                urls_metadata.append(map_bbox_and_index(words, annot))

        if hasattr(obj, "get_text"):
            inner_text_objects = extract_text_objects(obj)
            for inner_obj in inner_text_objects:
                inner_bbox = rect_to_bbox(inner_obj.bbox, page_height)
                if not _validate_bbox(inner_bbox):
                    continue
                texts.append(inner_obj.get_text())
                element_coords.append(inner_bbox)
                element_class.append(0)
        else:
            inner_image_objects = extract_image_objects(obj)
            for img_obj in inner_image_objects:
                inner_bbox = rect_to_bbox(img_obj.bbox, page_height)
                if not _validate_bbox(inner_bbox):
                    continue
                texts.append(None)
                element_coords.append(inner_bbox)
                element_class.append(1)

    return (
        LayoutElements(
            element_coords=coord_coef * np.array(element_coords),
            texts=np.array(texts).astype(object),
            element_class_ids=np.array(element_class),
            element_class_id_map={0: ElementType.UNCATEGORIZED_TEXT, 1: ElementType.IMAGE},
            sources=np.array([Source.PDFMINER] * len(element_class)),
        ),
        urls_metadata,
    )


@requires_dependencies("unstructured_inference")
def process_data_with_pdfminer(
    file: Optional[Union[bytes, BinaryIO]] = None,
    dpi: int = 200,
    password: Optional[str] = None,
    pdfminer_config: Optional[PDFMinerConfig] = None,
) -> tuple[List[LayoutElements], List[List]]:
    """Loads the image and word objects from a pdf using pdfplumber and the image renderings of the
    pdf pages using pdf2image"""

    from unstructured_inference.inference.layoutelement import LayoutElements

    layouts = []
    layouts_links = []
    # Coefficient to rescale bounding box to be compatible with images
    coef = dpi / 72
    for page_number, (page, page_layout) in enumerate(
        open_pdfminer_pages_generator(file, password=password, pdfminer_config=pdfminer_config)
    ):
        width, height = page_layout.width, page_layout.height

        annotation_list = []
        coordinate_system = PixelSpace(
            width=width,
            height=height,
        )
        if page.annots:
            annotation_list = get_uris(page.annots, height, coordinate_system, page_number)

        layout, urls_metadata = process_page_layout_from_pdfminer(
            annotation_list, page_layout, height, page_number, coef
        )

        links = [
            {
                "bbox": [x * coef for x in metadata["bbox"]],
                "text": metadata["text"],
                "url": metadata["uri"],
                "start_index": metadata["start_index"],
            }
            for metadata in urls_metadata
        ]

        clean_layouts = []
        for threshold, element_class in zip(
            (
                env_config.EMBEDDED_TEXT_SAME_REGION_THRESHOLD,
                env_config.EMBEDDED_IMAGE_SAME_REGION_THRESHOLD,
            ),
            (0, 1),
        ):
            elements_to_sort = layout.slice(layout.element_class_ids == element_class)
            clean_layouts.append(
                remove_duplicate_elements(elements_to_sort, threshold)
                if len(elements_to_sort)
                else elements_to_sort
            )

        layout = LayoutElements.concatenate(clean_layouts)
        # NOTE(christine): always do the basic sort first for deterministic order across
        # python versions.
        layout = sort_text_regions(layout, SORT_MODE_BASIC)

        # apply the current default sorting to the layout elements extracted by pdfminer
        layout = sort_text_regions(layout)

        layouts.append(layout)
        layouts_links.append(links)
    return layouts, layouts_links


def _create_text_region(x1, y1, x2, y2, coef, text, source, region_class):
    """Creates a text region of the specified class with scaled coordinates."""
    return region_class.from_coords(
        x1 * coef,
        y1 * coef,
        x2 * coef,
        y2 * coef,
        text=text,
        source=source,
    )


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
    return (inter_area / np.maximum(EPSILON_AREA, boxa_area + boxb_area.T - inter_area)) > threshold


@requires_dependencies("unstructured_inference")
def pdfminer_elements_to_text_regions(layout_elements: LayoutElements) -> list[TextRegions]:
    """a temporary solution to convert layout elements to a list of either EmbeddedTextRegion or
    ImageTextRegion; this should be made obsolete after we refactor the merging logic in inference
    library"""
    from unstructured_inference.inference.elements import (
        EmbeddedTextRegion,
        ImageTextRegion,
    )

    regions = []
    for i, element_class in enumerate(layout_elements.element_class_ids):
        region_class = EmbeddedTextRegion if element_class == 0 else ImageTextRegion
        regions.append(
            region_class.from_coords(
                *layout_elements.element_coords[i],
                text=layout_elements.texts[i],
                source=Source.PDFMINER,
            )
        )
    return regions


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

        for i, text in enumerate(merged_layout.texts):
            if text is None:
                text = aggregate_embedded_text_by_block(
                    target_region=merged_layout.slice([i]),
                    source_regions=extracted_page_layout,
                )
            merged_layout.texts[i] = remove_control_characters(text)

        inferred_page.elements_array = merged_layout

    return inferred_document_layout


def clean_pdfminer_inner_elements(document: "DocumentLayout") -> "DocumentLayout":
    """Clean pdfminer elements from inside tables.

    This function removes elements sourced from PDFMiner that are subregions within table elements.
    """

    for page in document.pages:
        pdfminer_mask = page.elements_array.sources == Source.PDFMINER
        non_pdfminer_element_boxes = page.elements_array.slice(~pdfminer_mask).element_coords
        pdfminer_element_boxes = page.elements_array.slice(pdfminer_mask).element_coords

        if len(pdfminer_element_boxes) == 0 or len(non_pdfminer_element_boxes) == 0:
            continue

        is_element_subregion_of_other_elements = (
            bboxes1_is_almost_subregion_of_bboxes2(
                pdfminer_element_boxes,
                non_pdfminer_element_boxes,
                env_config.EMBEDDED_TEXT_AGGREGATION_SUBREGION_THRESHOLD,
            ).sum(axis=1)
            == 1
        )

        pdfminer_to_keep = np.where(pdfminer_mask)[0][~is_element_subregion_of_other_elements]
        page.elements_array = page.elements_array.slice(
            np.sort(np.concatenate((np.where(~pdfminer_mask)[0], pdfminer_to_keep)))
        )

    return document


@requires_dependencies("unstructured_inference")
def remove_duplicate_elements(
    elements: TextRegions,
    threshold: float = 0.5,
) -> TextRegions:
    """Removes duplicate text elements extracted by PDFMiner from a document layout."""

    coords = elements.element_coords
    # experiments show 2e3 is the block size that constrains the peak memory around 1Gb for this
    # function; that accounts for all the intermediate matricies allocated and memory for storing
    # final results
    memory_cap_in_gb = os.getenv("UNST_MATMUL_MEMORY_CAP_IN_GB", 1)
    n_split = np.ceil(coords.shape[0] / 2e3 / memory_cap_in_gb)
    splits = np.array_split(coords, n_split, axis=0)

    ious = [~np.triu(boxes_iou(split, coords, threshold), k=1).any(axis=1) for split in splits]
    return elements.slice(np.concatenate(ious))


def aggregate_embedded_text_by_block(
    target_region: TextRegions,
    source_regions: TextRegions,
    threshold: float = env_config.EMBEDDED_TEXT_AGGREGATION_SUBREGION_THRESHOLD,
) -> str:
    """Extracts the text aggregated from the elements of the given layout that lie within the given
    block."""

    if len(source_regions) == 0 or len(target_region) == 0:
        return ""

    mask = (
        bboxes1_is_almost_subregion_of_bboxes2(
            source_regions.element_coords,
            target_region.element_coords,
            threshold,
        )
        .sum(axis=1)
        .astype(bool)
    )

    text = " ".join([text for text in source_regions.slice(mask).texts if text])
    return text


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


def get_uris(
    annots: PDFObjRef | list[PDFObjRef],
    height: float,
    coordinate_system: PixelSpace | PointSpace,
    page_number: int,
) -> list[dict[str, Any]]:
    """
    Extracts URI annotations from a single or a list of PDF object references on a specific page.
    The type of annots (list or not) depends on the pdf formatting. The function detectes the type
    of annots and then pass on to get_uris_from_annots function as a list.

    Args:
        annots (PDFObjRef | list[PDFObjRef]): A single or a list of PDF object references
            representing annotations on the page.
        height (float): The height of the page in the specified coordinate system.
        coordinate_system (PixelSpace | PointSpace): The coordinate system used to represent
            the annotations' coordinates.
        page_number (int): The page number from which to extract annotations.

    Returns:
        list[dict]: A list of dictionaries, each containing information about a URI annotation,
        including its coordinates, bounding box, type, URI link, and page number.
    """
    if isinstance(annots, list):
        return get_uris_from_annots(annots, height, coordinate_system, page_number)
    resolved_annots = annots.resolve()
    if resolved_annots is None:
        return []
    return get_uris_from_annots(resolved_annots, height, coordinate_system, page_number)


def get_uris_from_annots(
    annots: list[PDFObjRef],
    height: int | float,
    coordinate_system: PixelSpace | PointSpace,
    page_number: int,
) -> list[dict[str, Any]]:
    """
    Extracts URI annotations from a list of PDF object references.

    Args:
        annots (list[PDFObjRef]): A list of PDF object references representing annotations on
            a page.
        height (int | float): The height of the page in the specified coordinate system.
        coordinate_system (PixelSpace | PointSpace): The coordinate system used to represent
            the annotations' coordinates.
        page_number (int): The page number from which to extract annotations.

    Returns:
        list[dict]: A list of dictionaries, each containing information about a URI annotation,
        including its coordinates, bounding box, type, URI link, and page number.
    """
    annotation_list = []
    for annotation in annots:
        # Check annotation is valid for extraction
        annotation_dict = try_resolve(annotation)
        if not isinstance(annotation_dict, dict):
            continue
        subtype = annotation_dict.get("Subtype", None)
        if not subtype or isinstance(subtype, PDFObjRef) or str(subtype) != "/'Link'":
            continue
        # Extract bounding box and update coordinates
        rect = annotation_dict.get("Rect", None)
        if not rect or isinstance(rect, PDFObjRef) or len(rect) != 4:
            continue
        x1, y1, x2, y2 = rect_to_bbox(rect, height)
        points = ((x1, y1), (x1, y2), (x2, y2), (x2, y1))
        coordinates_metadata = CoordinatesMetadata(
            points=points,
            system=coordinate_system,
        )
        # Extract type
        if "A" not in annotation_dict:
            continue
        uri_dict = try_resolve(annotation_dict["A"])
        if not isinstance(uri_dict, dict):
            continue
        uri_type = None
        if "S" in uri_dict and not isinstance(uri_dict["S"], PDFObjRef):
            uri_type = str(uri_dict["S"])
        # Extract URI link
        uri = None
        try:
            if uri_type == "/'URI'":
                uri = try_resolve(try_resolve(uri_dict["URI"])).decode("utf-8")
            if uri_type == "/'GoTo'":
                uri = try_resolve(try_resolve(uri_dict["D"])).decode("utf-8")
        except Exception:
            pass

        annotation_list.append(
            {
                "coordinates": coordinates_metadata,
                "bbox": (x1, y1, x2, y2),
                "type": uri_type,
                "uri": uri,
                "page_number": page_number,
            },
        )
    return annotation_list


def try_resolve(annot: PDFObjRef):
    """
    Attempt to resolve a PDF object reference. If successful, returns the resolved object;
    otherwise, returns the original reference.
    """
    try:
        return annot.resolve()
    except Exception:
        return annot


def check_annotations_within_element(
    annotation_list: list[dict[str, Any]],
    element_bbox: tuple[float, float, float, float],
    page_number: int,
    annotation_threshold: float,
) -> list[dict[str, Any]]:
    """
    Filter annotations that are within or highly overlap with a specified element on a page.

    Args:
        annotation_list (list[dict[str,Any]]): A list of dictionaries, each containing information
            about an annotation.
        element_bbox (tuple[float, float, float, float]): The bounding box coordinates of the
            specified element in the bbox format (x1, y1, x2, y2).
        page_number (int): The page number to which the annotations and element belong.
        annotation_threshold (float, optional): The threshold value (between 0.0 and 1.0)
            that determines the minimum overlap required for an annotation to be considered
            within the element. Default is 0.9.

    Returns:
        list[dict[str,Any]]: A list of dictionaries containing information about annotations
        that are within or highly overlap with the specified element on the given page, based on
        the specified threshold.
    """
    annotations_within_element = []
    for annotation in annotation_list:
        if annotation["page_number"] == page_number:
            annotation_bbox_size = calculate_bbox_area(annotation["bbox"])
            if annotation_bbox_size and (
                calculate_intersection_area(element_bbox, annotation["bbox"]) / annotation_bbox_size
                > annotation_threshold
            ):
                annotations_within_element.append(annotation)
    return annotations_within_element


def get_words_from_obj(
    obj: LTTextBox,
    height: float,
) -> tuple[list[LTChar], list[dict[str, Any]]]:
    """
    Extracts characters and word bounding boxes from a PDF text element.

    Args:
        obj (LTTextBox): The PDF text element from which to extract characters and words.
        height (float): The height of the page in the specified coordinate system.

    Returns:
        tuple[list[LTChar], list[dict[str,Any]]]: A tuple containing two lists:
            - list[LTChar]: A list of LTChar objects representing individual characters.
            - list[dict[str,Any]]]: A list of dictionaries, each containing information about
                a word, including its text, bounding box, and start index in the element's text.
    """
    characters = []
    words = []
    text_len = 0

    for text_line in obj:
        word = ""
        x1, y1, x2, y2 = None, None, None, None
        start_index = 0
        for index, character in enumerate(text_line):
            if isinstance(character, LTChar):
                characters.append(character)
                char = character.get_text()

                if word and not char.strip():
                    words.append(
                        {"text": word, "bbox": (x1, y1, x2, y2), "start_index": start_index},
                    )
                    word = ""
                    continue

                # TODO(klaijan) - isalnum() only works with A-Z, a-z and 0-9
                # will need to switch to some pattern matching once we support more languages
                if not word:
                    isalnum = char.isalnum()
                if word and char.isalnum() != isalnum:
                    isalnum = char.isalnum()
                    words.append(
                        {"text": word, "bbox": (x1, y1, x2, y2), "start_index": start_index},
                    )
                    word = ""

                if len(word) == 0:
                    start_index = text_len + index
                    x1 = character.x0
                    y2 = height - character.y0
                    x2 = character.x1
                    y1 = height - character.y1
                else:
                    x2 = character.x1
                    y2 = height - character.y0

                word += char
            else:
                words.append(
                    {"text": word, "bbox": (x1, y1, x2, y2), "start_index": start_index},
                )
                word = ""
        text_len += len(text_line)
    return characters, words


def map_bbox_and_index(words: list[dict[str, Any]], annot: dict[str, Any]):
    """
    Maps a bounding box annotation to the corresponding text and start index within a list of words.

    Args:
        words (list[dict[str,Any]]): A list of dictionaries, each containing information about
            a word, including its text, bounding box, and start index.
        annot (dict[str,Any]): The annotation dictionary to be mapped, which will be updated with
        "text" and "start_index" fields.

    Returns:
        dict: The updated annotation dictionary with "text" representing the mapped text and
            "start_index" representing the start index of the mapped text in the list of words.
    """
    if len(words) == 0:
        annot["text"] = ""
        annot["start_index"] = -1
        return annot
    distance_from_bbox_start = np.sqrt(
        (annot["bbox"][0] - np.array([word["bbox"][0] for word in words])) ** 2
        + (annot["bbox"][1] - np.array([word["bbox"][1] for word in words])) ** 2,
    )
    distance_from_bbox_end = np.sqrt(
        (annot["bbox"][2] - np.array([word["bbox"][2] for word in words])) ** 2
        + (annot["bbox"][3] - np.array([word["bbox"][3] for word in words])) ** 2,
    )
    closest_start = try_argmin(distance_from_bbox_start)
    closest_end = try_argmin(distance_from_bbox_end)

    # NOTE(klaijan) - get the word from closest start only if the end index comes after start index
    text = ""
    if closest_end >= closest_start:
        for _ in range(closest_start, closest_end + 1):
            text += " "
            text += words[_]["text"]
    else:
        text = words[closest_start]["text"]

    annot["text"] = text.strip()
    annot["start_index"] = words[closest_start]["start_index"]
    return annot


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


def try_argmin(array: np.ndarray) -> int:
    """
    Attempt to find the index of the minimum value in a NumPy array.

    Args:
        array (np.ndarray): The NumPy array in which to find the minimum value's index.

    Returns:
        int: The index of the minimum value in the array. If the array is empty or an
        IndexError occurs, it returns -1.
    """
    try:
        return int(np.argmin(array))
    except IndexError:
        return -1
