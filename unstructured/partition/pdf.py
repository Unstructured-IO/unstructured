from __future__ import annotations

import contextlib
import copy
import io
import os
import re
import warnings
from pathlib import Path
from typing import IO, TYPE_CHECKING, Any, Optional, cast

import numpy as np
import wrapt
from pdfminer.layout import LTContainer, LTImage, LTItem, LTTextBox
from pdfminer.utils import open_filename
from pi_heif import register_heif_opener
from PIL import Image as PILImage
from pypdf import PdfReader
from unstructured_inference.inference.layout import DocumentLayout
from unstructured_inference.inference.layoutelement import LayoutElement

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
    Title,
    process_metadata,
)
from unstructured.errors import PageCountExceededError
from unstructured.file_utils.filetype import add_metadata_with_filetype
from unstructured.file_utils.model import FileType
from unstructured.logger import logger, trace_logger
from unstructured.nlp.patterns import PARAGRAPH_PATTERN
from unstructured.partition.common.common import (
    add_element_metadata,
    exactly_one,
    get_page_image_metadata,
    normalize_layout_element,
    ocr_data_to_elements,
    spooled_to_bytes_io_if_needed,
)
from unstructured.partition.common.lang import (
    check_language_args,
    prepare_languages_for_tesseract,
    tesseract_to_paddle_language,
)
from unstructured.partition.common.metadata import get_last_modified_date
from unstructured.partition.pdf_image.analysis.layout_dump import (
    ExtractedLayoutDumper,
    FinalLayoutDumper,
    ObjectDetectionLayoutDumper,
    OCRLayoutDumper,
)
from unstructured.partition.pdf_image.analysis.tools import save_analysis_artifiacts
from unstructured.partition.pdf_image.form_extraction import run_form_extraction
from unstructured.partition.pdf_image.pdf_image_utils import (
    check_element_types_to_extract,
    convert_pdf_to_images,
    save_elements,
)
from unstructured.partition.pdf_image.pdfminer_processing import (
    check_annotations_within_element,
    clean_pdfminer_inner_elements,
    get_links_in_element,
    get_uris,
    get_words_from_obj,
    map_bbox_and_index,
    merge_inferred_with_extracted_layout,
)
from unstructured.partition.pdf_image.pdfminer_utils import (
    open_pdfminer_pages_generator,
    rect_to_bbox,
)
from unstructured.partition.strategies import determine_pdf_or_image_strategy, validate_strategy
from unstructured.partition.text import element_from_text
from unstructured.partition.utils.config import env_config
from unstructured.partition.utils.constants import (
    OCR_AGENT_PADDLE,
    SORT_MODE_BASIC,
    SORT_MODE_DONT,
    SORT_MODE_XY_CUT,
    OCRMode,
    PartitionStrategy,
)
from unstructured.partition.utils.sorting import coord_has_valid_points, sort_page_elements
from unstructured.patches.pdfminer import patch_psparser
from unstructured.utils import first, requires_dependencies

if TYPE_CHECKING:
    pass


# Correct a bug that was introduced by a previous patch to
# pdfminer.six, causing needless and unsuccessful repairing of PDFs
# which were not actually broken.
patch_psparser()


RE_MULTISPACE_INCLUDING_NEWLINES = re.compile(pattern=r"\s+", flags=re.DOTALL)


@requires_dependencies("unstructured_inference")
def default_hi_res_model() -> str:
    # a light config for the hi res model; this is not defined as a constant so that no setting of
    # the default hi res model name is done on importing of this submodule; this allows (if user
    # prefers) for setting env after importing the sub module and changing the default model name

    from unstructured_inference.models.base import DEFAULT_MODEL

    return os.environ.get("UNSTRUCTURED_HI_RES_MODEL_NAME", DEFAULT_MODEL)


