from __future__ import annotations

import contextlib
import io
import os
import re
import warnings
from tempfile import SpooledTemporaryFile
from typing import (
    IO,
    TYPE_CHECKING,
    Any,
    BinaryIO,
    Dict,
    Iterator,
    List,
    Optional,
    Sequence,
    Tuple,
    Union,
    cast,
)

import numpy as np
import pdf2image
import wrapt
from pdfminer import psparser
from pdfminer.layout import (
    LTChar,
    LTContainer,
    LTImage,
    LTItem,
    LTTextBox,
)
from pdfminer.pdftypes import PDFObjRef
from pdfminer.utils import open_filename
from PIL import Image as PILImage

from unstructured.chunking import add_chunking_strategy
from unstructured.cleaners.core import (
    clean_extra_whitespace_with_index_run,
    index_adjustment_after_clean_extra_whitespace,
)
from unstructured.documents.coordinates import PixelSpace, PointSpace
from unstructured.documents.elements import (
    CoordinatesMetadata,
    Element,
    ElementMetadata,
    ElementType,
    Image,
    Link,
    ListItem,
    PageBreak,
    Text,
    process_metadata,
)
from unstructured.file_utils.filetype import (
    FileType,
    add_metadata_with_filetype,
)
from unstructured.logger import logger, trace_logger
from unstructured.nlp.patterns import PARAGRAPH_PATTERN
from unstructured.partition.common import (
    convert_to_bytes,
    document_to_element_list,
    exactly_one,
    get_last_modified_date,
    get_last_modified_date_from_file,
    ocr_data_to_elements,
    spooled_to_bytes_io_if_needed,
)
from unstructured.partition.lang import (
    check_languages,
    prepare_languages_for_tesseract,
)
from unstructured.partition.pdf_image.pdf_image_utils import (
    annotate_layout_elements,
    check_element_types_to_extract,
    save_elements,
)
from unstructured.partition.pdf_image.pdfminer_processing import (
    merge_inferred_with_extracted_layout,
)
from unstructured.partition.pdf_image.pdfminer_utils import (
    open_pdfminer_pages_generator,
    rect_to_bbox,
)
from unstructured.partition.strategies import determine_pdf_or_image_strategy, validate_strategy
from unstructured.partition.text import element_from_text
from unstructured.partition.utils.constants import (
    OCR_AGENT_TESSERACT,
    SORT_MODE_BASIC,
    SORT_MODE_DONT,
    SORT_MODE_XY_CUT,
    OCRMode,
    PartitionStrategy,
)
from unstructured.partition.utils.processing_elements import clean_pdfminer_inner_elements
from unstructured.partition.utils.sorting import (
    coord_has_valid_points,
    sort_page_elements,
)
from unstructured.patches.pdfminer import parse_keyword
from unstructured.utils import requires_dependencies

if TYPE_CHECKING:
    pass

# NOTE(alan): Patching this to fix a bug in pdfminer.six. Submitted this PR into pdfminer.six to fix
# the bug: https://github.com/pdfminer/pdfminer.six/pull/885
psparser.PSBaseParser._parse_keyword = parse_keyword  # type: ignore

RE_MULTISPACE_INCLUDING_NEWLINES = re.compile(pattern=r"\s+", flags=re.DOTALL)


def default_hi_res_model(infer_table_structure: bool) -> str:
    # a light config for the hi res model; this is not defined as a constant so that no setting of
    # the default hi res model name is done on importing of this submodule; this allows (if user
    # prefers) for setting env after importing the sub module and changing the default model name

    # if tabler structure is needed we defaul to use yolox for better table detection
    default = "yolox" if infer_table_structure else "yolox_quantized"
    return os.environ.get("UNSTRUCTURED_HI_RES_MODEL_NAME", default)


