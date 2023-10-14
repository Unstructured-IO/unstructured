import os
import tempfile
from copy import deepcopy
from typing import BinaryIO, List, Optional, Union, cast

import numpy as np
import pdf2image
import unstructured_pytesseract

# NOTE(yuming): Rename PIL.Image to avoid conflict with
# unstructured.documents.elements.Image
from PIL import Image as PILImage
from PIL import ImageSequence
from unstructured_inference.inference.elements import TextRegion
from unstructured_inference.inference.layout import DocumentLayout, PageLayout
from unstructured_inference.inference.layoutelement import (
    LayoutElement,
    partition_groups_from_regions,
)
from unstructured_pytesseract import Output

from unstructured.logger import logger
from unstructured.partition.utils.constants import SUBREGION_THRESHOLD_FOR_OCR, OCRMode

# Force tesseract to be single threaded,
# otherwise we see major performance problems
if "OMP_THREAD_LIMIT" not in os.environ:
    os.environ["OMP_THREAD_LIMIT"] = "1"


def process_data_with_ocr(
    data: Union[bytes, BinaryIO],
    out_layout: "DocumentLayout",
    is_image: bool = False,
    ocr_languages: str = "eng",
    ocr_mode: str = OCRMode.FULL_PAGE.value,
    pdf_image_dpi: int = 200,
) -> "DocumentLayout":
    """
    Process OCR data from a given data and supplement the output DocumentLayout
    from unstructured_inference with ocr.

    Parameters:
    - data (Union[bytes, BinaryIO]): The input file data,
        which can be either bytes or a BinaryIO object.

     - out_layout (DocumentLayout): The output layout from unstructured-inference.

    - is_image (bool, optional): Indicates if the input data is an image (True) or not (False).
        Defaults to False.

    - ocr_languages (str, optional): The languages for OCR processing. Defaults to "eng" (English).

    - ocr_mode (str, optional): The OCR processing mode, e.g., "entire_page" or "individual_blocks".
        Defaults to "entire_page". If choose "entire_page" OCR, OCR processes the entire image
        page and will be merged with the output layout. If choose "individual_blocks" OCR,
        OCR is performed on individual elements by cropping the image.

    - pdf_image_dpi (int, optional): DPI (dots per inch) for processing PDF images. Defaults to 200.

    Returns:
        DocumentLayout: The merged layout information obtained after OCR processing.
    """
    with tempfile.NamedTemporaryFile() as tmp_file:
        tmp_file.write(data.read() if hasattr(data, "read") else data)
        tmp_file.flush()
        merged_layouts = process_file_with_ocr(
            filename=tmp_file.name,
            out_layout=out_layout,
            is_image=is_image,
            ocr_languages=ocr_languages,
            ocr_mode=ocr_mode,
            pdf_image_dpi=pdf_image_dpi,
        )
        return merged_layouts


def process_file_with_ocr(
    filename: str,
    out_layout: "DocumentLayout",
    is_image: bool = False,
    ocr_languages: str = "eng",
    ocr_mode: str = OCRMode.FULL_PAGE.value,
    pdf_image_dpi: int = 200,
) -> "DocumentLayout":
    """
    Process OCR data from a given file and supplement the output DocumentLayout
    from unsturcutured0inference with ocr.

    Parameters:
    - filename (str): The path to the input file, which can be an image or a PDF.

    - out_layout (DocumentLayout): The output layout from unstructured-inference.

    - is_image (bool, optional): Indicates if the input data is an image (True) or not (False).
        Defaults to False.

    - ocr_languages (str, optional): The languages for OCR processing. Defaults to "eng" (English).

    - ocr_mode (str, optional): The OCR processing mode, e.g., "entire_page" or "individual_blocks".
        Defaults to "entire_page". If choose "entire_page" OCR, OCR processes the entire image
        page and will be merged with the output layout. If choose "individual_blocks" OCR,
        OCR is performed on individual elements by cropping the image.

    - pdf_image_dpi (int, optional): DPI (dots per inch) for processing PDF images. Defaults to 200.

    Returns:
        DocumentLayout: The merged layout information obtained after OCR processing.
    """
    merged_page_layouts = []
    try:
        if is_image:
            with PILImage.open(filename) as images:
                format = images.format
                for i, image in enumerate(ImageSequence.Iterator(images)):
                    image = image.convert("RGB")
                    image.format = format
                    merged_page_layout = supplement_page_layout_with_ocr(
                        out_layout.pages[i],
                        image,
                        ocr_languages=ocr_languages,
                        ocr_mode=ocr_mode,
                    )
                    merged_page_layouts.append(merged_page_layout)
                return DocumentLayout.from_pages(merged_page_layouts)
        else:
            with tempfile.TemporaryDirectory() as temp_dir:
                _image_paths = pdf2image.convert_from_path(
                    filename,
                    dpi=pdf_image_dpi,
                    output_folder=temp_dir,
                    paths_only=True,
                )
                image_paths = cast(List[str], _image_paths)
                for i, image_path in enumerate(image_paths):
                    with PILImage.open(image_path) as image:
                        merged_page_layout = supplement_page_layout_with_ocr(
                            out_layout.pages[i],
                            image,
                            ocr_languages=ocr_languages,
                            ocr_mode=ocr_mode,
                        )
                        merged_page_layouts.append(merged_page_layout)
                return DocumentLayout.from_pages(merged_page_layouts)
    except Exception as e:
        if os.path.isdir(filename) or os.path.isfile(filename):
            raise e
        else:
            raise FileNotFoundError(f'File "{filename}" not found!') from e


