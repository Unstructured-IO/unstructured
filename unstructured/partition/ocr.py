import os
import tempfile
from pathlib import PurePath
from typing import Any, BinaryIO, Collection, List, Optional, Tuple, Union, cast

import pdf2image
import pytesseract
from pdfminer.high_level import extract_pages
from pdfminer.layout import LTContainer, LTImage
from PIL import Image, ImageSequence
from pytesseract import Output
from scipy.sparse.csgraph import connected_components
from unstructured_inference.inference.elements import (
    EmbeddedTextRegion,
    ImageTextRegion,
    Rectangle,
    TextRegion,
    intersections,
)
from unstructured_inference.inference.layoutelement import (
    LayoutElement,
)

from unstructured.logger import logger

SUBREGION_THRESHOLD_FOR_OCR = 0.5
ELEMENTS_V_PADDING_COEF = 0.3
ELEMENTS_H_PADDING_COEF = 0.4
LAYOUT_SAME_REGION_THRESHOLD = 0.75
LAYOUT_SUBREGION_THRESHOLD = 0.75
FULL_PAGE_REGION_THRESHOLD = 0.99


def process_data_with_ocr(
    data: Optional[Union[bytes, BinaryIO]],
    is_image: bool = False,
    ocr_languages: str = "eng",
    pdf_image_dpi: int = 200,
) -> List[List[TextRegion]]:
    with tempfile.NamedTemporaryFile() as tmp_file:
        tmp_file.write(data.read())
        tmp_file.flush()  #
        ocr_layouts, extracted_layouts = process_file_with_ocr(
            tmp_file.name,
            is_image=is_image,
            ocr_languages=ocr_languages,
            pdf_image_dpi=pdf_image_dpi,
        )
        return ocr_layouts, extracted_layouts


def process_file_with_ocr(
    filename: str = "",
    is_image: bool = False,
    ocr_languages: str = "eng",
    pdf_image_dpi: int = 200,
) -> List[List[TextRegion]]:
    if is_image:
        logger.info(f"Reading image file: {filename} ...")
        try:
            image = Image.open(filename)
            format = image.format
            images = []
            for im in ImageSequence.Iterator(image):
                im = im.convert("RGB")
                im.format = format
                images.append(im)
        except Exception as e:
            if os.path.isdir(filename) or os.path.isfile(filename):
                raise e
            else:
                raise FileNotFoundError(f'File "{filename}" not found!') from e
        ocr_layouts = []
        for image in images:
            ocr_data = pytesseract.image_to_data(
                image,
                lang=ocr_languages,
                output_type=Output.DICT,
            )
            ocr_layout = parse_ocr_data_tesseract(ocr_data)
            ocr_layouts.append(ocr_layout)
        return ocr_layouts, None
    else:
        logger.info(f"Reading PDF for file: {filename} ...")
        with tempfile.TemporaryDirectory() as temp_dir:
            extracted_layouts, _image_paths = load_pdf(
                filename,
                pdf_image_dpi,
                output_folder=temp_dir,
                path_only=True,
            )
            image_paths = cast(List[str], _image_paths)
            if len(extracted_layouts) > len(image_paths):
                raise RuntimeError(
                    "Some images were not loaded. "
                    "Check that poppler is installed and in your $PATH.",
                )
            for i, image_path in enumerate(image_paths):
                with Image.open(image_path) as image:
                    ocr_data = pytesseract.image_to_data(
                        image,
                        lang=ocr_languages,
                        output_type=Output.DICT,
                    )
                ocr_layout = parse_ocr_data_tesseract(ocr_data)
                ocr_layouts.append(ocr_layout)
        return ocr_layouts, extracted_layouts


def merge_layouts(infered_layouts, extracted_layouts, ocr_layouts):
    merged_layouts = []
    return merged_layouts


def load_pdf(
    filename: str,
    dpi: int = 200,
    output_folder: Optional[Union[str, PurePath]] = None,
    path_only: bool = False,
) -> Tuple[List[List[TextRegion]], Union[List[Image.Image], List[str]]]:
    """Loads the image and word objects from a pdf using pdfplumber and the image renderings of the
    pdf pages using pdf2image"""

    layouts = []
    for page in extract_pages(filename):
        layout: List[TextRegion] = []
        height = page.height
        for element in page:
            x1, y2, x2, y1 = element.bbox
            y1 = height - y1
            y2 = height - y2
            # Coefficient to rescale bounding box to be compatible with images
            coef = dpi / 72

            if hasattr(element, "get_text"):
                _text = element.get_text()
                element_class = EmbeddedTextRegion  # type: ignore
            else:
                embedded_images = get_images_from_pdf_element(element)
                if len(embedded_images) > 0:
                    _text = None
                    element_class = ImageTextRegion  # type: ignore
                else:
                    continue

            text_region = element_class(x1 * coef, y1 * coef, x2 * coef, y2 * coef, text=_text)

            if text_region.area > 0:
                layout.append(text_region)
        layouts.append(layout)

    if path_only and not output_folder:
        raise ValueError("output_folder must be specified if path_only is true")

    if output_folder is not None:
        images = pdf2image.convert_from_path(
            filename,
            dpi=dpi,
            output_folder=output_folder,
            paths_only=path_only,
        )
    else:
        images = pdf2image.convert_from_path(
            filename,
            dpi=dpi,
            paths_only=path_only,
        )

    return layouts, images