@process_metadata()
@add_metadata_with_filetype(FileType.PDF)
@add_chunking_strategy()
def partition_pdf(
    filename: str = "",
    file: Optional[Union[BinaryIO, SpooledTemporaryFile]] = None,
    include_page_breaks: bool = False,
    strategy: str = PartitionStrategy.AUTO,
    infer_table_structure: bool = False,
    ocr_languages: Optional[str] = None,  # changing to optional for deprecation
    languages: Optional[List[str]] = None,
    include_metadata: bool = True,  # used by decorator
    metadata_filename: Optional[str] = None,  # used by decorator
    metadata_last_modified: Optional[str] = None,
    chunking_strategy: Optional[str] = None,  # used by decorator
    links: Sequence[Link] = [],
    hi_res_model_name: Optional[str] = None,
    extract_images_in_pdf: bool = False,
    extract_element_types: Optional[List[str]] = None,
    image_output_dir_path: Optional[str] = None,
    extract_to_payload: bool = False,
    **kwargs,
) -> List[Element]:
    """Parses a pdf document into a list of interpreted elements.
    Parameters
    ----------
    filename
        A string defining the target filename path.
    file
        A file-like object as bytes --> open(filename, "rb").
    strategy
        The strategy to use for partitioning the PDF. Valid strategies are "hi_res",
        "ocr_only", and "fast". When using the "hi_res" strategy, the function uses
        a layout detection model to identify document elements. When using the
        "ocr_only" strategy, partition_pdf simply extracts the text from the
        document using OCR and processes it. If the "fast" strategy is used, the text
        is extracted directly from the PDF. The default strategy `auto` will determine
        when a page can be extracted using `fast` mode, otherwise it will fall back to `hi_res`.
    infer_table_structure
        Only applicable if `strategy=hi_res`.
        If True, any Table elements that are extracted will also have a metadata field
        named "text_as_html" where the table's text content is rendered into an html string.
        I.e., rows and cells are preserved.
        Whether True or False, the "text" field is always present in any Table element
        and is the text content of the table (no structure).
    languages
        The languages present in the document, for use in partitioning and/or OCR. To use a language
        with Tesseract, you'll first need to install the appropriate Tesseract language pack.
    metadata_last_modified
        The last modified date for the document.
    hi_res_model_name
        The layout detection model used when partitioning strategy is set to `hi_res`.
    extract_images_in_pdf
        Only applicable if `strategy=hi_res`.
        If True, any detected images will be saved in the path specified by 'image_output_dir_path'
        or stored as base64 encoded data within metadata fields.
        Deprecation Note: This parameter is marked for deprecation. Future versions will use
        'extract_element_types' for broader extraction capabilities.
    extract_element_types
        Only applicable if `strategy=hi_res`.
        Images of the element type(s) specified in this list (e.g., ["Image", "Table"]) will be
        saved in the path specified by 'image_output_dir_path' or stored as base64 encoded data
        within metadata fields.
    extract_to_payload
        Only applicable if `strategy=hi_res`.
        If True, images of the element type(s) defined in 'extract_element_types' will be encoded
        as base64 data and stored in two metadata fields: 'image_base64' and 'image_mime_type'.
        This parameter facilitates the inclusion of element data directly within the payload,
        especially for web-based applications or APIs.
    image_output_dir_path
        Only applicable if `strategy=hi_res` and `extract_to_payload=False`.
        The filesystem path for saving images of the element type(s)
        specified in 'extract_element_types'.
    """

    exactly_one(filename=filename, file=file)

    languages = check_languages(languages, ocr_languages)

    return partition_pdf_or_image(
        filename=filename,
        file=file,
        include_page_breaks=include_page_breaks,
        strategy=strategy,
        infer_table_structure=infer_table_structure,
        languages=languages,
        metadata_last_modified=metadata_last_modified,
        hi_res_model_name=hi_res_model_name,
        extract_images_in_pdf=extract_images_in_pdf,
        extract_element_types=extract_element_types,
        image_output_dir_path=image_output_dir_path,
        extract_to_payload=extract_to_payload,
        **kwargs,
    )


def extractable_elements(
    filename: str = "",
    file: Optional[Union[bytes, IO[bytes]]] = None,
    include_page_breaks: bool = False,
    languages: Optional[List[str]] = None,
    metadata_last_modified: Optional[str] = None,
    **kwargs: Any,
):
    if isinstance(file, bytes):
        file = io.BytesIO(file)
    return _partition_pdf_with_pdfminer(
        filename=filename,
        file=file,
        include_page_breaks=include_page_breaks,
        languages=languages,
        metadata_last_modified=metadata_last_modified,
        **kwargs,
    )


def get_the_last_modification_date_pdf_or_img(
    file: Optional[Union[bytes, BinaryIO, SpooledTemporaryFile]] = None,
    filename: Optional[str] = "",
) -> Union[str, None]:
    last_modification_date = None
    if not file and filename:
        last_modification_date = get_last_modified_date(filename=filename)
    elif not filename and file:
        last_modification_date = get_last_modified_date_from_file(file=file)
    return last_modification_date


