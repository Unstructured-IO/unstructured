import os
import tempfile
from typing import BinaryIO, List, Optional, Union, cast

import numpy as np
import pdf2image
import pytesseract
from PIL import Image as PILImage
from PIL import ImageSequence
from pytesseract import Output
from unstructured_inference.inference.elements import (
    # Rectangle,
    TextRegion,
)

# partition_groups_from_regions,
from unstructured_inference.inference.layout import DocumentLayout

# from unstructured_inference.inference.layoutelement import (
#     LayoutElement,
#     aggregate_ocr_text_by_block,
#     get_elements_from_ocr_regions,
#     merge_text_regions,
#     supplement_layout_with_ocr_elements,
# )
from unstructured_inference.inference.layoutelement import (
    merge_inferred_layout_with_ocr_layout as merge_inferred_layout_with_ocr_layout_per_page,
)

SUBREGION_THRESHOLD_FOR_OCR = 0.5


def process_data_with_ocr(
    data: Optional[Union[bytes, BinaryIO]],
    is_image: bool = False,
    ocr_languages: str = "eng",
    pdf_image_dpi: int = 200,
) -> List[List[TextRegion]]:
    with tempfile.NamedTemporaryFile() as tmp_file:
        tmp_file.write(data.read() if hasattr(data, "read") else data)
        tmp_file.flush()
        ocr_layouts = process_file_with_ocr(
            filename=tmp_file.name,
            is_image=is_image,
            ocr_languages=ocr_languages,
            pdf_image_dpi=pdf_image_dpi,
        )
        return ocr_layouts


def process_file_with_ocr(
    filename: str = "",
    is_image: bool = False,
    ocr_languages: str = "eng",
    pdf_image_dpi: int = 200,
) -> List[List[TextRegion]]:
    if is_image:
        try:
            with PILImage.open(filename) as image:
                format = image.format
                ocr_layouts = []
                for im in ImageSequence.Iterator(image):
                    im = im.convert("RGB")
                    im.format = format
                    ocr_data = pytesseract.image_to_data(
                        np.array(im),
                        lang=ocr_languages,
                        output_type=Output.DICT,
                    )
                    ocr_layout = parse_ocr_data_tesseract(ocr_data)
                    ocr_layouts.append(ocr_layout)
            return ocr_layouts
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
            ocr_layouts = []
            for image_path in image_paths:
                with PILImage.open(image_path) as image:
                    ocr_data = pytesseract.image_to_data(
                        np.array(image),
                        lang=ocr_languages,
                        output_type=Output.DICT,
                    )
                    ocr_layout = parse_ocr_data_tesseract(ocr_data)
                    ocr_layouts.append(ocr_layout)
            return ocr_layouts


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
            text_region = TextRegion(x1, y1, x2, y2, text=text)
            text_regions.append(text_region)

    return text_regions


def merge_inferred_layout_with_ocr_layout(
    inferred_layouts: "DocumentLayout",
    ocr_layouts: List[List[TextRegion]],
) -> "DocumentLayout":
    merged_layouts = inferred_layouts
    pages = inferred_layouts.pages
    for i in range(len(pages)):
        inferred_layout = pages[i].elements
        ocr_layout = ocr_layouts[i]
        merged_layout = merge_inferred_layout_with_ocr_layout_per_page(inferred_layout, ocr_layout)
        merged_layouts.pages[i].elements[:] = merged_layout
    return merged_layouts
