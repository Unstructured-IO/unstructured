from __future__ import annotations

from typing import IO, Any, Optional

from unstructured.chunking import add_chunking_strategy
from unstructured.documents.elements import Element, process_metadata
from unstructured.file_utils.filetype import add_metadata
from unstructured.partition.common import exactly_one
from unstructured.partition.lang import check_language_args
from unstructured.partition.pdf import partition_pdf_or_image
from unstructured.partition.utils.constants import PartitionStrategy


@process_metadata()
@add_metadata
@add_chunking_strategy
def partition_image(
    filename: Optional[str] = None,
    file: Optional[IO[bytes]] = None,
    include_page_breaks: bool = False,
    infer_table_structure: bool = False,
    ocr_languages: Optional[str] = None,
    languages: Optional[list[str]] = None,
    strategy: str = PartitionStrategy.HI_RES,
    metadata_last_modified: Optional[str] = None,
    chunking_strategy: Optional[str] = None,
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
    """Parses an image into a list of interpreted elements.

    Parameters
    ----------
    filename
        A string defining the target filename path.
    file
        A file-like object as bytes --> open(filename, "rb").
    include_page_breaks
        If True, includes page breaks at the end of each page in the document.
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
    strategy
        The strategy to use for partitioning the image. Valid strategies are "hi_res" and
        "ocr_only". When using the "hi_res" strategy, the function uses a layout detection
        model if to identify document elements. When using the "ocr_only" strategy,
        partition_image simply extracts the text from the document using OCR and processes it.
        The default strategy is `hi_res`.
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
        saved in the path specified by 'extract_image_block_output_dir' or stored as base64 encoded
        data within metadata fields.
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

    languages = check_language_args(languages or [], ocr_languages)

    return partition_pdf_or_image(
        filename=filename,
        file=file,
        is_image=True,
        include_page_breaks=include_page_breaks,
        infer_table_structure=infer_table_structure,
        languages=languages,
        strategy=strategy,
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