@requires_dependencies("unstructured_inference")
def _partition_pdf_or_image_local(
    filename: str = "",
    file: Optional[Union[bytes, BinaryIO]] = None,
    is_image: bool = False,
    infer_table_structure: bool = False,
    include_page_breaks: bool = False,
    languages: Optional[List[str]] = None,
    ocr_mode: str = OCRMode.FULL_PAGE.value,
    model_name: Optional[str] = None,  # to be deprecated in favor of `hi_res_model_name`
    hi_res_model_name: Optional[str] = None,
    pdf_image_dpi: Optional[int] = None,
    metadata_last_modified: Optional[str] = None,
    pdf_text_extractable: bool = False,
    extract_images_in_pdf: bool = False,
    extract_element_types: Optional[List[str]] = None,
    image_output_dir_path: Optional[str] = None,
    extract_to_payload: bool = False,
    analysis: bool = False,
    analyzed_image_output_dir_path: Optional[str] = None,
    **kwargs,
) -> List[Element]:
    """Partition using package installed locally"""
    from unstructured_inference.inference.layout import (
        process_data_with_model,
        process_file_with_model,
    )

    from unstructured.partition.pdf_image.ocr import (
        process_data_with_ocr,
        process_file_with_ocr,
    )
    from unstructured.partition.pdf_image.pdfminer_processing import (
        process_data_with_pdfminer,
        process_file_with_pdfminer,
    )

    if languages is None:
        languages = ["eng"]

    ocr_languages = prepare_languages_for_tesseract(languages)

    hi_res_model_name = (
        hi_res_model_name or model_name or default_hi_res_model(infer_table_structure)
    )
    if pdf_image_dpi is None:
        pdf_image_dpi = 300 if hi_res_model_name == "chipper" else 200
    if (pdf_image_dpi < 300) and (hi_res_model_name == "chipper"):
        logger.warning(
            "The Chipper model performs better when images are rendered with DPI >= 300 "
            f"(currently {pdf_image_dpi}).",
        )

    if file is None:
        inferred_document_layout = process_file_with_model(
            filename,
            is_image=is_image,
            model_name=hi_res_model_name,
            pdf_image_dpi=pdf_image_dpi,
        )

        extracted_layout = (
            process_file_with_pdfminer(filename=filename, dpi=pdf_image_dpi)
            if pdf_text_extractable
            else []
        )

        if analysis:
            annotate_layout_elements(
                inferred_document_layout=inferred_document_layout,
                extracted_layout=extracted_layout,
                filename=filename,
                output_dir_path=analyzed_image_output_dir_path,
                pdf_image_dpi=pdf_image_dpi,
                is_image=is_image,
            )

        # NOTE(christine): merged_document_layout = extracted_layout + inferred_layout
        merged_document_layout = merge_inferred_with_extracted_layout(
            inferred_document_layout=inferred_document_layout,
            extracted_layout=extracted_layout,
        )

        if hi_res_model_name.startswith("chipper"):
            # NOTE(alan): We shouldn't do OCR with chipper
            final_document_layout = merged_document_layout
        else:
            final_document_layout = process_file_with_ocr(
                filename,
                merged_document_layout,
                is_image=is_image,
                infer_table_structure=infer_table_structure,
                ocr_languages=ocr_languages,
                ocr_mode=ocr_mode,
                pdf_image_dpi=pdf_image_dpi,
            )
    else:
        inferred_document_layout = process_data_with_model(
            file,
            is_image=is_image,
            model_name=hi_res_model_name,
            pdf_image_dpi=pdf_image_dpi,
        )
        if hasattr(file, "seek"):
            file.seek(0)

        extracted_layout = (
            process_data_with_pdfminer(file=file, dpi=pdf_image_dpi) if pdf_text_extractable else []
        )

        # NOTE(christine): merged_document_layout = extracted_layout + inferred_layout
        merged_document_layout = merge_inferred_with_extracted_layout(
            inferred_document_layout=inferred_document_layout,
            extracted_layout=extracted_layout,
        )

        if hi_res_model_name.startswith("chipper"):
            # NOTE(alan): We shouldn't do OCR with chipper
            final_document_layout = merged_document_layout
        else:
            if hasattr(file, "seek"):
                file.seek(0)
            final_document_layout = process_data_with_ocr(
                file,
                merged_document_layout,
                is_image=is_image,
                infer_table_structure=infer_table_structure,
                ocr_languages=ocr_languages,
                ocr_mode=ocr_mode,
                pdf_image_dpi=pdf_image_dpi,
            )

    # NOTE(alan): starting with v2, chipper sorts the elements itself.
    if hi_res_model_name == "chipper":
        kwargs["sort_mode"] = SORT_MODE_DONT

    final_document_layout = clean_pdfminer_inner_elements(final_document_layout)

    for page in final_document_layout.pages:
        for el in page.elements:
            el.text = el.text or ""

    elements = document_to_element_list(
        final_document_layout,
        sortable=True,
        include_page_breaks=include_page_breaks,
        last_modification_date=metadata_last_modified,
        # NOTE(crag): do not attempt to derive ListItem's from a layout-recognized "List"
        # block with NLP rules. Otherwise, the assumptions in
        # unstructured.partition.common::layout_list_to_list_items often result in weird chunking.
        infer_list_items=False,
        languages=languages,
        **kwargs,
    )

    extract_element_types = check_element_types_to_extract(extract_element_types)
    #  NOTE(christine): `extract_images_in_pdf` would deprecate
    #  (but continue to support for a while)
    if extract_images_in_pdf:
        save_elements(
            elements=elements,
            element_category_to_save=ElementType.IMAGE,
            filename=filename,
            file=file,
            is_image=is_image,
            pdf_image_dpi=pdf_image_dpi,
            extract_to_payload=extract_to_payload,
            output_dir_path=image_output_dir_path,
        )

    for el_type in extract_element_types:
        if extract_images_in_pdf and el_type == ElementType.IMAGE:
            continue

        save_elements(
            elements=elements,
            element_category_to_save=el_type,
            filename=filename,
            file=file,
            is_image=is_image,
            pdf_image_dpi=pdf_image_dpi,
            extract_to_payload=extract_to_payload,
            output_dir_path=image_output_dir_path,
        )

    out_elements = []
    for el in elements:
        if isinstance(el, PageBreak) and not include_page_breaks:
            continue

        if isinstance(el, Image):
            if (
                not extract_images_in_pdf
                and ElementType.IMAGE not in extract_element_types
                and (el.text is None or len(el.text) < 24 or el.text.find(" ") == -1)
            ):
                # NOTE(crag): small chunks of text from Image elements tend to be garbage
                continue
            else:
                out_elements.append(cast(Element, el))
        # NOTE(crag): this is probably always a Text object, but check for the sake of typing
        elif isinstance(el, Text):
            el.text = re.sub(
                RE_MULTISPACE_INCLUDING_NEWLINES,
                " ",
                el.text or "",
            ).strip()
            # NOTE(alan): with chipper there are parent elements with no text we don't want to
            # filter those out and leave the children orphaned.
            if el.text or isinstance(el, PageBreak) or hi_res_model_name.startswith("chipper"):
                out_elements.append(cast(Element, el))

    return out_elements


