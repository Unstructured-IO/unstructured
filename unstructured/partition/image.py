from typing import List, Optional

from unstructured.chunking.title import add_chunking_strategy
from unstructured.documents.elements import Element, process_metadata
from unstructured.file_utils.filetype import add_metadata
from unstructured.logger import logger
from unstructured.partition.common import exactly_one
from unstructured.partition.lang import (
    convert_old_ocr_languages_to_languages,
)
from unstructured.partition.pdf import partition_pdf_or_image
from unstructured.partition.utils.constants import PartitionStrategy


@process_metadata()
@add_metadata
@add_chunking_strategy()
def partition_image(
    filename: str = "",
    file: Optional[bytes] = None,
    include_page_breaks: bool = False,
    infer_table_structure: bool = False,
    ocr_languages: Optional[str] = None,
    languages: Optional[List[str]] = ["eng"],
    strategy: str = PartitionStrategy.HI_RES,
    metadata_last_modified: Optional[str] = None,
    chunking_strategy: Optional[str] = None,
    **kwargs,
) -> List[Element]:
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
    """
    exactly_one(filename=filename, file=file)

    if languages is None:
        languages = ["eng"]

    if not isinstance(languages, list):
        raise TypeError(
            'The language parameter must be a list of language codes as strings, ex. ["eng"]',
        )

    if ocr_languages is not None:
        if languages != ["eng"]:
            raise ValueError(
                "Only one of languages and ocr_languages should be specified. "
                "languages is preferred. ocr_languages is marked for deprecation.",
            )

        else:
            languages = convert_old_ocr_languages_to_languages(ocr_languages)
            logger.warning(
                "The ocr_languages kwarg will be deprecated in a future version of unstructured. "
                "Please use languages instead.",
            )

    return partition_pdf_or_image(
        filename=filename,
        file=file,
        is_image=True,
        include_page_breaks=include_page_breaks,
        infer_table_structure=infer_table_structure,
        languages=languages,
        strategy=strategy,
        metadata_last_modified=metadata_last_modified,
        **kwargs,
    )
