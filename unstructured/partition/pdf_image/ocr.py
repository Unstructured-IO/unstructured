from __future__ import annotations

import os
import tempfile
from typing import IO, TYPE_CHECKING, Any, List, Optional, cast

import numpy as np
import pdf2image

# NOTE(yuming): Rename PIL.Image to avoid conflict with
# unstructured.documents.elements.Image
from PIL import Image as PILImage
from PIL import ImageSequence

from unstructured.documents.elements import ElementType
from unstructured.metrics.table.table_formats import SimpleTableCell
from unstructured.partition.common.lang import tesseract_to_paddle_language
from unstructured.partition.pdf_image.analysis.layout_dump import OCRLayoutDumper
from unstructured.partition.pdf_image.pdf_image_utils import valid_text
from unstructured.partition.pdf_image.pdfminer_processing import (
    aggregate_embedded_text_by_block,
    bboxes1_is_almost_subregion_of_bboxes2,
)
from unstructured.partition.utils.config import env_config
from unstructured.partition.utils.constants import OCR_AGENT_PADDLE, OCR_AGENT_TESSERACT, OCRMode
from unstructured.partition.utils.ocr_models.ocr_interface import OCRAgent
from unstructured.utils import requires_dependencies

if TYPE_CHECKING:
    from unstructured_inference.inference.elements import TextRegion, TextRegions
    from unstructured_inference.inference.layout import DocumentLayout, PageLayout
    from unstructured_inference.inference.layoutelement import LayoutElement, LayoutElements
    from unstructured_inference.models.tables import UnstructuredTableTransformerModel