def get_images_from_pdf_element(layout_object: Any) -> List[LTImage]:
    """
    Recursively extracts LTImage objects from a PDF layout element.

    This function takes a PDF layout element (could be LTImage or LTContainer) and recursively
    extracts all LTImage objects contained within it.

    Parameters:
    - layout_object (Any): The PDF layout element to extract images from.

    Returns:
    - List[LTImage]: A list of LTImage objects extracted from the layout object.

    Note:
    - This function recursively traverses through the layout_object to find and accumulate all
     LTImage objects.
    - If the input layout_object is an LTImage, it will be included in the returned list.
    - If the input layout_object is an LTContainer, the function will recursively search its
     children for LTImage objects.
    - If the input layout_object is neither LTImage nor LTContainer, an empty list will be
     returned.
    """

    # recursively locate Image objects in layout_object
    if isinstance(layout_object, LTImage):
        return [layout_object]
    if isinstance(layout_object, LTContainer):
        img_list: List[LTImage] = []
        for child in layout_object:
            img_list = img_list + get_images_from_pdf_element(child)
        return img_list
    else:
        return []


def parse_ocr_data_tesseract(ocr_data: dict) -> List[TextRegion]:
    """
    Parse the OCR result data to extract a list of TextRegion objects from
    tesseract.

    The function processes the OCR result dictionary, looking for bounding
    box information and associated text to create instances of the TextRegion
    class, which are then appended to a list.

    Parameters:
    - ocr_data (dict): A dictionary containing the OCR result data, expected
                      to have keys like "level", "left", "top", "width",
                      "height", and "text".

    Returns:
    - List[TextRegion]: A list of TextRegion objects, each representing a
                        detected text region within the OCR-ed image.

    Note:
    - An empty string or a None value for the 'text' key in the input
      dictionary will result in its associated bounding box being ignored.
    """

    levels = ocr_data["level"]
    text_regions = []
    for i, level in enumerate(levels):
        (l, t, w, h) = (
            ocr_data["left"][i],
            ocr_data["top"][i],
            ocr_data["width"][i],
            ocr_data["height"][i],
        )
        (x1, y1, x2, y2) = l, t, l + w, t + h
        text = ocr_data["text"][i]
        if text:
            text_region = TextRegion(x1, y1, x2, y2, text=text, source="OCR")
            text_regions.append(text_region)

    return text_regions


