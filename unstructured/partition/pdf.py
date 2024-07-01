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
from pdfminer import psparser
from pdfminer.layout import LTChar, LTContainer, LTImage, LTItem, LTTextBox
from pdfminer.pdftypes import PDFObjRef
from pdfminer.utils import open_filename
from PIL import Image as PILImage
from pillow_heif import register_heif_opener

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
from unstructured.file_utils.filetype import FileType, add_metadata_with_filetype
from unstructured.logger import logger, trace_logger
from unstructured.nlp.patterns import PARAGRAPH_PATTERN
from unstructured.partition.common import (
    document_to_element_list,
    exactly_one,
    ocr_data_to_elements,
    spooled_to_bytes_io_if_needed,
)
from unstructured.partition.lang import check_language_args, prepare_languages_for_tesseract
from unstructured.partition.pdf_image.analysis.bbox_visualisation import (
    AnalysisDrawer,
    FinalLayoutDrawer,
    OCRLayoutDrawer,
    ODModelLayoutDrawer,
    PdfminerLayoutDrawer,
)
from unstructured.partition.pdf_image.analysis.layout_dump import (
    JsonLayoutDumper,
    ObjectDetectionLayoutDumper,
)
from unstructured.partition.pdf_image.form_extraction import run_form_extraction
from unstructured.partition.pdf_image.pdf_image_utils import (
    check_element_types_to_extract,
    convert_pdf_to_images,
    get_the_last_modification_date_pdf_or_img,
    save_elements,
)
from unstructured.partition.pdf_image.pdfminer_processing import (
    clean_pdfminer_duplicate_image_elements,
    clean_pdfminer_inner_elements,
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
    SORT_MODE_BASIC,
    SORT_MODE_DONT,
    SORT_MODE_XY_CUT,
    OCRMode,
    PartitionStrategy,
)
from unstructured.partition.utils.sorting import coord_has_valid_points, sort_page_elements
from unstructured.patches.pdfminer import parse_keyword
from unstructured.utils import requires_dependencies

if TYPE_CHECKING:
    pass