def partition_pdf_or_image(
    filename: str = "",
    file: Optional[Union[bytes, BinaryIO, SpooledTemporaryFile]] = None,
    is_image: bool = False,
    include_page_breaks: bool = False,
    strategy: str = PartitionStrategy.AUTO,
    infer_table_structure: bool = False,
    ocr_languages: Optional[str] = None,
    languages: Optional[List[str]] = None,
    metadata_last_modified: Optional[str] = None,
    hi_res_model_name: Optional[str] = None,
    extract_images_in_pdf: bool = False,
    extract_element_types: Optional[List[str]] = None,
    image_output_dir_path: Optional[str] = None,
    extract_to_payload: bool = False,
    **kwargs,
) -> List[Element]:
    """Parses a pdf or image document into a list of interpreted elements."""
    # TODO(alan): Extract information about the filetype to be processed from the template
    # route. Decoding the routing should probably be handled by a single function designed for
    # that task so as routing design changes, those changes are implemented in a single
    # function.

    validate_strategy(strategy, is_image)

    languages = check_languages(languages, ocr_languages)

    last_modification_date = get_the_last_modification_date_pdf_or_img(
        file=file,
        filename=filename,
    )

    extracted_elements = []
    pdf_text_extractable = False
    if not is_image:
        try:
            extracted_elements = extractable_elements(
                filename=filename,
                file=spooled_to_bytes_io_if_needed(file),
                include_page_breaks=include_page_breaks,
                languages=languages,
                metadata_last_modified=metadata_last_modified or last_modification_date,
                **kwargs,
            )
            pdf_text_extractable = any(
                isinstance(el, Text) and el.text.strip() for el in extracted_elements
            )
        except Exception as e:
            logger.error(e)
            logger.warning("PDF text extraction failed, skip text extraction...")

    strategy = determine_pdf_or_image_strategy(
        strategy,
        is_image=is_image,
        pdf_text_extractable=pdf_text_extractable,
        infer_table_structure=infer_table_structure,
        extract_images_in_pdf=extract_images_in_pdf,
        extract_element_types=extract_element_types,
    )

    if file is not None:
        file.seek(0)

    if strategy == PartitionStrategy.HI_RES:
        # NOTE(robinson): Catches a UserWarning that occurs when detectron is called
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            elements = _partition_pdf_or_image_local(
                filename=filename,
                file=spooled_to_bytes_io_if_needed(file),
                is_image=is_image,
                infer_table_structure=infer_table_structure,
                include_page_breaks=include_page_breaks,
                languages=languages,
                metadata_last_modified=metadata_last_modified or last_modification_date,
                hi_res_model_name=hi_res_model_name,
                pdf_text_extractable=pdf_text_extractable,
                extract_images_in_pdf=extract_images_in_pdf,
                extract_element_types=extract_element_types,
                image_output_dir_path=image_output_dir_path,
                extract_to_payload=extract_to_payload,
                **kwargs,
            )
            out_elements = _process_uncategorized_text_elements(elements)

    elif strategy == PartitionStrategy.FAST:
        return extracted_elements

    elif strategy == PartitionStrategy.OCR_ONLY:
        # NOTE(robinson): Catches file conversion warnings when running with PDFs
        with warnings.catch_warnings():
            elements = _partition_pdf_or_image_with_ocr(
                filename=filename,
                file=file,
                include_page_breaks=include_page_breaks,
                languages=languages,
                is_image=is_image,
                metadata_last_modified=metadata_last_modified or last_modification_date,
                **kwargs,
            )
            out_elements = _process_uncategorized_text_elements(elements)

    return out_elements