def process_data_with_ocr(
    data: bytes | IO[bytes],
    out_layout: "DocumentLayout",
    extracted_layout: List[List["TextRegion"]],
    is_image: bool = False,
    infer_table_structure: bool = False,
    ocr_agent: str = OCR_AGENT_TESSERACT,
    ocr_languages: str = "eng",
    ocr_mode: str = OCRMode.FULL_PAGE.value,
    pdf_image_dpi: int = 200,
    ocr_layout_dumper: Optional[OCRLayoutDumper] = None,
    password: Optional[str] = None,
    table_ocr_agent: str = OCR_AGENT_TESSERACT,
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

    - ocr_layout_dumper (OCRLayoutDumper, optional): The OCR layout dumper to save the OCR layout.

    Returns:
        DocumentLayout: The merged layout information obtained after OCR processing.
    """
    data_bytes = data if isinstance(data, bytes) else data.read()

    with tempfile.TemporaryDirectory() as tmp_dir_path:
        tmp_file_path = os.path.join(tmp_dir_path, "tmp_file")
        with open(tmp_file_path, "wb") as tmp_file:
            tmp_file.write(data_bytes)

        merged_layouts = process_file_with_ocr(
            filename=tmp_file_path,
            out_layout=out_layout,
            extracted_layout=extracted_layout,
            is_image=is_image,
            infer_table_structure=infer_table_structure,
            ocr_agent=ocr_agent,
            ocr_languages=ocr_languages,
            ocr_mode=ocr_mode,
            pdf_image_dpi=pdf_image_dpi,
            ocr_layout_dumper=ocr_layout_dumper,
            password=password,
            table_ocr_agent=table_ocr_agent,
        )

    return merged_layouts


@requires_dependencies("unstructured_inference")
def process_file_with_ocr(
    filename: str,
    out_layout: "DocumentLayout",
    extracted_layout: List[TextRegions],
    is_image: bool = False,
    infer_table_structure: bool = False,
    ocr_agent: str = OCR_AGENT_TESSERACT,
    ocr_languages: str = "eng",
    ocr_mode: str = OCRMode.FULL_PAGE.value,
    pdf_image_dpi: int = 200,
    ocr_layout_dumper: Optional[OCRLayoutDumper] = None,
    password: Optional[str] = None,
    table_ocr_agent: str = OCR_AGENT_TESSERACT,
) -> "DocumentLayout":
    """
    Process OCR data from a given file and supplement the output DocumentLayout
    from unstructured-inference with ocr.

    Parameters:
    - filename (str): The path to the input file, which can be an image or a PDF.

    - out_layout (DocumentLayout): The output layout from unstructured-inference.

    - extracted_layout (List[TextRegions]): a list of text regions extracted by pdfminer, one for
      each page

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

    from unstructured_inference.inference.layout import DocumentLayout

    merged_page_layouts: list[PageLayout] = []
    try:
        if is_image:
            with PILImage.open(filename) as images:
                image_format = images.format
                for i, image in enumerate(ImageSequence.Iterator(images)):
                    image = image.convert("RGB")
                    image.format = image_format
                    extracted_regions = extracted_layout[i] if i < len(extracted_layout) else None
                    merged_page_layout = supplement_page_layout_with_ocr(
                        page_layout=out_layout.pages[i],
                        image=image,
                        infer_table_structure=infer_table_structure,
                        ocr_agent=ocr_agent,
                        ocr_languages=ocr_languages,
                        ocr_mode=ocr_mode,
                        extracted_regions=extracted_regions,
                        ocr_layout_dumper=ocr_layout_dumper,
                        table_ocr_agent=table_ocr_agent,
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
                    userpw=password or "",
                )
                image_paths = cast(List[str], _image_paths)
                for i, image_path in enumerate(image_paths):
                    extracted_regions = extracted_layout[i] if i < len(extracted_layout) else None
                    with PILImage.open(image_path) as image:
                        merged_page_layout = supplement_page_layout_with_ocr(
                            page_layout=out_layout.pages[i],
                            image=image,
                            infer_table_structure=infer_table_structure,
                            ocr_agent=ocr_agent,
                            ocr_languages=ocr_languages,
                            ocr_mode=ocr_mode,
                            extracted_regions=extracted_regions,
                            ocr_layout_dumper=ocr_layout_dumper,
                            table_ocr_agent=table_ocr_agent,
                        )
                        merged_page_layouts.append(merged_page_layout)
                return DocumentLayout.from_pages(merged_page_layouts)
    except Exception as e:
        if os.path.isdir(filename) or os.path.isfile(filename):
            raise e
        else:
            raise FileNotFoundError(f'File "{filename}" not found!') from e


@requires_dependencies("unstructured_inference")
def supplement_page_layout_with_ocr(
    page_layout: "PageLayout",
    image: PILImage.Image,
    infer_table_structure: bool = False,
    ocr_agent: str = OCR_AGENT_TESSERACT,
    ocr_languages: str = "eng",
    ocr_mode: str = OCRMode.FULL_PAGE.value,
    extracted_regions: Optional[TextRegions] = None,
    ocr_layout_dumper: Optional[OCRLayoutDumper] = None,
    table_ocr_agent: str = OCR_AGENT_TESSERACT,
) -> "PageLayout":
    """
    Supplement an PageLayout with OCR results depending on OCR mode.
    If mode is "entire_page", we get the OCR layout for the entire image and
    merge it with PageLayout.
    If mode is "individual_blocks", we find the elements from PageLayout
    with no text and add text from OCR to each element.
    """

    language = ocr_languages
    if ocr_agent == OCR_AGENT_PADDLE:
        language = tesseract_to_paddle_language(ocr_languages)
    _ocr_agent = OCRAgent.get_instance(ocr_agent_module=ocr_agent, language=language)
    if ocr_mode == OCRMode.FULL_PAGE.value:
        ocr_layout = _ocr_agent.get_layout_from_image(image)
        if ocr_layout_dumper:
            ocr_layout_dumper.add_ocred_page(ocr_layout.as_list())
        page_layout.elements_array = merge_out_layout_with_ocr_layout(
            out_layout=page_layout.elements_array,
            ocr_layout=ocr_layout,
        )
    elif ocr_mode == OCRMode.INDIVIDUAL_BLOCKS.value:
        # individual block mode still keeps using the list data structure for elements instead of
        # the vectorized page_layout.elements_array data structure
        for i, text in enumerate(page_layout.elements_array.texts):
            if text:
                continue
            padding = env_config.IMAGE_CROP_PAD
            cropped_image = image.crop(
                (
                    page_layout.elements_array.x1[i] - padding,
                    page_layout.elements_array.y1[i] - padding,
                    page_layout.elements_array.x2[i] + padding,
                    page_layout.elements_array.y2[i] + padding,
                ),
            )
            # Note(yuming): instead of getting OCR layout, we just need
            # the text extraced from OCR for individual elements
            text_from_ocr = _ocr_agent.get_text_from_image(cropped_image)
            page_layout.elements_array.texts[i] = text_from_ocr
    else:
        raise ValueError(
            "Invalid OCR mode. Parameter `ocr_mode` "
            "must be set to `entire_page` or `individual_blocks`.",
        )

    # Note(yuming): use the OCR data from entire page OCR for table extraction
    if infer_table_structure:
        language = ocr_languages
        if table_ocr_agent == OCR_AGENT_PADDLE:
            language = tesseract_to_paddle_language(ocr_languages)
        _table_ocr_agent = OCRAgent.get_instance(
            ocr_agent_module=table_ocr_agent, language=language
        )
        from unstructured_inference.models import tables

        tables.load_agent()
        if tables.tables_agent is None:
            raise RuntimeError("Unable to load table extraction agent.")

        page_layout.elements_array = supplement_element_with_table_extraction(
            elements=page_layout.elements_array,
            image=image,
            tables_agent=tables.tables_agent,
            ocr_agent=_table_ocr_agent,
            extracted_regions=extracted_regions,
        )

    return page_layout


@requires_dependencies("unstructured_inference")
def supplement_element_with_table_extraction(
    elements: LayoutElements,
    image: PILImage.Image,
    tables_agent: "UnstructuredTableTransformerModel",
    ocr_agent,
    extracted_regions: Optional[TextRegions] = None,
) -> List["LayoutElement"]:
    """Supplement the existing layout with table extraction. Any Table elements
    that are extracted will have a metadata fields "text_as_html" where
    the table's text content is rendered into a html string and "table_as_cells"
    with the raw table cells output from table agent if env_config.EXTRACT_TABLE_AS_CELLS is True
    """
    from unstructured_inference.models.tables import cells_to_html

    table_id = {v: k for k, v in elements.element_class_id_map.items()}.get(ElementType.TABLE)
    if table_id is None:
        # no table found in this page
        return elements

    table_ele_indices = np.where(elements.element_class_ids == table_id)[0]
    table_elements = elements.slice(table_ele_indices)
    padding = env_config.TABLE_IMAGE_CROP_PAD
    for i, element_coords in enumerate(table_elements.element_coords):
        cropped_image = image.crop(
            (
                element_coords[0] - padding,
                element_coords[1] - padding,
                element_coords[2] + padding,
                element_coords[3] + padding,
            ),
        )
        table_tokens = get_table_tokens(
            table_element_image=cropped_image,
            ocr_agent=ocr_agent,
        )
        tatr_cells = tables_agent.predict(
            cropped_image, ocr_tokens=table_tokens, result_format="cells"
        )

        # NOTE(christine): `tatr_cells == ""` means that the table was not recognized
        text_as_html = "" if tatr_cells == "" else cells_to_html(tatr_cells)
        elements.text_as_html[table_ele_indices[i]] = text_as_html

        if env_config.EXTRACT_TABLE_AS_CELLS:
            simple_table_cells = [
                SimpleTableCell.from_table_transformer_cell(cell).to_dict() for cell in tatr_cells
            ]
            elements.table_as_cells[table_ele_indices[i]] = simple_table_cells

    return elements


def get_table_tokens(
    table_element_image: PILImage.Image,
    ocr_agent: OCRAgent,
) -> List[dict[str, Any]]:
    """Get OCR tokens from either paddleocr or tesseract"""

    ocr_layout = ocr_agent.get_layout_from_image(image=table_element_image)
    table_tokens = []
    for i, text in enumerate(ocr_layout.texts):
        table_tokens.append(
            {
                "bbox": [
                    ocr_layout.x1[i],
                    ocr_layout.y1[i],
                    ocr_layout.x2[i],
                    ocr_layout.y2[i],
                ],
                "text": text,
                # 'table_tokens' is a list of tokens
                # Need to be in a relative reading order
                "span_num": i,
                "line_num": 0,
                "block_num": 0,
            }
        )

    return table_tokens


def merge_out_layout_with_ocr_layout(
    out_layout: LayoutElements,
    ocr_layout: TextRegions,
    supplement_with_ocr_elements: bool = True,
    subregion_threshold: float = env_config.OCR_LAYOUT_SUBREGION_THRESHOLD,
) -> LayoutElements:
    """
    Merge the out layout with the OCR-detected text regions on page level.

    This function iterates over each out layout element and aggregates the associated text from
    the OCR layout using the specified threshold. The out layout's text attribute is then updated
    with this aggregated text. If `supplement_with_ocr_elements` is `True`, the out layout will be
    supplemented with the OCR layout.
    """

    if len(out_layout) == 0 or len(ocr_layout) == 0:
        # what if od model finds nothing but ocr finds something? should we use ocr output at all
        # currently we require some kind of bounding box, from `out_layout` to aggreaget ocr
        # results. Can we just use ocr bounding boxes (gonna be many but at least we save
        # information)
        return out_layout

    invalid_text_indices = [i for i, text in enumerate(out_layout.texts) if not valid_text(text)]
    out_layout.texts = out_layout.texts.astype(object)

    for idx in invalid_text_indices:
        out_layout.texts[idx] = aggregate_embedded_text_by_block(
            target_region=out_layout.slice([idx]),
            source_regions=ocr_layout,
            threshold=subregion_threshold,
        )

    final_layout = (
        supplement_layout_with_ocr_elements(out_layout, ocr_layout)
        if supplement_with_ocr_elements
        else out_layout
    )

    return final_layout


def aggregate_ocr_text_by_block(
    ocr_layout: List["TextRegion"],
    region: "TextRegion",
    subregion_threshold: float = env_config.OCR_LAYOUT_SUBREGION_THRESHOLD,
) -> Optional[str]:
    """Extracts the text aggregated from the regions of the ocr layout that lie within the given
    block."""

    extracted_texts = []

    for ocr_region in ocr_layout:
        ocr_region_is_subregion_of_given_region = ocr_region.bbox.is_almost_subregion_of(
            region.bbox,
            subregion_threshold,
        )
        if ocr_region_is_subregion_of_given_region and ocr_region.text:
            extracted_texts.append(ocr_region.text)

    return " ".join(extracted_texts) if extracted_texts else ""


@requires_dependencies("unstructured_inference")
def supplement_layout_with_ocr_elements(
    layout: LayoutElements,
    ocr_layout: TextRegions,
    subregion_threshold: float = env_config.OCR_LAYOUT_SUBREGION_THRESHOLD,
) -> LayoutElements:
    """
    Supplement the existing layout with additional OCR-derived elements.

    This function takes two lists: one list of pre-existing layout elements (`layout`)
    and another list of OCR-detected text regions (`ocr_layout`). It identifies OCR regions
    that are subregions of the elements in the existing layout and removes them from the
    OCR-derived list. Then, it appends the remaining OCR-derived regions to the existing layout.

    Parameters:
    - layout (LayoutElements): A collection of existing layout elements in array structures
    - ocr_layout (TextRegions): A collection of OCR-derived text regions in array structures

    Returns:
    - List[LayoutElement]: The final combined layout consisting of both the original layout
                           elements and the new OCR-derived elements.

    Note:
    - The function relies on `is_almost_subregion_of()` method to determine if an OCR region
      is a subregion of an existing layout element.
    - It also relies on `build_layout_elements_from_ocr_regions()` to convert OCR regions to
     layout elements.
    - The env_config `OCR_LAYOUT_SUBREGION_THRESHOLD` is used to specify the subregion matching
     threshold.
    """

    from unstructured_inference.inference.layoutelement import LayoutElements

    from unstructured.partition.pdf_image.inference_utils import (
        build_layout_elements_from_ocr_regions,
    )

    if len(layout) == 0:
        if len(ocr_layout) == 0:
            return layout
        else:
            ocr_regions_to_add = ocr_layout
    else:
        mask = (
            ~bboxes1_is_almost_subregion_of_bboxes2(
                ocr_layout.element_coords, layout.element_coords, subregion_threshold
            )
            .sum(axis=1)
            .astype(bool)
        )

        # add ocr regions that are not covered by layout
        ocr_regions_to_add = ocr_layout.slice(mask)

    if len(ocr_regions_to_add):
        ocr_elements_to_add = build_layout_elements_from_ocr_regions(ocr_regions_to_add)
        final_layout = LayoutElements.concatenate([layout, ocr_elements_to_add])
    else:
        final_layout = layout

    return final_layout