def merge_inferred_layout_with_extracted_layout(
    inferred_layout: Collection[LayoutElement],
    extracted_layout: Collection[TextRegion],
    page_image_size: tuple,
    ocr_layout: Optional[List[TextRegion]] = None,
    supplement_with_ocr_elements: bool = True,
    same_region_threshold: float = LAYOUT_SAME_REGION_THRESHOLD,
    subregion_threshold: float = LAYOUT_SUBREGION_THRESHOLD,
) -> List[LayoutElement]:
    """Merge two layouts to produce a single layout."""
    extracted_elements_to_add: List[TextRegion] = []
    inferred_regions_to_remove = []
    w, h = page_image_size
    full_page_region = Rectangle(0, 0, w, h)
    for extracted_region in extracted_layout:
        extracted_is_image = isinstance(extracted_region, ImageTextRegion)
        if extracted_is_image:
            # Skip extracted images for this purpose, we don't have the text from them and they
            # don't provide good text bounding boxes.

            is_full_page_image = region_bounding_boxes_are_almost_the_same(
                extracted_region,
                full_page_region,
                FULL_PAGE_REGION_THRESHOLD,
            )

            if is_full_page_image:
                continue
        region_matched = False
        for inferred_region in inferred_layout:
            if inferred_region.intersects(extracted_region):
                same_bbox = region_bounding_boxes_are_almost_the_same(
                    inferred_region,
                    extracted_region,
                    same_region_threshold,
                )
                inferred_is_subregion_of_extracted = inferred_region.is_almost_subregion_of(
                    extracted_region,
                    subregion_threshold=subregion_threshold,
                )
                inferred_is_text = inferred_region.type not in (
                    "Figure",
                    "Image",
                    "PageBreak",
                    "Table",
                )
                extracted_is_subregion_of_inferred = extracted_region.is_almost_subregion_of(
                    inferred_region,
                    subregion_threshold=subregion_threshold,
                )
                either_region_is_subregion_of_other = (
                    inferred_is_subregion_of_extracted or extracted_is_subregion_of_inferred
                )
                if same_bbox:
                    # Looks like these represent the same region
                    grow_region_to_match_region(inferred_region, extracted_region)
                    inferred_region.text = extracted_region.text
                    region_matched = True
                elif extracted_is_subregion_of_inferred and inferred_is_text and extracted_is_image:
                    grow_region_to_match_region(inferred_region, extracted_region)
                    region_matched = True
                elif either_region_is_subregion_of_other and inferred_region.type != "Table":
                    inferred_regions_to_remove.append(inferred_region)
        if not region_matched:
            extracted_elements_to_add.append(extracted_region)
    # Need to classify the extracted layout elements we're keeping.
    categorized_extracted_elements_to_add = [
        LayoutElement(
            el.x1,
            el.y1,
            el.x2,
            el.y2,
            text=el.text,
            type="Image" if isinstance(el, ImageTextRegion) else "UncategorizedText",
            source=el.source,
        )
        for el in extracted_elements_to_add
    ]
    inferred_regions_to_add = [
        region for region in inferred_layout if region not in inferred_regions_to_remove
    ]
    inferred_regions_to_add_without_text = [
        region for region in inferred_regions_to_add if not region.text
    ]
    if ocr_layout is not None:
        for inferred_region in inferred_regions_to_add_without_text:
            inferred_region.text = aggregate_ocr_text_by_block(
                ocr_layout,
                inferred_region,
                SUBREGION_THRESHOLD_FOR_OCR,
            )
        out_layout = categorized_extracted_elements_to_add + inferred_regions_to_add
        final_layout = (
            supplement_layout_with_ocr_elements(out_layout, ocr_layout)
            if supplement_with_ocr_elements
            else out_layout
        )
    else:
        final_layout = categorized_extracted_elements_to_add + inferred_regions_to_add

    return final_layout


def region_bounding_boxes_are_almost_the_same(
    region1: Rectangle,
    region2: Rectangle,
    same_region_threshold: float = 0.75,
) -> bool:
    """Returns whether bounding boxes are almost the same. This is determined by checking if the
    intersection over union is above some threshold."""
    return region1.intersection_over_union(region2) > same_region_threshold


def grow_region_to_match_region(region_to_grow: Rectangle, region_to_match: Rectangle):
    """Grows a region to the minimum size necessary to contain both regions."""
    (new_x1, new_y1), _, (new_x2, new_y2), _ = minimal_containing_region(
        region_to_grow,
        region_to_match,
    ).coordinates
    region_to_grow.x1, region_to_grow.y1, region_to_grow.x2, region_to_grow.y2 = (
        new_x1,
        new_y1,
        new_x2,
        new_y2,
    )


def minimal_containing_region(*regions: Rectangle) -> Rectangle:
    """Returns the smallest rectangular region that contains all regions passed"""
    x1 = min(region.x1 for region in regions)
    y1 = min(region.y1 for region in regions)
    x2 = max(region.x2 for region in regions)
    y2 = max(region.y2 for region in regions)

    return Rectangle(x1, y1, x2, y2)


def merge_inferred_layout_with_ocr_layout(
    inferred_layout: List[LayoutElement],
    ocr_layout: List[TextRegion],
    supplement_with_ocr_elements: bool = True,
) -> List[LayoutElement]:
    """
    Merge the inferred layout with the OCR-detected text regions.

    This function iterates over each inferred layout element and aggregates the
    associated text from the OCR layout using the specified threshold. The inferred
    layout's text attribute is then updated with this aggregated text.
    """

    for inferred_region in inferred_layout:
        inferred_region.text = aggregate_ocr_text_by_block(
            ocr_layout,
            inferred_region,
            SUBREGION_THRESHOLD_FOR_OCR,
        )

    final_layout = (
        supplement_layout_with_ocr_elements(inferred_layout, ocr_layout)
        if supplement_with_ocr_elements
        else inferred_layout
    )

    return final_layout