def _process_uncategorized_text_elements(elements: List[Element]):
    """Processes a list of elements, creating a new list where elements with the
    category `UncategorizedText` are replaced with corresponding
    elements created from their text content."""

    out_elements = []
    for el in elements:
        if hasattr(el, "category") and el.category == ElementType.UNCATEGORIZED_TEXT:
            new_el = element_from_text(cast(Text, el).text)
            new_el.metadata = el.metadata
        else:
            new_el = el
        out_elements.append(new_el)

    return out_elements


@requires_dependencies("pdfminer", "local-inference")
def _partition_pdf_with_pdfminer(
    filename: str,
    file: Optional[IO[bytes]],
    include_page_breaks: bool,
    languages: List[str],
    metadata_last_modified: Optional[str],
    **kwargs: Any,
) -> List[Element]:
    """Partitions a PDF using PDFMiner instead of using a layoutmodel. Used for faster
    processing or detectron2 is not available.

    Implementation is based on the `extract_text` implemenation in pdfminer.six, but
    modified to support tracking page numbers and working with file-like objects.

    ref: https://github.com/pdfminer/pdfminer.six/blob/master/pdfminer/high_level.py
    """
    if languages is None:
        languages = ["eng"]

    exactly_one(filename=filename, file=file)
    if filename:
        with open_filename(filename, "rb") as fp:
            fp = cast(BinaryIO, fp)
            elements = _process_pdfminer_pages(
                fp=fp,
                filename=filename,
                include_page_breaks=include_page_breaks,
                languages=languages,
                metadata_last_modified=metadata_last_modified,
                **kwargs,
            )

    elif file:
        fp = cast(BinaryIO, file)
        elements = _process_pdfminer_pages(
            fp=fp,
            filename=filename,
            include_page_breaks=include_page_breaks,
            languages=languages,
            metadata_last_modified=metadata_last_modified,
            **kwargs,
        )

    return elements


def _extract_text(item: LTItem) -> str:
    """Recursively extracts text from PDFMiner objects to account
    for scenarios where the text is in a sub-container."""
    if hasattr(item, "get_text"):
        return item.get_text()

    elif isinstance(item, LTContainer):
        text = ""
        for child in item:
            text += _extract_text(child) or ""
        return text

    elif isinstance(item, (LTTextBox, LTImage)):
        # TODO(robinson) - Support pulling text out of images
        # https://github.com/pdfminer/pdfminer.six/blob/master/pdfminer/image.py#L90
        return "\n"
    return "\n"


# Some pages with a ICC color space do not follow the pdf spec
# They throw an error when we call interpreter.process_page
# Since we don't need color info, we can just drop it in the pdfminer code
# See #2059
@wrapt.patch_function_wrapper("pdfminer.pdfinterp", "PDFPageInterpreter.init_resources")
def pdfminer_interpreter_init_resources(wrapped, instance, args, kwargs):
    resources = args[0]
    if "ColorSpace" in resources:
        del resources["ColorSpace"]

    return wrapped(resources)


def _process_pdfminer_pages(
    fp: BinaryIO,
    filename: str,
    include_page_breaks: bool,
    languages: List[str],
    metadata_last_modified: Optional[str],
    sort_mode: str = SORT_MODE_XY_CUT,
    **kwargs,
):
    """Uses PDFMiner to split a document into pages and process them."""
    elements: List[Element] = []

    for i, (page, page_layout) in enumerate(open_pdfminer_pages_generator(fp)):
        width, height = page_layout.width, page_layout.height

        page_elements: List[Element] = []
        annotation_list = []

        coordinate_system = PixelSpace(
            width=width,
            height=height,
        )
        if page.annots:
            annotation_list = get_uris(page.annots, height, coordinate_system, i + 1)

        for obj in page_layout:
            x1, y1, x2, y2 = rect_to_bbox(obj.bbox, height)
            bbox = (x1, y1, x2, y2)

            urls_metadata: List[Dict[str, Any]] = []

            if len(annotation_list) > 0 and isinstance(obj, LTTextBox):
                annotations_within_element = check_annotations_within_element(
                    annotation_list,
                    bbox,
                    i + 1,
                )
                _, words = get_word_bounding_box_from_element(obj, height)
                for annot in annotations_within_element:
                    urls_metadata.append(map_bbox_and_index(words, annot))

            if hasattr(obj, "get_text"):
                _text_snippets: List = [obj.get_text()]
            else:
                _text = _extract_text(obj)
                _text_snippets = re.split(PARAGRAPH_PATTERN, _text)

            for _text in _text_snippets:
                _text, moved_indices = clean_extra_whitespace_with_index_run(_text)
                if _text.strip():
                    points = ((x1, y1), (x1, y2), (x2, y2), (x2, y1))
                    element = element_from_text(
                        _text,
                        coordinates=points,
                        coordinate_system=coordinate_system,
                    )
                    coordinates_metadata = CoordinatesMetadata(
                        points=points,
                        system=coordinate_system,
                    )
                    links = _get_links_from_urls_metadata(urls_metadata, moved_indices)

                    element.metadata = ElementMetadata(
                        filename=filename,
                        page_number=i + 1,
                        coordinates=coordinates_metadata,
                        last_modified=metadata_last_modified,
                        links=links,
                        languages=languages,
                    )
                    element.metadata.detection_origin = "pdfminer"
                    page_elements.append(element)

        page_elements = _combine_list_elements(page_elements, coordinate_system)

        # NOTE(crag, christine): always do the basic sort first for determinsitic order across
        # python versions.
        sorted_page_elements = sort_page_elements(page_elements, SORT_MODE_BASIC)
        if sort_mode != SORT_MODE_BASIC:
            sorted_page_elements = sort_page_elements(sorted_page_elements, sort_mode)

        elements += sorted_page_elements

        if include_page_breaks:
            elements.append(PageBreak(text=""))

    return elements