@process_metadata()
@add_metadata_with_filetype(FileType.PDF)
@add_chunking_strategy
def partition_pdf(
    filename: Optional[str] = None,
    file: Optional[IO[bytes]] = None,
    include_page_breaks: bool = False,
    strategy: str = PartitionStrategy.AUTO,
    infer_table_structure: bool = False,
    ocr_languages: Optional[str] = None,  # changing to optional for deprecation
    languages: Optional[list[str]] = None,
    metadata_filename: Optional[str] = None,  # used by decorator
    metadata_last_modified: Optional[str] = None,
    chunking_strategy: Optional[str] = None,  # used by decorator
    hi_res_model_name: Optional[str] = None,
    extract_images_in_pdf: bool = False,
    extract_image_block_types: Optional[list[str]] = None,
    extract_image_block_output_dir: Optional[str] = None,
    extract_image_block_to_payload: bool = False,
    starting_page_number: int = 1,
    extract_forms: bool = False,
    form_extraction_skip_tables: bool = True,
    **kwargs: Any,
) -> list[Element]:
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
        If True, any detected images will be saved in the path specified by
        'extract_image_block_output_dir' or stored as base64 encoded data within metadata fields.
        Deprecation Note: This parameter is marked for deprecation. Future versions will use
        'extract_image_block_types' for broader extraction capabilities.
    extract_image_block_types
        Only applicable if `strategy=hi_res`.
        Images of the element type(s) specified in this list (e.g., ["Image", "Table"]) will be
        saved in the path specified by 'extract_image_block_output_dir' or stored as base64
        encoded data within metadata fields.
    extract_image_block_to_payload
        Only applicable if `strategy=hi_res`.
        If True, images of the element type(s) defined in 'extract_image_block_types' will be
        encoded as base64 data and stored in two metadata fields: 'image_base64' and
        'image_mime_type'.
        This parameter facilitates the inclusion of element data directly within the payload,
        especially for web-based applications or APIs.
    extract_image_block_output_dir
        Only applicable if `strategy=hi_res` and `extract_image_block_to_payload=False`.
        The filesystem path for saving images of the element type(s)
        specified in 'extract_image_block_types'.
    extract_forms
        Whether the form extraction logic should be run
        (results in adding FormKeysValues elements to output).
    form_extraction_skip_tables
        Whether the form extraction logic should ignore regions designated as Tables.
    """

    exactly_one(filename=filename, file=file)

    languages = check_language_args(languages or [], ocr_languages)

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
        extract_image_block_types=extract_image_block_types,
        extract_image_block_output_dir=extract_image_block_output_dir,
        extract_image_block_to_payload=extract_image_block_to_payload,
        starting_page_number=starting_page_number,
        extract_forms=extract_forms,
        form_extraction_skip_tables=form_extraction_skip_tables,
        **kwargs,
    )


def partition_pdf_or_image(
    filename: str = "",
    file: Optional[bytes | IO[bytes]] = None,
    is_image: bool = False,
    include_page_breaks: bool = False,
    strategy: str = PartitionStrategy.AUTO,
    infer_table_structure: bool = False,
    languages: Optional[list[str]] = None,
    metadata_last_modified: Optional[str] = None,
    hi_res_model_name: Optional[str] = None,
    extract_images_in_pdf: bool = False,
    extract_image_block_types: Optional[list[str]] = None,
    extract_image_block_output_dir: Optional[str] = None,
    extract_image_block_to_payload: bool = False,
    starting_page_number: int = 1,
    extract_forms: bool = False,
    form_extraction_skip_tables: bool = True,
    **kwargs: Any,
) -> list[Element]:
    """Parses a pdf or image document into a list of interpreted elements."""
    # TODO(alan): Extract information about the filetype to be processed from the template
    # route. Decoding the routing should probably be handled by a single function designed for
    # that task so as routing design changes, those changes are implemented in a single
    # function.

    if languages is None:
        languages = ["eng"]

    # init ability to process .heic files
    register_heif_opener()

    validate_strategy(strategy, is_image)

    last_modified = get_last_modified_date(filename) if filename else None

    extracted_elements = []
    pdf_text_extractable = False
    if not is_image:
        try:
            extracted_elements = extractable_elements(
                filename=filename,
                file=spooled_to_bytes_io_if_needed(file),
                languages=languages,
                metadata_last_modified=metadata_last_modified or last_modified,
                starting_page_number=starting_page_number,
                **kwargs,
            )
            pdf_text_extractable = any(
                isinstance(el, Text) and el.text.strip()
                for page_elements in extracted_elements
                for el in page_elements
            )
        except Exception as e:
            logger.debug(e)
            logger.info("PDF text extraction failed, skip text extraction...")

    strategy = determine_pdf_or_image_strategy(
        strategy,
        is_image=is_image,
        pdf_text_extractable=pdf_text_extractable,
        infer_table_structure=infer_table_structure,
        extract_images_in_pdf=extract_images_in_pdf,
        extract_image_block_types=extract_image_block_types,
    )

    if file is not None:
        file.seek(0)

    ocr_languages = prepare_languages_for_tesseract(languages)
    if env_config.OCR_AGENT == OCR_AGENT_PADDLE:
        ocr_languages = tesseract_to_paddle_language(ocr_languages)

    if strategy == PartitionStrategy.HI_RES:
        # NOTE(robinson): Catches a UserWarning that occurs when detection is called
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            elements = _partition_pdf_or_image_local(
                filename=filename,
                file=spooled_to_bytes_io_if_needed(file),
                is_image=is_image,
                infer_table_structure=infer_table_structure,
                include_page_breaks=include_page_breaks,
                languages=languages,
                ocr_languages=ocr_languages,
                metadata_last_modified=metadata_last_modified or last_modified,
                hi_res_model_name=hi_res_model_name,
                pdf_text_extractable=pdf_text_extractable,
                extract_images_in_pdf=extract_images_in_pdf,
                extract_image_block_types=extract_image_block_types,
                extract_image_block_output_dir=extract_image_block_output_dir,
                extract_image_block_to_payload=extract_image_block_to_payload,
                starting_page_number=starting_page_number,
                extract_forms=extract_forms,
                form_extraction_skip_tables=form_extraction_skip_tables,
                **kwargs,
            )
            out_elements = _process_uncategorized_text_elements(elements)

    elif strategy == PartitionStrategy.FAST:
        out_elements = _partition_pdf_with_pdfparser(
            extracted_elements=extracted_elements,
            include_page_breaks=include_page_breaks,
            **kwargs,
        )

        return out_elements

    elif strategy == PartitionStrategy.OCR_ONLY:
        # NOTE(robinson): Catches file conversion warnings when running with PDFs
        with warnings.catch_warnings():
            elements = _partition_pdf_or_image_with_ocr(
                filename=filename,
                file=file,
                include_page_breaks=include_page_breaks,
                languages=languages,
                ocr_languages=ocr_languages,
                is_image=is_image,
                metadata_last_modified=metadata_last_modified or last_modified,
                starting_page_number=starting_page_number,
                **kwargs,
            )
            out_elements = _process_uncategorized_text_elements(elements)

    return out_elements


def extractable_elements(
    filename: str = "",
    file: Optional[bytes | IO[bytes]] = None,
    languages: Optional[list[str]] = None,
    metadata_last_modified: Optional[str] = None,
    starting_page_number: int = 1,
    **kwargs: Any,
) -> list[list[Element]]:
    if isinstance(file, bytes):
        file = io.BytesIO(file)
    return _partition_pdf_with_pdfminer(
        filename=filename,
        file=file,
        languages=languages,
        metadata_last_modified=metadata_last_modified,
        starting_page_number=starting_page_number,
        **kwargs,
    )


def _partition_pdf_with_pdfminer(
    filename: str,
    file: Optional[IO[bytes]],
    languages: list[str],
    metadata_last_modified: Optional[str],
    starting_page_number: int = 1,
    **kwargs: Any,
) -> list[list[Element]]:
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
            fp = cast(IO[bytes], fp)
            elements = _process_pdfminer_pages(
                fp=fp,
                filename=filename,
                languages=languages,
                metadata_last_modified=metadata_last_modified,
                starting_page_number=starting_page_number,
                **kwargs,
            )

    elif file:
        elements = _process_pdfminer_pages(
            fp=file,
            filename=filename,
            languages=languages,
            metadata_last_modified=metadata_last_modified,
            starting_page_number=starting_page_number,
            **kwargs,
        )

    return elements


@requires_dependencies("pdfminer")
def _process_pdfminer_pages(
    fp: IO[bytes],
    filename: str,
    languages: list[str],
    metadata_last_modified: Optional[str],
    annotation_threshold: Optional[float] = env_config.PDF_ANNOTATION_THRESHOLD,
    starting_page_number: int = 1,
    **kwargs,
) -> list[list[Element]]:
    """Uses PDFMiner to split a document into pages and process them."""

    elements = []

    for page_number, (page, page_layout) in enumerate(
        open_pdfminer_pages_generator(fp), start=starting_page_number
    ):
        width, height = page_layout.width, page_layout.height

        page_elements: list[Element] = []
        annotation_list = []

        coordinate_system = PixelSpace(
            width=width,
            height=height,
        )
        if page.annots:
            annotation_list = get_uris(page.annots, height, coordinate_system, page_number)

        for obj in page_layout:
            x1, y1, x2, y2 = rect_to_bbox(obj.bbox, height)
            bbox = (x1, y1, x2, y2)

            urls_metadata: list[dict[str, Any]] = []

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
                _text_snippets: list[str] = [obj.get_text()]
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
                        page_number=page_number,
                        coordinates=coordinates_metadata,
                        last_modified=metadata_last_modified,
                        links=links,
                        languages=languages,
                    )
                    element.metadata.detection_origin = "pdfminer"
                    page_elements.append(element)

        page_elements = _combine_list_elements(page_elements, coordinate_system)
        elements.append(page_elements)

    return elements


def _get_pdf_page_number(
    filename: str = "",
    file: Optional[bytes | IO[bytes]] = None,
) -> int:
    if file:
        number_of_pages = PdfReader(file).get_num_pages()
        file.seek(0)
    elif filename:
        number_of_pages = PdfReader(filename).get_num_pages()
    else:
        raise ValueError("Either 'file' or 'filename' must be provided.")
    return number_of_pages


def check_pdf_hi_res_max_pages_exceeded(
    filename: str = "",
    file: Optional[bytes | IO[bytes]] = None,
    pdf_hi_res_max_pages: int = None,
) -> None:
    """Checks whether PDF exceeds pdf_hi_res_max_pages limit."""
    if pdf_hi_res_max_pages:
        document_pages = _get_pdf_page_number(filename=filename, file=file)
        if document_pages > pdf_hi_res_max_pages:
            raise PageCountExceededError(
                document_pages=document_pages, pdf_hi_res_max_pages=pdf_hi_res_max_pages
            )


@requires_dependencies("unstructured_inference")
def _partition_pdf_or_image_local(
    filename: str = "",
    file: Optional[bytes | IO[bytes]] = None,
    is_image: bool = False,
    infer_table_structure: bool = False,
    include_page_breaks: bool = False,
    languages: Optional[list[str]] = None,
    ocr_languages: Optional[str] = None,
    ocr_mode: str = OCRMode.FULL_PAGE.value,
    model_name: Optional[str] = None,  # to be deprecated in favor of `hi_res_model_name`
    hi_res_model_name: Optional[str] = None,
    pdf_image_dpi: Optional[int] = None,
    metadata_last_modified: Optional[str] = None,
    pdf_text_extractable: bool = False,
    extract_images_in_pdf: bool = False,
    extract_image_block_types: Optional[list[str]] = None,
    extract_image_block_output_dir: Optional[str] = None,
    extract_image_block_to_payload: bool = False,
    analysis: bool = False,
    analyzed_image_output_dir_path: Optional[str] = None,
    starting_page_number: int = 1,
    extract_forms: bool = False,
    form_extraction_skip_tables: bool = True,
    pdf_hi_res_max_pages: Optional[int] = None,
    **kwargs: Any,
) -> list[Element]:
    """Partition using package installed locally"""
    from unstructured_inference.inference.layout import (
        process_data_with_model,
        process_file_with_model,
    )

    from unstructured.partition.pdf_image.ocr import process_data_with_ocr, process_file_with_ocr
    from unstructured.partition.pdf_image.pdfminer_processing import (
        process_data_with_pdfminer,
        process_file_with_pdfminer,
    )

    if not is_image:
        check_pdf_hi_res_max_pages_exceeded(
            filename=filename, file=file, pdf_hi_res_max_pages=pdf_hi_res_max_pages
        )

    hi_res_model_name = hi_res_model_name or model_name or default_hi_res_model()
    if pdf_image_dpi is None:
        pdf_image_dpi = 200

    od_model_layout_dumper: Optional[ObjectDetectionLayoutDumper] = None
    extracted_layout_dumper: Optional[ExtractedLayoutDumper] = None
    ocr_layout_dumper: Optional[OCRLayoutDumper] = None
    final_layout_dumper: Optional[FinalLayoutDumper] = None

    skip_analysis_dump = env_config.ANALYSIS_DUMP_OD_SKIP

    if file is None:
        inferred_document_layout = process_file_with_model(
            filename,
            is_image=is_image,
            model_name=hi_res_model_name,
            pdf_image_dpi=pdf_image_dpi,
        )

        extracted_layout, layouts_links = (
            process_file_with_pdfminer(filename=filename, dpi=pdf_image_dpi)
            if pdf_text_extractable
            else ([], [])
        )

        if analysis:
            if not analyzed_image_output_dir_path:
                if env_config.GLOBAL_WORKING_DIR_ENABLED:
                    analyzed_image_output_dir_path = str(
                        Path(env_config.GLOBAL_WORKING_PROCESS_DIR) / "annotated"
                    )
                else:
                    analyzed_image_output_dir_path = str(Path.cwd() / "annotated")
            os.makedirs(analyzed_image_output_dir_path, exist_ok=True)
            if not skip_analysis_dump:
                od_model_layout_dumper = ObjectDetectionLayoutDumper(
                    layout=inferred_document_layout,
                    model_name=hi_res_model_name,
                )
                extracted_layout_dumper = ExtractedLayoutDumper(
                    layout=[layout.as_list() for layout in extracted_layout],
                )
                ocr_layout_dumper = OCRLayoutDumper()
        # NOTE(christine): merged_document_layout = extracted_layout + inferred_layout
        merged_document_layout = merge_inferred_with_extracted_layout(
            inferred_document_layout=inferred_document_layout,
            extracted_layout=extracted_layout,
            hi_res_model_name=hi_res_model_name,
        )

        final_document_layout = process_file_with_ocr(
            filename,
            merged_document_layout,
            extracted_layout=extracted_layout,
            is_image=is_image,
            infer_table_structure=infer_table_structure,
            ocr_languages=ocr_languages,
            ocr_mode=ocr_mode,
            pdf_image_dpi=pdf_image_dpi,
            ocr_layout_dumper=ocr_layout_dumper,
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

        extracted_layout, layouts_links = (
            process_data_with_pdfminer(file=file, dpi=pdf_image_dpi)
            if pdf_text_extractable
            else ([], [])
        )

        if analysis:
            if not analyzed_image_output_dir_path:
                if env_config.GLOBAL_WORKING_DIR_ENABLED:
                    analyzed_image_output_dir_path = str(
                        Path(env_config.GLOBAL_WORKING_PROCESS_DIR) / "annotated"
                    )
                else:
                    analyzed_image_output_dir_path = str(Path.cwd() / "annotated")
            if not skip_analysis_dump:
                od_model_layout_dumper = ObjectDetectionLayoutDumper(
                    layout=inferred_document_layout,
                    model_name=hi_res_model_name,
                )
                extracted_layout_dumper = ExtractedLayoutDumper(
                    layout=[layout.as_list() for layout in extracted_layout],
                )
                ocr_layout_dumper = OCRLayoutDumper()

        # NOTE(christine): merged_document_layout = extracted_layout + inferred_layout
        merged_document_layout = merge_inferred_with_extracted_layout(
            inferred_document_layout=inferred_document_layout,
            extracted_layout=extracted_layout,
            hi_res_model_name=hi_res_model_name,
        )

        if hasattr(file, "seek"):
            file.seek(0)
        final_document_layout = process_data_with_ocr(
            file,
            merged_document_layout,
            extracted_layout=extracted_layout,
            is_image=is_image,
            infer_table_structure=infer_table_structure,
            ocr_languages=ocr_languages,
            ocr_mode=ocr_mode,
            pdf_image_dpi=pdf_image_dpi,
            ocr_layout_dumper=ocr_layout_dumper,
        )

    # vectorization of the data structure ends here
    final_document_layout = clean_pdfminer_inner_elements(final_document_layout)

    for page in final_document_layout.pages:
        for el in page.elements:
            el.text = el.text or ""

    elements = document_to_element_list(
        final_document_layout,
        sortable=True,
        include_page_breaks=include_page_breaks,
        last_modification_date=metadata_last_modified,
        # NOTE(crag): do not attempt to derive ListItem's from a layout-recognized "list"
        # block with NLP rules. Otherwise, the assumptions in
        # unstructured.partition.common::layout_list_to_list_items often result in weird chunking.
        infer_list_items=False,
        languages=languages,
        starting_page_number=starting_page_number,
        layouts_links=layouts_links,
        **kwargs,
    )

    extract_image_block_types = check_element_types_to_extract(extract_image_block_types)
    #  NOTE(christine): `extract_images_in_pdf` would deprecate
    #  (but continue to support for a while)
    if extract_images_in_pdf:
        save_elements(
            elements=elements,
            starting_page_number=starting_page_number,
            element_category_to_save=ElementType.IMAGE,
            filename=filename,
            file=file,
            is_image=is_image,
            pdf_image_dpi=pdf_image_dpi,
            extract_image_block_to_payload=extract_image_block_to_payload,
            output_dir_path=extract_image_block_output_dir,
        )

    for el_type in extract_image_block_types:
        if extract_images_in_pdf and el_type == ElementType.IMAGE:
            continue

        save_elements(
            elements=elements,
            starting_page_number=starting_page_number,
            element_category_to_save=el_type,
            filename=filename,
            file=file,
            is_image=is_image,
            pdf_image_dpi=pdf_image_dpi,
            extract_image_block_to_payload=extract_image_block_to_payload,
            output_dir_path=extract_image_block_output_dir,
        )

    out_elements = []
    for el in elements:
        if isinstance(el, PageBreak) and not include_page_breaks:
            continue

        if isinstance(el, Image):
            out_elements.append(cast(Element, el))
        # NOTE(crag): this is probably always a Text object, but check for the sake of typing
        elif isinstance(el, Text):
            el.text = re.sub(
                RE_MULTISPACE_INCLUDING_NEWLINES,
                " ",
                el.text or "",
            ).strip()
            if el.text or isinstance(el, PageBreak):
                out_elements.append(cast(Element, el))

    if extract_forms:
        forms = run_form_extraction(
            file=file,
            filename=filename,
            model_name=hi_res_model_name,
            elements=out_elements,
            skip_table_regions=form_extraction_skip_tables,
        )
        out_elements.extend(forms)

    if analysis:
        if not skip_analysis_dump:
            final_layout_dumper = FinalLayoutDumper(
                layout=out_elements,
            )
        layout_dumpers = []
        if od_model_layout_dumper:
            layout_dumpers.append(od_model_layout_dumper)
        if extracted_layout_dumper:
            layout_dumpers.append(extracted_layout_dumper)
        if ocr_layout_dumper:
            layout_dumpers.append(ocr_layout_dumper)
        if final_layout_dumper:
            layout_dumpers.append(final_layout_dumper)
        save_analysis_artifiacts(
            *layout_dumpers,
            filename=filename,
            file=file,
            is_image=is_image,
            analyzed_image_output_dir_path=analyzed_image_output_dir_path,
            skip_bboxes=env_config.ANALYSIS_BBOX_SKIP,
            skip_dump_od=env_config.ANALYSIS_DUMP_OD_SKIP,
            draw_grid=env_config.ANALYSIS_BBOX_DRAW_GRID,
            draw_caption=env_config.ANALYSIS_BBOX_DRAW_CAPTION,
            resize=env_config.ANALYSIS_BBOX_RESIZE,
            format=env_config.ANALYSIS_BBOX_FORMAT,
        )

    return out_elements


def _partition_pdf_with_pdfparser(
    extracted_elements: list[list[Element]],
    include_page_breaks: bool = False,
    sort_mode: str = SORT_MODE_XY_CUT,
    **kwargs,
):
    """Partitions a PDF using pdfparser."""
    elements = []

    for page_elements in extracted_elements:
        # NOTE(crag, christine): always do the basic sort first for deterministic order across
        # python versions.
        sorted_page_elements = sort_page_elements(page_elements, SORT_MODE_BASIC)
        if sort_mode != SORT_MODE_BASIC:
            sorted_page_elements = sort_page_elements(sorted_page_elements, sort_mode)

        elements += sorted_page_elements

        if include_page_breaks:
            elements.append(PageBreak(text=""))

    return elements


def _partition_pdf_or_image_with_ocr(
    filename: str = "",
    file: Optional[bytes | IO[bytes]] = None,
    include_page_breaks: bool = False,
    languages: Optional[list[str]] = None,
    ocr_languages: Optional[str] = None,
    is_image: bool = False,
    metadata_last_modified: Optional[str] = None,
    starting_page_number: int = 1,
    **kwargs: Any,
):
    """Partitions an image or PDF using OCR. For PDFs, each page is converted
    to an image prior to processing."""

    elements = []
    if is_image:
        images = []
        image = PILImage.open(file) if file is not None else PILImage.open(filename)
        images.append(image)

        for page_number, image in enumerate(images, start=starting_page_number):
            page_elements = _partition_pdf_or_image_with_ocr_from_image(
                image=image,
                languages=languages,
                ocr_languages=ocr_languages,
                page_number=page_number,
                include_page_breaks=include_page_breaks,
                metadata_last_modified=metadata_last_modified,
                **kwargs,
            )
            elements.extend(page_elements)
    else:
        for page_number, image in enumerate(
            convert_pdf_to_images(filename, file), start=starting_page_number
        ):
            page_elements = _partition_pdf_or_image_with_ocr_from_image(
                image=image,
                languages=languages,
                ocr_languages=ocr_languages,
                page_number=page_number,
                include_page_breaks=include_page_breaks,
                metadata_last_modified=metadata_last_modified,
                **kwargs,
            )
            elements.extend(page_elements)

    return elements


def _partition_pdf_or_image_with_ocr_from_image(
    image: PILImage.Image,
    languages: Optional[list[str]] = None,
    ocr_languages: Optional[str] = None,
    page_number: int = 1,
    include_page_breaks: bool = False,
    metadata_last_modified: Optional[str] = None,
    sort_mode: str = SORT_MODE_XY_CUT,
    **kwargs: Any,
) -> list[Element]:
    """Extract `unstructured` elements from an image using OCR and perform partitioning."""

    from unstructured.partition.utils.ocr_models.ocr_interface import OCRAgent

    ocr_agent = OCRAgent.get_agent(language=ocr_languages)

    # NOTE(christine): `pytesseract.image_to_string()` returns sorted text
    if ocr_agent.is_text_sorted():
        sort_mode = SORT_MODE_DONT

    ocr_data = ocr_agent.get_layout_elements_from_image(image=image)

    metadata = ElementMetadata(
        last_modified=metadata_last_modified,
        filetype=image.format,
        page_number=page_number,
        languages=languages,
    )

    # NOTE (yao): elements for a document is still stored as a list therefore at this step we have
    # to convert the vector data structured ocr_data into a list
    page_elements = ocr_data_to_elements(
        ocr_data.as_list(),
        image_size=image.size,
        common_metadata=metadata,
    )

    sorted_page_elements = page_elements
    if sort_mode != SORT_MODE_DONT:
        sorted_page_elements = sort_page_elements(page_elements, sort_mode)

    if include_page_breaks:
        sorted_page_elements.append(PageBreak(text=""))

    return page_elements


def _process_uncategorized_text_elements(elements: list[Element]):
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


def _combine_list_elements(
    elements: list[Element], coordinate_system: PixelSpace | PointSpace
) -> list[Element]:
    """Combine elements that should be considered a single ListItem element."""
    tmp_element = None
    updated_elements: list[Element] = []
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
    urls_metadata: list[dict[str, Any]], moved_indices: np.ndarray
) -> list[Link]:
    """Extracts links from a list of URL metadata."""
    links: list[Link] = []
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
    element1: Element, element2: Element, coordinate_system: PixelSpace | PointSpace
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
    return copy.deepcopy(element1)


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


def document_to_element_list(
    document: DocumentLayout,
    sortable: bool = False,
    include_page_breaks: bool = False,
    last_modification_date: Optional[str] = None,
    infer_list_items: bool = True,
    source_format: Optional[str] = None,
    detection_origin: Optional[str] = None,
    sort_mode: str = SORT_MODE_XY_CUT,
    languages: Optional[list[str]] = None,
    starting_page_number: int = 1,
    layouts_links: Optional[list[list]] = None,
    **kwargs: Any,
) -> list[Element]:
    """Converts a DocumentLayout object to a list of unstructured elements."""
    elements: list[Element] = []

    num_pages = len(document.pages)
    for page_number, page in enumerate(document.pages, start=starting_page_number):
        page_elements: list[Element] = []

        page_image_metadata = get_page_image_metadata(page)
        image_format = page_image_metadata.get("format")
        image_width = page_image_metadata.get("width")
        image_height = page_image_metadata.get("height")

        translation_mapping: list[tuple["LayoutElement", Element]] = []

        links = (
            layouts_links[page_number - starting_page_number]
            if layouts_links and layouts_links[0]
            else None
        )

        for layout_element in page.elements:
            if (
                image_width
                and image_height
                and getattr(layout_element.bbox, "x1") not in (None, np.nan)
            ):
                coordinate_system = PixelSpace(width=image_width, height=image_height)
            else:
                coordinate_system = None

            element = normalize_layout_element(
                layout_element,
                coordinate_system=coordinate_system,
                infer_list_items=infer_list_items,
                source_format=source_format if source_format else "html",
            )
            if isinstance(element, list):
                for el in element:
                    if last_modification_date:
                        el.metadata.last_modified = last_modification_date
                    el.metadata.page_number = page_number
                page_elements.extend(element)
                translation_mapping.extend([(layout_element, el) for el in element])
                continue
            else:

                element.metadata.links = (
                    get_links_in_element(links, layout_element.bbox) if links else []
                )

                if last_modification_date:
                    element.metadata.last_modified = last_modification_date
                element.metadata.text_as_html = getattr(layout_element, "text_as_html", None)
                element.metadata.table_as_cells = getattr(layout_element, "table_as_cells", None)

                if (isinstance(element, Title) and element.metadata.category_depth is None) and any(
                    getattr(el, "type", "") in ["Headline", "Subheadline"] for el in page.elements
                ):
                    element.metadata.category_depth = 0

                page_elements.append(element)
                translation_mapping.append((layout_element, element))
            coordinates = (
                element.metadata.coordinates.points if element.metadata.coordinates else None
            )

            el_image_path = (
                layout_element.image_path if hasattr(layout_element, "image_path") else None
            )

            add_element_metadata(
                element,
                page_number=page_number,
                filetype=image_format,
                coordinates=coordinates,
                coordinate_system=coordinate_system,
                category_depth=element.metadata.category_depth,
                image_path=el_image_path,
                detection_origin=detection_origin,
                languages=languages,
                **kwargs,
            )

        for layout_element, element in translation_mapping:
            if hasattr(layout_element, "parent") and layout_element.parent is not None:
                element_parent = first(
                    (el for l_el, el in translation_mapping if l_el is layout_element.parent),
                )
                element.metadata.parent_id = element_parent.id
        sorted_page_elements = page_elements
        if sortable and sort_mode != SORT_MODE_DONT:
            sorted_page_elements = sort_page_elements(page_elements, sort_mode)

        if include_page_breaks and page_number < num_pages + starting_page_number:
            sorted_page_elements.append(PageBreak(text=""))
        elements.extend(sorted_page_elements)

    return elements
