import os
import tempfile
from pathlib import PurePath
from typing import BinaryIO, List, Optional, Union, cast

import pdf2image
import PIL
import pytesseract
from pytesseract import Output
from unstructured_inference.inference.elements import (
    Rectangle,
    TextRegion,
    partition_groups_from_regions,
)
from unstructured_inference.inference.layoutelement import (
    LayoutElement,
)

SUBREGION_THRESHOLD_FOR_OCR = 0.5


def process_data_with_ocr(
    data: Optional[Union[bytes, BinaryIO]],
    is_image: bool = False,
    ocr_languages: str = "eng",
    pdf_image_dpi: int = 200,
) -> List[List[TextRegion]]:
    with tempfile.NamedTemporaryFile() as tmp_file:
        tmp_file.write(data.read())
        tmp_file.flush()  #
        ocr_layouts = process_file_with_ocr(
            tmp_file.name,
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
            image = PIL.Image.open(filename)
            format = image.format
            images = []
            for im in PIL.ImageSequence.Iterator(image):
                im = im.convert("RGB")
                im.format = format
                images.append(im)
        except Exception as e:
            if os.path.isdir(filename) or os.path.isfile(filename):
                raise e
            else:
                raise FileNotFoundError(f'File "{filename}" not found!') from e
    else:
        # ocr PDF
        ...
    ocr_layouts = []
    for image in images:
        ocr_data = pytesseract.image_to_data(
            image,
            lang=ocr_languages,
            output_type=Output.DICT,
        )
        ocr_layout = parse_ocr_data_tesseract(ocr_data)
        ocr_layouts.append(ocr_layout)
    return ocr_layouts


def load_images_from_pdf(
    filename: str,
    dpi: int = 200,
    output_folder: Optional[Union[str, PurePath]] = None,
    path_only: bool = False,
) -> Union[List[PIL.Image.Image], List[str]]:
    """image renderings of the pdf pages using pdf2image""" ""
    if path_only and not output_folder:
        raise ValueError("output_folder must be specified if path_only is true")

    if output_folder is not None:
        _image_paths = pdf2image.convert_from_path(
            filename,
            dpi=dpi,
            output_folder=output_folder,
            paths_only=path_only,
        )
    else:
        _image_paths = pdf2image.convert_from_path(
            filename,
            dpi=dpi,
            paths_only=path_only,
        )
    image_paths = cast(List[str], _image_paths)
    return image_paths


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