def _combine_list_elements(
    elements: List[Element], coordinate_system: Union[PixelSpace, PointSpace]
) -> List[Element]:
    """Combine elements that should be considered a single ListItem element."""
    tmp_element = None
    updated_elements: List[Element] = []
    for element in elements:
        if isinstance(element, ListItem):
            tmp_element = element
            tmp_text = element.text
            tmp_coords = element.metadata.coordinates
        elif tmp_element and check_coords_within_boundary(
            coordinates=element.metadata.coordinates,
            boundary=tmp_coords,
        ):
            tmp_element.text = f"{tmp_text} {element.text}"
            # replace "element" with the corrected element
            element = _combine_coordinates_into_element1(
                element1=tmp_element,
                element2=element,
                coordinate_system=coordinate_system,
            )
            # remove previously added ListItem element with incomplete text
            updated_elements.pop()
        updated_elements.append(element)
    return updated_elements


def _get_links_from_urls_metadata(
    urls_metadata: List[Dict[str, Any]], moved_indices: np.ndarray
) -> List[Link]:
    """Extracts links from a list of URL metadata."""
    links: List[Link] = []
    for url in urls_metadata:
        with contextlib.suppress(IndexError):
            links.append(
                {
                    "text": url["text"],
                    "url": url["uri"],
                    "start_index": index_adjustment_after_clean_extra_whitespace(
                        url["start_index"],
                        moved_indices,
                    ),
                },
            )
    return links


def _combine_coordinates_into_element1(
    element1: Element, element2: Element, coordinate_system: Union[PixelSpace, PointSpace]
) -> Element:
    """Combine the coordiantes of two elements and apply the updated coordiantes to `elements1`"""
    x1 = min(
        element1.metadata.coordinates.points[0][0],
        element2.metadata.coordinates.points[0][0],
    )
    x2 = max(
        element1.metadata.coordinates.points[2][0],
        element2.metadata.coordinates.points[2][0],
    )
    y1 = min(
        element1.metadata.coordinates.points[0][1],
        element2.metadata.coordinates.points[0][1],
    )
    y2 = max(
        element1.metadata.coordinates.points[1][1],
        element2.metadata.coordinates.points[1][1],
    )
    points = ((x1, y1), (x1, y2), (x2, y2), (x2, y1))
    element1.metadata.coordinates = CoordinatesMetadata(
        points=points,
        system=coordinate_system,
    )
    return element1


def convert_pdf_to_images(
    filename: str = "",
    file: Optional[Union[bytes, IO[bytes]]] = None,
    chunk_size: int = 10,
) -> Iterator[PILImage.Image]:
    # Convert a PDF in small chunks of pages at a time (e.g. 1-10, 11-20... and so on)
    exactly_one(filename=filename, file=file)
    if file is not None:
        f_bytes = convert_to_bytes(file)
        info = pdf2image.pdfinfo_from_bytes(f_bytes)
    else:
        f_bytes = None
        info = pdf2image.pdfinfo_from_path(filename)

    total_pages = info["Pages"]
    for start_page in range(1, total_pages + 1, chunk_size):
        end_page = min(start_page + chunk_size - 1, total_pages)
        if f_bytes is not None:
            chunk_images = pdf2image.convert_from_bytes(
                f_bytes,
                first_page=start_page,
                last_page=end_page,
            )
        else:
            chunk_images = pdf2image.convert_from_path(
                filename,
                first_page=start_page,
                last_page=end_page,
            )

        for image in chunk_images:
            yield image


