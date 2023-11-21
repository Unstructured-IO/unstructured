import os
import tempfile
from copy import deepcopy
from typing import BinaryIO, Dict, List, Optional, Union, cast

import cv2
import numpy as np
import pandas as pd
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
from unstructured_inference.models.tables import UnstructuredTableTransformerModel
from unstructured_pytesseract import Output

from unstructured.documents.elements import ElementType
from unstructured.logger import logger
from unstructured.partition.utils.config import env_config
from unstructured.partition.utils.constants import (
    OCR_AGENT_PADDLE,
    OCR_AGENT_TESSERACT,
    SUBREGION_THRESHOLD_FOR_OCR,
    TESSERACT_TEXT_HEIGHT,
    OCRMode,
    Source,
)

# Force tesseract to be single threaded,
# otherwise we see major performance problems
if "OMP_THREAD_LIMIT" not in os.environ:
    os.environ["OMP_THREAD_LIMIT"] = "1"


def process_data_with_ocr(
    data: Union[bytes, BinaryIO],
    out_layout: "DocumentLayout",
    is_image: bool = False,
    infer_table_structure: bool = False,
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

    - infer_table_structure (bool, optional):  If true, extract the table content.

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
            infer_table_structure=infer_table_structure,
            ocr_languages=ocr_languages,
            ocr_mode=ocr_mode,
            pdf_image_dpi=pdf_image_dpi,
        )
        return merged_layouts


