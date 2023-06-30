from typing import List, Optional

from unstructured.documents.elements import Element, process_metadata
from unstructured.partition.common import exactly_one
from unstructured.partition.pdf import partition_pdf_or_image


@process_metadata()
def partition_image(
    filename: str = "",
    file: Optional[bytes] = None,
    include_page_breaks: bool = False,
    ocr_languages: str = "eng",
    strategy: str = "auto",
    **kwargs,
) -> List[Element]:
    """Parses an image into a list of interpreted elements.

    Parameters
    ----------
    filename
        A string defining the target filename path.
    file
        A file-like object as bytes --> open(filename, "rb").
    ocr_languages
        The languages to use for the Tesseract agent. To use a language, you'll first need
        to install the appropriate Tesseract language pack.
    strategy
        The strategy to use for partitioning the image. Valid strategies are "hi_res" and
        "ocr_only". When using the "hi_res" strategy, the function uses a layout detection
        model if to identify document elements. When using the "ocr_only" strategy,
        partition_image simply extracts the text from the document using OCR and processes it.
        The default strategy `auto` will determine when a image can be extracted using
        `ocr_only` mode, otherwise it will fall back to `hi_res`.
    """
    exactly_one(filename=filename, file=file)

    return partition_pdf_or_image(
        filename=filename,
        file=file,
        is_image=True,
        include_page_breaks=include_page_breaks,
        ocr_languages=ocr_languages,
        strategy=strategy,
    )