@requires_dependencies("unstructured_pytesseract", "unstructured_inference")
def _partition_pdf_or_image_with_ocr(
    filename: str = "",
    file: Optional[Union[bytes, IO[bytes]]] = None,
    include_page_breaks: bool = False,
    languages: Optional[List[str]] = ["eng"],
    is_image: bool = False,
    metadata_last_modified: Optional[str] = None,
    **kwargs,
):
    """Partitions an image or PDF using OCR. For PDFs, each page is converted
    to an image prior to processing."""

    elements = []
    if is_image:
        images = []
        image = PILImage.open(file) if file is not None else PILImage.open(filename)
        images.append(image)

        for i, image in enumerate(images):
            page_elements = _partition_pdf_or_image_with_ocr_from_image(
                image=image,
                languages=languages,
                page_number=i + 1,
                include_page_breaks=include_page_breaks,
                metadata_last_modified=metadata_last_modified,
                **kwargs,
            )
            elements.extend(page_elements)
    else:
        page_number = 0
        for image in convert_pdf_to_images(filename, file):
            page_number += 1
            page_elements = _partition_pdf_or_image_with_ocr_from_image(
                image=image,
                languages=languages,
                page_number=page_number,
                include_page_breaks=include_page_breaks,
                metadata_last_modified=metadata_last_modified,
                **kwargs,
            )
            elements.extend(page_elements)

    return elements


def _partition_pdf_or_image_with_ocr_from_image(
    image: PILImage,
    languages: Optional[List[str]] = None,
    page_number: int = 1,
    include_page_breaks: bool = False,
    metadata_last_modified: Optional[str] = None,
    sort_mode: str = SORT_MODE_XY_CUT,
    **kwargs,
) -> List[Element]:
    """Extract `unstructured` elements from an image using OCR and perform partitioning."""

    from unstructured.partition.pdf_image.ocr import (
        get_layout_elements_from_ocr,
        get_ocr_agent,
    )

    ocr_agent = get_ocr_agent()
    ocr_languages = prepare_languages_for_tesseract(languages)

    # NOTE(christine): `unstructured_pytesseract.image_to_string()` returns sorted text
    if ocr_agent == OCR_AGENT_TESSERACT:
        sort_mode = SORT_MODE_DONT

    ocr_data = get_layout_elements_from_ocr(
        image=image,
        ocr_languages=ocr_languages,
        ocr_agent=ocr_agent,
    )

    metadata = ElementMetadata(
        last_modified=metadata_last_modified,
        filetype=image.format,
        page_number=page_number,
        languages=languages,
    )

    page_elements = ocr_data_to_elements(
        ocr_data,
        image_size=image.size,
        common_metadata=metadata,
    )

    sorted_page_elements = page_elements
    if sort_mode != SORT_MODE_DONT:
        sorted_page_elements = sort_page_elements(page_elements, sort_mode)

    if include_page_breaks:
        sorted_page_elements.append(PageBreak(text=""))

    return page_elements


def check_coords_within_boundary(
    coordinates: CoordinatesMetadata,
    boundary: CoordinatesMetadata,
    horizontal_threshold: float = 0.2,
    vertical_threshold: float = 0.3,
) -> bool:
    """Checks if the coordinates are within boundary thresholds.
    Parameters
    ----------
    coordinates
        a CoordinatesMetadata input
    boundary
        a CoordinatesMetadata to compare against
    vertical_threshold
        a float ranges from [0,1] to scale the vertical (y-axis) boundary
    horizontal_threshold
        a float ranges from [0,1] to scale the horizontal (x-axis) boundary
    """
    if not coord_has_valid_points(coordinates) and not coord_has_valid_points(boundary):
        trace_logger.detail(  # type: ignore
            f"coordinates {coordinates} and boundary {boundary} did not pass validation",
        )
        return False

    boundary_x_min = boundary.points[0][0]
    boundary_x_max = boundary.points[2][0]
    boundary_y_min = boundary.points[0][1]
    boundary_y_max = boundary.points[1][1]

    line_width = boundary_x_max - boundary_x_min
    line_height = boundary_y_max - boundary_y_min

    x_within_boundary = (
        (coordinates.points[0][0] > boundary_x_min - (horizontal_threshold * line_width))
        and (coordinates.points[2][0] < boundary_x_max + (horizontal_threshold * line_width))
        and (coordinates.points[0][0] >= boundary_x_min)
    )
    y_within_boundary = (
        coordinates.points[0][1] < boundary_y_max + (vertical_threshold * line_height)
    ) and (coordinates.points[0][1] > boundary_y_min - (vertical_threshold * line_height))

    return x_within_boundary and y_within_boundary


def get_uris(
    annots: Union[PDFObjRef, List[PDFObjRef]],
    height: float,
    coordinate_system: Union[PixelSpace, PointSpace],
    page_number: int,
) -> List[Dict[str, Any]]:
    """
    Extracts URI annotations from a single or a list of PDF object references on a specific page.
    The type of annots (list or not) depends on the pdf formatting. The function detectes the type
    of annots and then pass on to get_uris_from_annots function as a List.

    Args:
        annots (Union[PDFObjRef, List[PDFObjRef]]): A single or a list of PDF object references
            representing annotations on the page.
        height (float): The height of the page in the specified coordinate system.
        coordinate_system (Union[PixelSpace, PointSpace]): The coordinate system used to represent
            the annotations' coordinates.
        page_number (int): The page number from which to extract annotations.

    Returns:
        List[dict]: A list of dictionaries, each containing information about a URI annotation,
        including its coordinates, bounding box, type, URI link, and page number.
    """
    if isinstance(annots, List):
        return get_uris_from_annots(annots, height, coordinate_system, page_number)
    resolved_annots = annots.resolve()
    if resolved_annots is None:
        return []
    return get_uris_from_annots(resolved_annots, height, coordinate_system, page_number)


