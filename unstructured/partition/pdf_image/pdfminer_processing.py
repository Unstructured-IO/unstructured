from typing import TYPE_CHECKING, BinaryIO, List, Optional, Union, cast

import numpy as np
from pdfminer.utils import open_filename

from unstructured.partition.pdf_image.pdf_image_utils import remove_control_characters
from unstructured.partition.pdf_image.pdfminer_utils import (
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
    from unstructured_inference.inference.elements import TextRegion
    from unstructured_inference.inference.layout import DocumentLayout


EPSILON_AREA = 0.01
# rounding floating point to nearest machine precision
DEFAULT_ROUND = 15


def process_file_with_pdfminer(
    filename: str = "",
    dpi: int = 200,
) -> List[List["TextRegion"]]:
    with open_filename(filename, "rb") as fp:
        fp = cast(BinaryIO, fp)
        extracted_layout = process_data_with_pdfminer(
            file=fp,
            dpi=dpi,
        )
        return extracted_layout


@requires_dependencies("unstructured_inference")
def process_data_with_pdfminer(
    file: Optional[Union[bytes, BinaryIO]] = None,
    dpi: int = 200,
) -> List[List["TextRegion"]]:
    """Loads the image and word objects from a pdf using pdfplumber and the image renderings of the
    pdf pages using pdf2image"""

    from unstructured_inference.inference.elements import (
        EmbeddedTextRegion,
        ImageTextRegion,
    )

    layouts = []
    # Coefficient to rescale bounding box to be compatible with images
    coef = dpi / 72
    for page, page_layout in open_pdfminer_pages_generator(file):
        height = page_layout.height

        text_layout = []
        image_layout = []
        for obj in page_layout:
            if hasattr(obj, "get_text"):
                inner_text_objects = extract_text_objects(obj)
                for inner_obj in inner_text_objects:
                    _text = inner_obj.get_text()
                    text_region = _create_text_region(
                        *rect_to_bbox(inner_obj.bbox, height),
                        coef,
                        _text,
                        Source.PDFMINER,
                        EmbeddedTextRegion,
                    )
                    if text_region.bbox is not None and text_region.bbox.area > 0:
                        text_layout.append(text_region)
            else:
                inner_image_objects = extract_image_objects(obj)
                for img_obj in inner_image_objects:
                    text_region = _create_text_region(
                        *rect_to_bbox(img_obj.bbox, height),
                        coef,
                        None,
                        Source.PDFMINER,
                        ImageTextRegion,
                    )
                    if text_region.bbox is not None and text_region.bbox.area > 0:
                        image_layout.append(text_region)

        clean_text_layout = remove_duplicate_elements(
            text_layout, env_config.EMBEDDED_TEXT_SAME_REGION_THRESHOLD
        )
        clean_image_layout = remove_duplicate_elements(
            image_layout, env_config.EMBEDDED_IMAGE_SAME_REGION_THRESHOLD
        )
        layout = [*clean_text_layout, *clean_image_layout]
        # NOTE(christine): always do the basic sort first for deterministic order across
        # python versions.
        layout = sort_text_regions(layout, SORT_MODE_BASIC)

        # apply the current default sorting to the layout elements extracted by pdfminer
        layout = sort_text_regions(layout)

        layouts.append(layout)

    return layouts


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
    coords = get_coords_from_bboxes(bboxes, round_to=round_to)

    inter_area, boxa_area, boxb_area = areas_of_boxes_and_intersection_area(
        coords, coords, round_to=round_to
    )

    return (inter_area / np.maximum(EPSILON_AREA, boxa_area + boxb_area.T - inter_area)) > threshold


@requires_dependencies("unstructured_inference")
def merge_inferred_with_extracted_layout(
    inferred_document_layout: "DocumentLayout",
    extracted_layout: List[List["TextRegion"]],
    hi_res_model_name: str,
) -> "DocumentLayout":
    """Merge an inferred layout with an extracted layout"""

    from unstructured_inference.inference.layoutelement import (
        merge_inferred_layout_with_extracted_layout as merge_inferred_with_extracted_page,
    )
    from unstructured_inference.models.detectron2onnx import UnstructuredDetectronONNXModel

    inferred_pages = inferred_document_layout.pages
    for i, (inferred_page, extracted_page_layout) in enumerate(
        zip(inferred_pages, extracted_layout)
    ):
        inferred_layout = inferred_page.elements
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

        merged_layout = merge_inferred_with_extracted_page(
            inferred_layout=inferred_layout,
            extracted_layout=extracted_page_layout,
            page_image_size=image_size,
            **threshold_kwargs,
        )

        merged_layout = sort_text_regions(cast(List["TextRegion"], merged_layout), SORT_MODE_BASIC)

        elements = []
        for layout_el in merged_layout:
            if layout_el.text is None:
                text = aggregate_embedded_text_by_block(
                    text_region=cast("TextRegion", layout_el),
                    pdf_objects=extracted_page_layout,
                )
            else:
                text = layout_el.text
            layout_el.text = remove_control_characters(text)
            elements.append(layout_el)

        inferred_page.elements[:] = elements

    return inferred_document_layout


def clean_pdfminer_inner_elements(document: "DocumentLayout") -> "DocumentLayout":
    """Clean pdfminer elements from inside tables.

    This function removes elements sourced from PDFMiner that are subregions within table elements.
    """

    for page in document.pages:
        non_pdfminer_element_boxes = [e.bbox for e in page.elements if e.source != Source.PDFMINER]
        element_boxes = []
        element_to_subregion_map = {}
        subregion_indice = 0
        for i, element in enumerate(page.elements):
            if element.source != Source.PDFMINER:
                continue
            element_boxes.append(element.bbox)
            element_to_subregion_map[i] = subregion_indice
            subregion_indice += 1

        is_element_subregion_of_other_elements = (
            bboxes1_is_almost_subregion_of_bboxes2(
                element_boxes,
                non_pdfminer_element_boxes,
                env_config.EMBEDDED_TEXT_AGGREGATION_SUBREGION_THRESHOLD,
            ).sum(axis=1)
            == 1
        )

        page.elements = [
            e
            for i, e in enumerate(page.elements)
            if (
                (i not in element_to_subregion_map)
                or not is_element_subregion_of_other_elements[element_to_subregion_map[i]]
            )
        ]

    return document


@requires_dependencies("unstructured_inference")
def remove_duplicate_elements(
    elements: list["TextRegion"],
    threshold: float = 0.5,
) -> list["TextRegion"]:
    """Removes duplicate text elements extracted by PDFMiner from a document layout."""

    bboxes = []
    for i, element in enumerate(elements):
        bboxes.append(element.bbox)

    iou = boxes_self_iou(bboxes, threshold)

    filtered_elements = []
    for i, element in enumerate(elements):
        if iou[i, i + 1 :].any():
            continue
        filtered_elements.append(element)

    return filtered_elements


def aggregate_embedded_text_by_block(
    text_region: "TextRegion",
    pdf_objects: list["TextRegion"],
) -> str:
    """Extracts the text aggregated from the elements of the given layout that lie within the given
    block."""

    mask = bboxes1_is_almost_subregion_of_bboxes2(
        [obj.bbox for obj in pdf_objects],
        [text_region.bbox],
        env_config.EMBEDDED_TEXT_AGGREGATION_SUBREGION_THRESHOLD,
    ).sum(axis=1)

    text = " ".join([obj.text for i, obj in enumerate(pdf_objects) if (mask[i] and obj.text)])
    return text
