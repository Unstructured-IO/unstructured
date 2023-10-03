import os
import tempfile
from typing import BinaryIO, List, Optional, Union, cast

import numpy as np
import pdf2image

# TODO(yuming): update pytesseract to unst forked pytesseract
import pytesseract

# rename PIL.Image to avoid conflict with unstructured.documents.elements.Image
from PIL import Image as PILImage
from PIL import ImageSequence
from pytesseract import Output

# TODO(yuming): check this if need to separate any ocr
from unstructured_inference.constants import Source
from unstructured_inference.inference.elements import (
    Rectangle,
    TextRegion,
    partition_groups_from_regions,
)
from unstructured_inference.inference.layout import DocumentLayout, PageLayout
from unstructured_inference.inference.layoutelement import (
    LayoutElement,
)

from unstructured.logger import logger

SUBREGION_THRESHOLD_FOR_OCR = 0.5


def process_data_with_ocr(
    data: Union[bytes, BinaryIO],
    inferred_layout: "DocumentLayout",
    is_image: bool = False,
    ocr_languages: str = "eng",
    ocr_mode: str = "entire_page",
    pdf_image_dpi: int = 200,
) -> List[List[TextRegion]]:
    """
    Retrieve OCR layout information as one document from given file data
    TODO(yuming): add me... (more information on each parameter ect)
    """
    with tempfile.NamedTemporaryFile() as tmp_file:
        tmp_file.write(data.read() if hasattr(data, "read") else data)
        tmp_file.flush()
        merged_layouts = process_file_with_ocr(
            filename=tmp_file.name,
            inferred_layout=inferred_layout,
            is_image=is_image,
            ocr_languages=ocr_languages,
            ocr_mode=ocr_mode,
            pdf_image_dpi=pdf_image_dpi,
        )
        return merged_layouts


def process_file_with_ocr(
    filename: str,
    inferred_layout: "DocumentLayout",
    is_image: bool = False,
    ocr_languages: str = "eng",
    ocr_mode: str = "entire_page",
    pdf_image_dpi: int = 200,
) -> List[List[TextRegion]]:
    """
    Retrieve OCR layout information as one document from given filename
    TODO(yuming): add me... (more information on each parameter ect)
    """
    merged_page_layouts = []
    if is_image:
        try:
            with PILImage.open(filename) as images:
                format = images.format
                for i, image in enumerate(ImageSequence.Iterator(images)):
                    image = image.convert("RGB")
                    image.format = format
                    merged_page_layout = supplement_page_layout_with_ocr(
                        inferred_layout[i],
                        image,
                        ocr_languages=ocr_languages,
                        ocr_mode=ocr_mode,
                    )
                    merged_page_layouts.append(merged_page_layout)
        except Exception as e:
            if os.path.isdir(filename) or os.path.isfile(filename):
                raise e
            else:
                raise FileNotFoundError(f'File "{filename}" not found!') from e
    else:
        with tempfile.TemporaryDirectory() as temp_dir:
            _image_paths = pdf2image.convert_from_path(
                filename,
                dpi=pdf_image_dpi,
                output_folder=temp_dir,
                paths_only=True,
            )
            image_paths = cast(List[str], _image_paths)
            for image_path in image_paths:
                with PILImage.open(image_path) as image:
                    merged_page_layout = supplement_page_layout_with_ocr(
                        inferred_layout[i],
                        image,
                        ocr_languages=ocr_languages,
                        ocr_mode=ocr_mode,
                    )
                    merged_page_layouts.append(merged_page_layout)
    return DocumentLayout.from_pages(merged_page_layouts)


def supplement_page_layout_with_ocr(
    inferred_page_layout: "PageLayout",
    image: PILImage,
    ocr_languages: str = "eng",
    ocr_mode: str = "entire_page",
) -> "PageLayout":
    entrie_page_ocr = os.getenv("ENTIRE_PAGE_OCR", "tesseract").lower()
    # TODO(yuming): add tests for paddle with ENTIRE_PAGE_OCR env
    # see core CORE-1886
    if entrie_page_ocr not in ["paddle", "tesseract"]:
        raise ValueError(
            "Environment variable ENTIRE_PAGE_OCR",
            " must be set to 'tesseract' or 'paddle'.",
        )
    if ocr_mode == "entire_page":
        ocr_layout = get_ocr_layout_from_image(
            image,
            ocr_languages=ocr_languages,
            entrie_page_ocr=entrie_page_ocr,
        )
        merged_page_layout = merge_inferred_layout_with_ocr_layout(inferred_page_layout, ocr_layout)
        return merged_page_layout
    elif ocr_mode == "individual_blocks":
        elements = inferred_page_layout.elements
        for i, element in enumerate(elements):
            if element.text == "":
                cropped_image = image.crop((element.x1, element.y1, element.x2, element.y2))
                ocr_layout = get_ocr_layout_from_image(
                    cropped_image,
                    ocr_languages=ocr_languages,
                    entrie_page_ocr=entrie_page_ocr,
                )
                text_from_ocr = ""
                for text_region in ocr_layout:
                    text_from_ocr += text_region.text
                elements[i].text = text_from_ocr
        inferred_page_layout.elements = elements
        return inferred_page_layout
    else:
        raise ValueError(
            "Invalid OCR mode. Parameter `ocr_mode` "
            "must be set to `entire_page` or individual_blocks`.",
        )


def get_ocr_layout_from_image(
    image: PILImage,
    ocr_languages: str = "eng",
    entrie_page_ocr: str = "tesseract",
) -> List[TextRegion]:
    if entrie_page_ocr == "paddle":
        logger.info("Processing entrie page OCR with paddle...")
        from unstructured.partition.utils.ocr_models import paddle_ocr

        # TODO(yuming): pass in language parameter once we
        # have the mapping for paddle lang code
        ocr_data = paddle_ocr.load_agent().ocr(np.array(image), cls=True)
        ocr_layout = parse_ocr_data_paddle(ocr_data)
    else:
        ocr_data = pytesseract.image_to_data(
            np.array(image),
            lang=ocr_languages,
            output_type=Output.DICT,
        )
        ocr_layout = parse_ocr_data_tesseract(ocr_data)
    return ocr_layout


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
            text_region = TextRegion(x1, y1, x2, y2, text=text, source=Source.OCR_TESSERACT)
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
                text_region = TextRegion(x1, y1, x2, y2, text, source=Source.OCR_PADDLE)
                text_regions.append(text_region)

    return text_regions


def merge_inferred_layout_with_ocr_layout(
    inferred_layout: List[LayoutElement],
    ocr_layout: List[TextRegion],
    supplement_with_ocr_elements: bool = True,
) -> List[LayoutElement]:
    """
    Merge the inferred layout with the OCR-detected text regions on page level.

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
            source=r.source,
            type="UncategorizedText",
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

    min_x1 = min([tr.x1 for tr in regions])
    min_y1 = min([tr.y1 for tr in regions])
    max_x2 = max([tr.x2 for tr in regions])
    max_y2 = max([tr.y2 for tr in regions])

    merged_text = " ".join([tr.text for tr in regions if tr.text])

    return TextRegion(min_x1, min_y1, max_x2, max_y2, merged_text)