def get_uris_from_annots(
    annots: List[PDFObjRef],
    height: Union[int, float],
    coordinate_system: Union[PixelSpace, PointSpace],
    page_number: int,
) -> List[Dict[str, Any]]:
    """
    Extracts URI annotations from a list of PDF object references.

    Args:
        annots (List[PDFObjRef]): A list of PDF object references representing annotations on
            a page.
        height (Union[int, float]): The height of the page in the specified coordinate system.
        coordinate_system (Union[PixelSpace, PointSpace]): The coordinate system used to represent
            the annotations' coordinates.
        page_number (int): The page number from which to extract annotations.

    Returns:
        List[dict]: A list of dictionaries, each containing information about a URI annotation,
        including its coordinates, bounding box, type, URI link, and page number.
    """
    annotation_list = []
    for annotation in annots:
        # Check annotation is valid for extraction
        annotation_dict = try_resolve(annotation)
        if not isinstance(annotation_dict, dict):
            continue
        subtype = annotation_dict["Subtype"] if "Subtype" in annotation_dict else None
        if not subtype or isinstance(subtype, PDFObjRef) or str(subtype) != "/'Link'":
            continue
        # Extract bounding box and update coordinates
        rect = annotation_dict["Rect"] if "Rect" in annotation_dict else None
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


def calculate_intersection_area(
    bbox1: Tuple[float, float, float, float],
    bbox2: Tuple[float, float, float, float],
) -> float:
    """
    Calculate the area of intersection between two bounding boxes.

    Args:
        bbox1 (Tuple[float, float, float, float]): The coordinates of the first bounding box
            in the format (x1, y1, x2, y2).
        bbox2 (Tuple[float, float, float, float]): The coordinates of the second bounding box
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


def calculate_bbox_area(bbox: Tuple[float, float, float, float]) -> float:
    """
    Calculate the area of a bounding box.

    Args:
        bbox (Tuple[float, float, float, float]): The coordinates of the bounding box
            in the format (x1, y1, x2, y2).

    Returns:
        float: The area of the bounding box, computed as the product of its width and height.
    """
    x1, y1, x2, y2 = bbox
    area = (x2 - x1) * (y2 - y1)
    return area


def check_annotations_within_element(
    annotation_list: List[Dict[str, Any]],
    element_bbox: Tuple[float, float, float, float],
    page_number: int,
    threshold: float = 0.9,
) -> List[Dict[str, Any]]:
    """
    Filter annotations that are within or highly overlap with a specified element on a page.

    Args:
        annotation_list (List[Dict[str,Any]]): A list of dictionaries, each containing information
            about an annotation.
        element_bbox (Tuple[float, float, float, float]): The bounding box coordinates of the
            specified element in the bbox format (x1, y1, x2, y2).
        page_number (int): The page number to which the annotations and element belong.
        threshold (float, optional): The threshold value (between 0.0 and 1.0) that determines
            the minimum overlap required for an annotation to be considered within the element.
            Default is 0.9.

    Returns:
        List[Dict[str,Any]]: A list of dictionaries containing information about annotations
        that are within or highly overlap with the specified element on the given page, based on
        the specified threshold.
    """
    annotations_within_element = []
    for annotation in annotation_list:
        if annotation["page_number"] == page_number:
            annotation_bbox_size = calculate_bbox_area(annotation["bbox"])
            if annotation_bbox_size and (
                calculate_intersection_area(element_bbox, annotation["bbox"]) / annotation_bbox_size
                > threshold
            ):
                annotations_within_element.append(annotation)
    return annotations_within_element


def get_word_bounding_box_from_element(
    obj: LTTextBox,
    height: float,
) -> Tuple[List[LTChar], List[Dict[str, Any]]]:
    """
    Extracts characters and word bounding boxes from a PDF text element.

    Args:
        obj (LTTextBox): The PDF text element from which to extract characters and words.
        height (float): The height of the page in the specified coordinate system.

    Returns:
        Tuple[List[LTChar], List[Dict[str,Any]]]: A tuple containing two lists:
            - List[LTChar]: A list of LTChar objects representing individual characters.
            - List[Dict[str,Any]]]: A list of dictionaries, each containing information about
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
        text_len += len(text_line)
    return characters, words


def map_bbox_and_index(words: List[Dict[str, Any]], annot: Dict[str, Any]):
    """
    Maps a bounding box annotation to the corresponding text and start index within a list of words.

    Args:
        words (List[Dict[str,Any]]): A list of dictionaries, each containing information about
            a word, including its text, bounding box, and start index.
        annot (Dict[str,Any]): The annotation dictionary to be mapped, which will be updated with
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