def aggregate_ocr_text_by_block(
    ocr_layout: List[TextRegion],
    region: TextRegion,
    subregion_threshold: float,
) -> Optional[str]:
    """Extracts the text aggregated from the regions of the ocr layout that lie within the given
    block."""

    extracted_texts = []

    for ocr_region in ocr_layout:
        ocr_region_is_subregion_of_given_region = ocr_region.is_almost_subregion_of(
            region,
            subregion_threshold=subregion_threshold,
        )
        if ocr_region_is_subregion_of_given_region and ocr_region.text:
            extracted_texts.append(ocr_region.text)

    return " ".join(extracted_texts) if extracted_texts else None


def supplement_layout_with_ocr_elements(
    layout: List[LayoutElement],
    ocr_layout: List[TextRegion],
) -> List[LayoutElement]:
    """
    Supplement the existing layout with additional OCR-derived elements.

    This function takes two lists: one list of pre-existing layout elements (`layout`)
    and another list of OCR-detected text regions (`ocr_layout`). It identifies OCR regions
    that are subregions of the elements in the existing layout and removes them from the
    OCR-derived list. Then, it appends the remaining OCR-derived regions to the existing layout.

    Parameters:
    - layout (List[LayoutElement]): A list of existing layout elements, each of which is
                                    an instance of `LayoutElement`.
    - ocr_layout (List[TextRegion]): A list of OCR-derived text regions, each of which is
                                     an instance of `TextRegion`.

    Returns:
    - List[LayoutElement]: The final combined layout consisting of both the original layout
                           elements and the new OCR-derived elements.

    Note:
    - The function relies on `is_almost_subregion_of()` method to determine if an OCR region
      is a subregion of an existing layout element.
    - It also relies on `get_elements_from_ocr_regions()` to convert OCR regions to layout elements.
    - The `SUBREGION_THRESHOLD_FOR_OCR` constant is used to specify the subregion matching
     threshold.
    """

    ocr_regions_to_remove = []
    for ocr_region in ocr_layout:
        for el in layout:
            ocr_region_is_subregion_of_out_el = ocr_region.is_almost_subregion_of(
                cast(Rectangle, el),
                SUBREGION_THRESHOLD_FOR_OCR,
            )
            if ocr_region_is_subregion_of_out_el:
                ocr_regions_to_remove.append(ocr_region)
                break

    ocr_regions_to_add = [region for region in ocr_layout if region not in ocr_regions_to_remove]
    if ocr_regions_to_add:
        ocr_elements_to_add = get_elements_from_ocr_regions(ocr_regions_to_add)
        final_layout = layout + ocr_elements_to_add
    else:
        final_layout = layout

    return final_layout


def get_elements_from_ocr_regions(ocr_regions: List[TextRegion]) -> List[LayoutElement]:
    """
    Get layout elements from OCR regions
    """

    grouped_regions = cast(
        List[List[TextRegion]],
        partition_groups_from_regions(ocr_regions),
    )
    merged_regions = [merge_text_regions(group) for group in grouped_regions]
    return [
        LayoutElement(
            r.x1,
            r.y1,
            r.x2,
            r.y2,
            text=r.text,
            source=None,
            type="UncategorizedText",
        )
        for r in merged_regions
    ]


def partition_groups_from_regions(regions: Collection[Rectangle]) -> List[List[Rectangle]]:
    """Partitions regions into groups of regions based on proximity. Returns list of lists of
    regions, each list corresponding with a group"""
    if len(regions) == 0:
        return []
    padded_regions = [
        r.vpad(r.height * ELEMENTS_V_PADDING_COEF).hpad(
            r.height * ELEMENTS_H_PADDING_COEF,
        )
        for r in regions
    ]

    intersection_mtx = intersections(*padded_regions)

    _, group_nums = connected_components(intersection_mtx)
    groups: List[List[Rectangle]] = [[] for _ in range(max(group_nums) + 1)]
    for region, group_num in zip(regions, group_nums):
        groups[group_num].append(region)

    return groups


def merge_text_regions(regions: List[TextRegion]) -> TextRegion:
    """
    Merge a list of TextRegion objects into a single TextRegion.

    Parameters:
    - group (List[TextRegion]): A list of TextRegion objects to be merged.

    Returns:
    - TextRegion: A single merged TextRegion object.
    """

    min_x1 = min([tr.x1 for tr in regions])
    min_y1 = min([tr.y1 for tr in regions])
    max_x2 = max([tr.x2 for tr in regions])
    max_y2 = max([tr.y2 for tr in regions])

    merged_text = " ".join([tr.text for tr in regions if tr.text])
    sources = [*{tr.source for tr in regions}]
    source = sources.pop() if len(sources) == 1 else "merged:".join(sources)  # type:ignore
    return TextRegion(min_x1, min_y1, max_x2, max_y2, source=source, text=merged_text)
