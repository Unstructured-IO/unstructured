from typing import List, Optional

from unstructured.documents.elements import Element, process_metadata
from unstructured.partition.common import exactly_one
from unstructured.partition.pdf import partition_pdf_or_image


@process_metadata()
def partition_image(
    filename: str = "",
    file: Optional[bytes] = None,
    include_page_breaks: bool = False,
    infer_table_structure: bool = False,
    ocr_languages: str = "eng",
    strategy: str = "hi_res",
    metadata_last_modified: Optional[str] = None,
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
    ocr_languages
        The languages to use for the Tesseract agent. To use a language, you'll first need
        to install the appropriate Tesseract language pack.
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

    return partition_pdf_or_image(
        filename=filename,
        file=file,
        is_image=True,
        include_page_breaks=include_page_breaks,
        infer_table_structure=infer_table_structure,
        ocr_languages=ocr_languages,
        strategy=strategy,
        metadata_last_modified=metadata_last_modified,
    )