def supplement_page_layout_with_ocr(
    page_layout: "PageLayout",
    image: PILImage,
    ocr_languages: str = "eng",
    ocr_mode: str = OCRMode.FULL_PAGE.value,
) -> "PageLayout":
    """
    Supplement an PageLayout with OCR results depending on OCR mode.
    If mode is "entire_page", we get the OCR layout for the entire image and
    merge it with PageLayout.
    If mode is "individual_blocks", we find the elements from PageLayout
    with no text and add text from OCR to each element.
    """
    entire_page_ocr = os.getenv("ENTIRE_PAGE_OCR", "tesseract").lower()
    # TODO(yuming): add tests for paddle with ENTIRE_PAGE_OCR env
    # see CORE-1886
    if entire_page_ocr not in ["paddle", "tesseract"]:
        raise ValueError(
            "Environment variable ENTIRE_PAGE_OCR",
            " must be set to 'tesseract' or 'paddle'.",
        )

    elements = page_layout.elements
    if ocr_mode == OCRMode.FULL_PAGE.value:
        ocr_layout = get_ocr_layout_from_image(
            image,
            ocr_languages=ocr_languages,
            entire_page_ocr=entire_page_ocr,
        )
        merged_page_layout_elements = merge_out_layout_with_ocr_layout(
            elements,
            ocr_layout,
        )
        elements[:] = merged_page_layout_elements
        return page_layout
    elif ocr_mode == OCRMode.INDIVIDUAL_BLOCKS.value:
        for element in elements:
            if element.text == "":
                padded_element = pad_element_bboxes(element, padding=12)
                cropped_image = image.crop(
                    (
                        padded_element.bbox.x1,
                        padded_element.bbox.y1,
                        padded_element.bbox.x2,
                        padded_element.bbox.y2,
                    ),
                )
                text_from_ocr = get_ocr_text_from_image(
                    cropped_image,
                    ocr_languages=ocr_languages,
                    entire_page_ocr=entire_page_ocr,
                )
                element.text = text_from_ocr
        return page_layout
    else:
        raise ValueError(
            "Invalid OCR mode. Parameter `ocr_mode` "
            "must be set to `entire_page` or `individual_blocks`.",
        )


def pad_element_bboxes(
    element: "LayoutElement",
    padding: Union[int, float],
) -> "LayoutElement":
    """Increases (or decreases, if padding is negative) the size of the bounding
    boxes of the element by extending the boundary outward (resp. inward)"""

    out_element = deepcopy(element)
    out_element.bbox.x1 -= padding
    out_element.bbox.x2 += padding
    out_element.bbox.y1 -= padding
    out_element.bbox.y2 += padding
    return out_element


def get_ocr_layout_from_image(
    image: PILImage,
    ocr_languages: str = "eng",
    entire_page_ocr: str = "tesseract",
) -> List[TextRegion]:
    """
    Get the OCR layout from image as a list of text regions with paddle or tesseract.
    """
    if entire_page_ocr == "paddle":
        logger.info("Processing entrie page OCR with paddle...")
        from unstructured.partition.utils.ocr_models import paddle_ocr

        # TODO(yuming): pass in language parameter once we
        # have the mapping for paddle lang code
        # see CORE-2034
        ocr_data = paddle_ocr.load_agent().ocr(np.array(image), cls=True)
        ocr_layout = parse_ocr_data_paddle(ocr_data)
    else:
        ocr_data = unstructured_pytesseract.image_to_data(
            np.array(image),
            lang=ocr_languages,
            output_type=Output.DICT,
        )
        ocr_layout = parse_ocr_data_tesseract(ocr_data)
    return ocr_layout