def process_file_with_ocr(
    filename: str,
    out_layout: "DocumentLayout",
    is_image: bool = False,
    infer_table_structure: bool = False,
    ocr_languages: str = "eng",
    ocr_mode: str = OCRMode.FULL_PAGE.value,
    pdf_image_dpi: int = 200,
) -> "DocumentLayout":
    """
    Process OCR data from a given file and supplement the output DocumentLayout
    from unsturcutured-inference with ocr.

    Parameters:
    - filename (str): The path to the input file, which can be an image or a PDF.

    - out_layout (DocumentLayout): The output layout from unstructured-inference.

    - is_image (bool, optional): Indicates if the input data is an image (True) or not (False).
        Defaults to False.

    - infer_table_structure (bool, optional):  If true, extract the table content.

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
                image_format = images.format
                for i, image in enumerate(ImageSequence.Iterator(images)):
                    image = image.convert("RGB")
                    image.format = image_format
                    merged_page_layout = supplement_page_layout_with_ocr(
                        out_layout.pages[i],
                        image,
                        infer_table_structure=infer_table_structure,
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
                            infer_table_structure=infer_table_structure,
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
    infer_table_structure: bool = False,
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

    ocr_agent = get_ocr_agent()
    if ocr_mode == OCRMode.FULL_PAGE.value:
        ocr_layout = get_ocr_layout_from_image(
            image,
            ocr_languages=ocr_languages,
            ocr_agent=ocr_agent,
        )
        page_layout.elements[:] = merge_out_layout_with_ocr_layout(
            out_layout=cast(List[LayoutElement], page_layout.elements),
            ocr_layout=ocr_layout,
        )
    elif ocr_mode == OCRMode.INDIVIDUAL_BLOCKS.value:
        for element in page_layout.elements:
            if element.text == "":
                padding = env_config.IMAGE_CROP_PAD
                padded_element = pad_element_bboxes(element, padding=padding)
                cropped_image = image.crop(
                    (
                        padded_element.bbox.x1,
                        padded_element.bbox.y1,
                        padded_element.bbox.x2,
                        padded_element.bbox.y2,
                    ),
                )
                # Note(yuming): instead of getting OCR layout, we just need
                # the text extraced from OCR for individual elements
                text_from_ocr = get_ocr_text_from_image(
                    cropped_image,
                    ocr_languages=ocr_languages,
                    ocr_agent=ocr_agent,
                )
                element.text = text_from_ocr
    else:
        raise ValueError(
            "Invalid OCR mode. Parameter `ocr_mode` "
            "must be set to `entire_page` or `individual_blocks`.",
        )

    # Note(yuming): use the OCR data from entire page OCR for table extraction
    if infer_table_structure:
        from unstructured_inference.models import tables

        tables.load_agent()
        if tables.tables_agent is None:
            raise RuntimeError("Unable to load table extraction agent.")

        page_layout.elements[:] = supplement_element_with_table_extraction(
            elements=cast(List[LayoutElement], page_layout.elements),
            image=image,
            tables_agent=tables.tables_agent,
            ocr_languages=ocr_languages,
            ocr_agent=ocr_agent,
        )

    return page_layout


def supplement_element_with_table_extraction(
    elements: List[LayoutElement],
    image: PILImage,
    tables_agent: "UnstructuredTableTransformerModel",
    ocr_languages: str = "eng",
    ocr_agent: str = OCR_AGENT_TESSERACT,
) -> List[LayoutElement]:
    """Supplement the existing layout with table extraction. Any Table elements
    that are extracted will have a metadata field "text_as_html" where
    the table's text content is rendered into an html string.
    """
    for element in elements:
        if element.type == ElementType.TABLE:
            padding = env_config.TABLE_IMAGE_CROP_PAD
            padded_element = pad_element_bboxes(element, padding=padding)
            cropped_image = image.crop(
                (
                    padded_element.bbox.x1,
                    padded_element.bbox.y1,
                    padded_element.bbox.x2,
                    padded_element.bbox.y2,
                ),
            )
            table_tokens = get_table_tokens(
                image=cropped_image, ocr_languages=ocr_languages, ocr_agent=ocr_agent
            )
            element.text_as_html = tables_agent.predict(cropped_image, ocr_tokens=table_tokens)
    return elements


def get_table_tokens(
    image: PILImage,
    ocr_languages: str = "eng",
    ocr_agent: str = OCR_AGENT_TESSERACT,
) -> List[Dict]:
    """Get OCR tokens from either paddleocr or tesseract"""

    ocr_layout = get_ocr_layout_from_image(
        image,
        ocr_languages=ocr_languages,
        ocr_agent=ocr_agent,
    )
    table_tokens = []
    for ocr_region in ocr_layout:
        table_tokens.append(
            {
                "bbox": [
                    ocr_region.bbox.x1,
                    ocr_region.bbox.y1,
                    ocr_region.bbox.x2,
                    ocr_region.bbox.y2,
                ],
                "text": ocr_region.text,
            }
        )

    # 'table_tokens' is a list of tokens
    # Need to be in a relative reading order
    # If no order is provided, use current order
    for idx, token in enumerate(table_tokens):
        if "span_num" not in token:
            token["span_num"] = idx
        if "line_num" not in token:
            token["line_num"] = 0
        if "block_num" not in token:
            token["block_num"] = 0
    return table_tokens


def get_layout_elements_from_ocr(
    image: PILImage,
    ocr_languages: str = "eng",
    ocr_agent: str = OCR_AGENT_TESSERACT,
) -> List[LayoutElement]:
    """
    Generate a PageLayout with OCR data from a given image.
    """

    ocr_regions = get_ocr_layout_from_image(
        image,
        ocr_languages=ocr_languages,
        ocr_agent=ocr_agent,
    )

    if ocr_agent == OCR_AGENT_PADDLE:
        # NOTE(christine): For paddle, there is no difference in `ocr_layout` and `ocr_text` in
        # terms of grouping because we get ocr_text from `ocr_layout, so the first two grouping
        # and merging steps are not necessary.

        layout_elements = [
            LayoutElement(
                bbox=r.bbox, text=r.text, source=r.source, type=ElementType.UNCATEGORIZED_TEXT
            )
            for r in ocr_regions
        ]
    else:
        # NOTE(christine): For tesseract, the ocr_text returned by
        # `unstructured_pytesseract.image_to_string()` doesn't contain bounding box data but is
        # well grouped. Conversely, the ocr_layout returned by parsing
        # `unstructured_pytesseract.image_to_data()` contains bounding box data but is not well
        # grouped. Therefore, we need to first group the `ocr_layout` by `ocr_text` and then merge
        # the text regions in each group to create a list of layout elements.

        ocr_text = get_ocr_text_from_image(
            image,
            ocr_languages=ocr_languages,
            ocr_agent=ocr_agent,
        )

        layout_elements = get_elements_from_ocr_regions(
            ocr_regions=ocr_regions,
            ocr_text=ocr_text,
            group_by_ocr_text=True,
        )

    return layout_elements


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


def zoom_image(image: PILImage, zoom: float = 1) -> PILImage:
    """scale an image based on the zoom factor using cv2; the scaled image is post processed by
    dilation then erosion to improve edge sharpness for OCR tasks"""
    if zoom <= 0:
        # no zoom but still does dilation and erosion
        zoom = 1
    new_image = cv2.resize(
        cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR),
        None,
        fx=zoom,
        fy=zoom,
        interpolation=cv2.INTER_CUBIC,
    )

    kernel = np.ones((1, 1), np.uint8)
    new_image = cv2.dilate(new_image, kernel, iterations=1)
    new_image = cv2.erode(new_image, kernel, iterations=1)

    return PILImage.fromarray(new_image)


def get_ocr_text_from_image(
    image: PILImage,
    ocr_languages: str = "eng",
    ocr_agent: str = "tesseract",
) -> str:
    """
    Get the OCR text from image as a string with paddle or tesseract.
    """
    if ocr_agent == OCR_AGENT_PADDLE:
        ocr_regions = get_ocr_layout_paddle(image)
        ocr_text = "\n\n".join([r.text for r in ocr_regions])
    else:
        ocr_text = unstructured_pytesseract.image_to_string(
            np.array(image),
            lang=ocr_languages,
        )
    return ocr_text


def get_ocr_layout_from_image(
    image: PILImage,
    ocr_languages: str = "eng",
    ocr_agent: str = "tesseract",
) -> List[TextRegion]:
    """
    Get the OCR regions from image as a list of text regions with paddle or tesseract.
    """

    if ocr_agent == OCR_AGENT_PADDLE:
        ocr_regions = get_ocr_layout_paddle(image)
    else:
        ocr_regions = get_ocr_layout_tesseract(image, ocr_languages)

    return ocr_regions


def get_ocr_layout_tesseract(
    image: PILImage,
    ocr_languages: str = "eng",
) -> List[TextRegion]:
    """Get the OCR regions from image as a list of text regions with tesseract."""

    logger.info("Processing entire page OCR with tesseract...")
    zoom = 1
    ocr_df: pd.DataFrame = unstructured_pytesseract.image_to_data(
        np.array(image),
        lang=ocr_languages,
        output_type=Output.DATAFRAME,
    )
    ocr_df = ocr_df.dropna()

    # tesseract performance degrades when the text height is out of the preferred zone so we
    # zoom the image (in or out depending on estimated text height) for optimum OCR results
    # but this needs to be evaluated based on actual use case as the optimum scaling also
    # depend on type of characters (font, language, etc); be careful about this
    # functionality
    text_height = ocr_df[TESSERACT_TEXT_HEIGHT].quantile(
        env_config.TESSERACT_TEXT_HEIGHT_QUANTILE,
    )
    if (
        text_height < env_config.TESSERACT_MIN_TEXT_HEIGHT
        or text_height > env_config.TESSERACT_MAX_TEXT_HEIGHT
    ):
        # rounding avoids unnecessary precision and potential numerical issues associated
        # with numbers very close to 1 inside cv2 image processing
        zoom = np.round(env_config.TESSERACT_OPTIMUM_TEXT_HEIGHT / text_height, 1)
        ocr_df = unstructured_pytesseract.image_to_data(
            np.array(zoom_image(image, zoom)),
            lang=ocr_languages,
            output_type=Output.DATAFRAME,
        )
        ocr_df = ocr_df.dropna()

    ocr_regions = parse_ocr_data_tesseract(ocr_df, zoom=zoom)

    return ocr_regions


def get_ocr_layout_paddle(image: PILImage) -> List[TextRegion]:
    """Get the OCR regions from image as a list of text regions with paddle."""

    logger.info("Processing entire page OCR with paddle...")
    from unstructured.partition.utils.ocr_models import paddle_ocr

    # TODO(yuming): pass in language parameter once we
    # have the mapping for paddle lang code
    # see CORE-2034
    ocr_data = paddle_ocr.load_agent().ocr(np.array(image), cls=True)
    ocr_regions = parse_ocr_data_paddle(ocr_data)

    return ocr_regions


def parse_ocr_data_tesseract(ocr_data: pd.DataFrame, zoom: float = 1) -> List[TextRegion]:
    """
    Parse the OCR result data to extract a list of TextRegion objects from
    tesseract.

    The function processes the OCR result data frame, looking for bounding
    box information and associated text to create instances of the TextRegion
    class, which are then appended to a list.

    Parameters:
    - ocr_data (pd.DataFrame):
        A Pandas DataFrame containing the OCR result data.
        It should have columns like 'text', 'left', 'top', 'width', and 'height'.

    - zoom (float, optional):
        A zoom factor to scale the coordinates of the bounding boxes from image scaling.
        Default is 1.

    Returns:
    - List[TextRegion]:
        A list of TextRegion objects, each representing a detected text region
        within the OCR-ed image.

    Note:
    - An empty string or a None value for the 'text' key in the input
      data frame will result in its associated bounding box being ignored.
    """

    if zoom <= 0:
        zoom = 1

    text_regions = []
    for idtx in ocr_data.itertuples():
        text = idtx.text
        if not text:
            continue

        cleaned_text = str(text) if not isinstance(text, str) else text.strip()

        if cleaned_text:
            x1 = idtx.left / zoom
            y1 = idtx.top / zoom
            x2 = (idtx.left + idtx.width) / zoom
            y2 = (idtx.top + idtx.height) / zoom
            text_region = TextRegion.from_coords(
                x1,
                y1,
                x2,
                y2,
                text=cleaned_text,
                source=Source.OCR_TESSERACT,
            )
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
        if not res:
            continue

        for line in res:
            x1 = min([i[0] for i in line[0]])
            y1 = min([i[1] for i in line[0]])
            x2 = max([i[0] for i in line[0]])
            y2 = max([i[1] for i in line[0]])
            text = line[1][0]
            if not text:
                continue
            cleaned_text = text.strip()
            if cleaned_text:
                text_region = TextRegion.from_coords(
                    x1,
                    y1,
                    x2,
                    y2,
                    cleaned_text,
                    source=Source.OCR_PADDLE,
                )
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


def get_elements_from_ocr_regions(
    ocr_regions: List[TextRegion],
    ocr_text: Optional[str] = None,
    group_by_ocr_text: bool = False,
) -> List[LayoutElement]:
    """
    Get layout elements from OCR regions
    """

    if group_by_ocr_text:
        text_sections = ocr_text.split("\n\n")
        grouped_regions = []
        for text_section in text_sections:
            regions = []
            words = text_section.replace("\n", " ").split()
            for ocr_region in ocr_regions:
                if not words:
                    break
                if ocr_region.text in words:
                    regions.append(ocr_region)
                    words.remove(ocr_region.text)

            if not regions:
                continue

            for r in regions:
                ocr_regions.remove(r)

            grouped_regions.append(regions)
    else:
        grouped_regions = cast(
            List[List[TextRegion]],
            partition_groups_from_regions(ocr_regions),
        )

    merged_regions = [merge_text_regions(group) for group in grouped_regions]
    return [
        LayoutElement(
            text=r.text, source=r.source, type=ElementType.UNCATEGORIZED_TEXT, bbox=r.bbox
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

    if not regions:
        raise ValueError("The text regions to be merged must be provided.")

    min_x1 = min([tr.bbox.x1 for tr in regions])
    min_y1 = min([tr.bbox.y1 for tr in regions])
    max_x2 = max([tr.bbox.x2 for tr in regions])
    max_y2 = max([tr.bbox.y2 for tr in regions])

    merged_text = " ".join([tr.text for tr in regions if tr.text])
    sources = [tr.source for tr in regions]
    source = sources[0] if all(s == sources[0] for s in sources) else None

    return TextRegion.from_coords(min_x1, min_y1, max_x2, max_y2, merged_text, source)


def get_ocr_agent() -> str:
    ocr_agent = env_config.OCR_AGENT.lower()
    if ocr_agent not in [OCR_AGENT_PADDLE, OCR_AGENT_TESSERACT]:
        raise ValueError(
            "Environment variable OCR_AGENT",
            " must be set to 'tesseract' or 'paddle'.",
        )
    return ocr_agent