# NOTE(alan): Patching this to fix a bug in pdfminer.six. Submitted this PR into pdfminer.six to fix
# the bug: https://github.com/pdfminer/pdfminer.six/pull/885
psparser.PSBaseParser._parse_keyword = parse_keyword  # type: ignore

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
    include_metadata: bool = True,  # used by decorator
    metadata_filename: Optional[str] = None,  # used by decorator
    metadata_last_modified: Optional[str] = None,
    chunking_strategy: Optional[str] = None,  # used by decorator
    hi_res_model_name: Optional[str] = None,
    extract_images_in_pdf: bool = False,
    extract_image_block_types: Optional[list[str]] = None,
    extract_image_block_output_dir: Optional[str] = None,
    extract_image_block_to_payload: bool = False,
    date_from_file_object: bool = False,
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
    date_from_file_object
        Applies only when providing file via `file` parameter. If this option is True, attempt
        infer last_modified metadata from bytes, otherwise set it to None.
    extract_forms
        Whether the form extraction logic should be run
        (results in adding FormKeysValues elements to output).
    form_extraction_skip_tables
        Whether the form extraction logic should ignore regions designated as Tables.
    """

    exactly_one(filename=filename, file=file)

    languages = check_language_args(languages or [], ocr_languages) or ["eng"]

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
        date_from_file_object=date_from_file_object,
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
    ocr_languages: Optional[str] = None,
    languages: Optional[list[str]] = None,
    metadata_last_modified: Optional[str] = None,
    hi_res_model_name: Optional[str] = None,
    extract_images_in_pdf: bool = False,
    extract_image_block_types: Optional[list[str]] = None,
    extract_image_block_output_dir: Optional[str] = None,
    extract_image_block_to_payload: bool = False,
    date_from_file_object: bool = False,
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

    # init ability to process .heic files
    register_heif_opener()

    validate_strategy(strategy, is_image)

    last_modification_date = get_the_last_modification_date_pdf_or_img(
        file=file,
        filename=filename,
        date_from_file_object=date_from_file_object,
    )

    extracted_elements = []
    pdf_text_extractable = False
    if not is_image:
        try:
            extracted_elements = extractable_elements(
                filename=filename,
                file=spooled_to_bytes_io_if_needed(file),
                languages=languages,
                metadata_last_modified=metadata_last_modified or last_modification_date,
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
                metadata_last_modified=metadata_last_modified or last_modification_date,
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
                is_image=is_image,
                metadata_last_modified=metadata_last_modified or last_modification_date,
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
                _, words = get_word_bounding_box_from_element(obj, height)
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


@requires_dependencies("unstructured_inference")
def _partition_pdf_or_image_local(
    filename: str = "",
    file: Optional[bytes | IO[bytes]] = None,
    is_image: bool = False,
    infer_table_structure: bool = False,
    include_page_breaks: bool = False,
    languages: Optional[list[str]] = None,
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

    if languages is None:
        languages = ["eng"]

    ocr_languages = prepare_languages_for_tesseract(languages)

    hi_res_model_name = hi_res_model_name or model_name or default_hi_res_model()
    if pdf_image_dpi is None:
        pdf_image_dpi = 300 if hi_res_model_name.startswith("chipper") else 200
    if (pdf_image_dpi < 300) and (hi_res_model_name.startswith("chipper")):
        logger.warning(
            "The Chipper model performs better when images are rendered with DPI >= 300 "
            f"(currently {pdf_image_dpi}).",
        )

    pdfminer_drawer: Optional[PdfminerLayoutDrawer] = None
    od_model_drawer: Optional[ODModelLayoutDrawer] = None
    ocr_drawer: Optional[OCRLayoutDrawer] = None
    od_model_layout_dumper: Optional[ObjectDetectionLayoutDumper] = None
    skip_bboxes = env_config.ANALYSIS_BBOX_SKIP
    skip_dump_od = env_config.ANALYSIS_DUMP_OD_SKIP

    if file is None:
        inferred_document_layout = process_file_with_model(
            filename,
            is_image=is_image,
            model_name=hi_res_model_name,
            pdf_image_dpi=pdf_image_dpi,
        )

        if hi_res_model_name.startswith("chipper"):
            # NOTE(alan): We shouldn't do OCR with chipper
            # NOTE(antonio): We shouldn't do PDFMiner with chipper
            final_document_layout = inferred_document_layout
        else:
            extracted_layout = (
                process_file_with_pdfminer(filename=filename, dpi=pdf_image_dpi)
                if pdf_text_extractable
                else []
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
                if not skip_bboxes:
                    pdfminer_drawer = PdfminerLayoutDrawer(
                        layout=extracted_layout,
                    )
                    od_model_drawer = ODModelLayoutDrawer(
                        layout=inferred_document_layout,
                    )
                    ocr_drawer = OCRLayoutDrawer()
                if not skip_dump_od:
                    od_model_layout_dumper = ObjectDetectionLayoutDumper(
                        layout=inferred_document_layout,
                        model_name=hi_res_model_name,
                    )
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
                ocr_drawer=ocr_drawer,
            )
    else:
        inferred_document_layout = process_data_with_model(
            file,
            is_image=is_image,
            model_name=hi_res_model_name,
            pdf_image_dpi=pdf_image_dpi,
        )

        if hi_res_model_name.startswith("chipper"):
            # NOTE(alan): We shouldn't do OCR with chipper
            # NOTE(antonio): We shouldn't do PDFMiner with chipper
            final_document_layout = inferred_document_layout
        else:
            if hasattr(file, "seek"):
                file.seek(0)

            extracted_layout = (
                process_data_with_pdfminer(file=file, dpi=pdf_image_dpi)
                if pdf_text_extractable
                else []
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
                pdfminer_drawer = PdfminerLayoutDrawer(
                    layout=extracted_layout,
                )
                od_model_drawer = ODModelLayoutDrawer(
                    layout=inferred_document_layout,
                )
                ocr_drawer = OCRLayoutDrawer()

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
                ocr_drawer=ocr_drawer,
            )

    # NOTE(alan): starting with v2, chipper sorts the elements itself.
    if hi_res_model_name.startswith("chipper") and hi_res_model_name != "chipperv1":
        kwargs["sort_mode"] = SORT_MODE_DONT

    final_document_layout = clean_pdfminer_duplicate_image_elements(final_document_layout)
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
            # NOTE(alan): with chipper there are parent elements with no text we don't want to
            # filter those out and leave the children orphaned.
            if el.text or isinstance(el, PageBreak) or hi_res_model_name.startswith("chipper"):
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

    if analysis and not skip_bboxes:
        final_drawer = FinalLayoutDrawer(
            layout=out_elements,
        )
        analysis_drawer = AnalysisDrawer(
            filename=filename,
            save_dir=analyzed_image_output_dir_path,
            draw_grid=env_config.ANALYSIS_BBOX_DRAW_GRID,
            draw_caption=env_config.ANALYSIS_BBOX_DRAW_CAPTION,
            resize=env_config.ANALYSIS_BBOX_RESIZE,
            format=env_config.ANALYSIS_BBOX_FORMAT,
        )

        if od_model_drawer:
            analysis_drawer.add_drawer(od_model_drawer)

        if pdfminer_drawer:
            analysis_drawer.add_drawer(pdfminer_drawer)

        if ocr_drawer:
            analysis_drawer.add_drawer(ocr_drawer)
        analysis_drawer.add_drawer(final_drawer)
        analysis_drawer.process()

    if analysis and not skip_dump_od:
        json_layout_dumper = JsonLayoutDumper(
            filename=filename,
            save_dir=analyzed_image_output_dir_path,
        )
        if od_model_layout_dumper:
            json_layout_dumper.add_layout_dumper(od_model_layout_dumper)
        json_layout_dumper.process()

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
    languages: Optional[list[str]] = ["eng"],
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
    page_number: int = 1,
    include_page_breaks: bool = False,
    metadata_last_modified: Optional[str] = None,
    sort_mode: str = SORT_MODE_XY_CUT,
    **kwargs: Any,
) -> list[Element]:
    """Extract `unstructured` elements from an image using OCR and perform partitioning."""

    from unstructured.partition.utils.ocr_models.ocr_interface import OCRAgent

    ocr_agent = OCRAgent.get_agent()
    ocr_languages = prepare_languages_for_tesseract(languages)

    # NOTE(christine): `unstructured_pytesseract.image_to_string()` returns sorted text
    if ocr_agent.is_text_sorted():
        sort_mode = SORT_MODE_DONT

    ocr_data = ocr_agent.get_layout_elements_from_image(
        image=image,
        ocr_languages=ocr_languages,
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


def get_word_bounding_box_from_element(
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