def get_ocr_text_from_image(
    image: PILImage,
    ocr_languages: str = "eng",
    entire_page_ocr: str = "tesseract",
) -> str:
    """
    Get the OCR text from image as a string with paddle or tesseract.
    """
    if entire_page_ocr == "paddle":
        logger.info("Processing entrie page OCR with paddle...")
        from unstructured.partition.utils.ocr_models import paddle_ocr

        # TODO(yuming): pass in language parameter once we
        # have the mapping for paddle lang code
        # see CORE-2034
        ocr_data = paddle_ocr.load_agent().ocr(np.array(image), cls=True)
        ocr_layout = parse_ocr_data_paddle(ocr_data)
        text_from_ocr = ""
        for text_region in ocr_layout:
            text_from_ocr += text_region.text
    else:
        text_from_ocr = unstructured_pytesseract.image_to_string(
            np.array(image),
            lang=ocr_languages,
            output_type=Output.DICT,
        )["text"]
    return text_from_ocr


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
            text_region = TextRegion.from_coords(x1, y1, x2, y2, text=text, source="OCR-tesseract")
            text_regions.append(text_region)

    return text_regions


def parse_ocr_data_paddle(ocr_data: list) -> List[TextRegion]:
    """
    Parse the OCR result data to extract a list of TextRegion objects from
    paddle.

    The function processes the OCR result dictionary, looking for bounding
    box information and associated text to create instances of the TextRegion
    class, which are then appended to a list.

    Parameters:
    - ocr_data (list): A list containing the OCR result data

    Returns:
    - List[TextRegion]: A list of TextRegion objects, each representing a
                        detected text region within the OCR-ed image.

    Note:
    - An empty string or a None value for the 'text' key in the input
      dictionary will result in its associated bounding box being ignored.
    """
    text_regions = []
    for idx in range(len(ocr_data)):
        res = ocr_data[idx]
        for line in res:
            x1 = min([i[0] for i in line[0]])
            y1 = min([i[1] for i in line[0]])
            x2 = max([i[0] for i in line[0]])
            y2 = max([i[1] for i in line[0]])
            text = line[1][0]
            if text:
                text_region = TextRegion.from_coords(x1, y1, x2, y2, text, source="OCR-paddle")
                text_regions.append(text_region)

    return text_regions


def merge_out_layout_with_ocr_layout(
    out_layout: List[LayoutElement],
    ocr_layout: List[TextRegion],
    supplement_with_ocr_elements: bool = True,
) -> List[LayoutElement]:
    """
    Merge the out layout with the OCR-detected text regions on page level.

    This function iterates over each out layout element and aggregates the associated text from
    the OCR layout using the specified threshold. The out layout's text attribute is then updated
    with this aggregated text. If `supplement_with_ocr_elements` is `True`, the out layout will be
    supplemented with the OCR layout.
    """

    out_regions_without_text = [region for region in out_layout if not region.text]

    for out_region in out_regions_without_text:
        out_region.text = aggregate_ocr_text_by_block(
            ocr_layout,
            out_region,
            SUBREGION_THRESHOLD_FOR_OCR,
        )

    final_layout = (
        supplement_layout_with_ocr_elements(out_layout, ocr_layout)
        if supplement_with_ocr_elements
        else out_layout
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
        ocr_region_is_subregion_of_given_region = ocr_region.bbox.is_almost_subregion_of(
            region.bbox,
            subregion_threshold=subregion_threshold,
        )
        if ocr_region_is_subregion_of_given_region and ocr_region.text:
            extracted_texts.append(ocr_region.text)

    return " ".join(extracted_texts) if extracted_texts else ""


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
            ocr_region_is_subregion_of_out_el = ocr_region.bbox.is_almost_subregion_of(
                el.bbox,
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
        LayoutElement(text=r.text, source=r.source, type="UncategorizedText", bbox=r.bbox)
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

    min_x1 = min([tr.bbox.x1 for tr in regions])
    min_y1 = min([tr.bbox.y1 for tr in regions])
    max_x2 = max([tr.bbox.x2 for tr in regions])
    max_y2 = max([tr.bbox.y2 for tr in regions])

    merged_text = " ".join([tr.text for tr in regions if tr.text])

    return TextRegion.from_coords(min_x1, min_y1, max_x2, max_y2, merged_text)
