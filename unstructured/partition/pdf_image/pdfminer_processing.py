from __future__ import annotations

from typing import TYPE_CHECKING, Any, BinaryIO, List, Optional, Union, cast

import numpy as np
from pdfminer.layout import LTChar, LTTextBox
from pdfminer.pdftypes import PDFObjRef
from pdfminer.utils import open_filename
from unstructured_inference.inference.elements import Rectangle

from unstructured.documents.coordinates import PixelSpace, PointSpace
from unstructured.documents.elements import CoordinatesMetadata
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
) -> tuple[List[List["TextRegion"]], List[List]]:
    with open_filename(filename, "rb") as fp:
        fp = cast(BinaryIO, fp)
        extracted_layout, layouts_links = process_data_with_pdfminer(
            file=fp,
            dpi=dpi,
        )
        return extracted_layout, layouts_links


@requires_dependencies("unstructured_inference")
def process_data_with_pdfminer(
    file: Optional[Union[bytes, BinaryIO]] = None,
    dpi: int = 200,
) -> tuple[List[List["TextRegion"]], List[List]]:
    """Loads the image and word objects from a pdf using pdfplumber and the image renderings of the
    pdf pages using pdf2image"""

    from unstructured_inference.inference.elements import (
        EmbeddedTextRegion,
        ImageTextRegion,
    )

    layouts = []
    layouts_links = []
    # Coefficient to rescale bounding box to be compatible with images
    coef = dpi / 72
    for page_number, (page, page_layout) in enumerate(open_pdfminer_pages_generator(file)):
        width, height = page_layout.width, page_layout.height

        text_layout = []
        image_layout = []
        annotation_list = []
        coordinate_system = PixelSpace(
            width=width,
            height=height,
        )
        if page.annots:
            annotation_list = get_uris(page.annots, height, coordinate_system, page_number)

        annotation_threshold = env_config.PDF_ANNOTATION_THRESHOLD
        urls_metadata: list[dict[str, Any]] = []

        for obj in page_layout:
            x1, y1, x2, y2 = rect_to_bbox(obj.bbox, height)
            bbox = (x1, y1, x2, y2)

            if len(annotation_list) > 0 and isinstance(obj, LTTextBox):
                annotations_within_element = check_annotations_within_element(
                    annotation_list,
                    bbox,
                    page_number,
                    annotation_threshold,
                )
                _, words = get_words_from_obj(obj, height)
                for annot in annotations_within_element:
                    urls_metadata.append(map_bbox_and_index(words, annot))

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
        links = [
            {
                "bbox": [x * coef for x in metadata["bbox"]],
                "text": metadata["text"],
                "url": metadata["uri"],
                "start_index": metadata["start_index"],
            }
            for metadata in urls_metadata
        ]

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
