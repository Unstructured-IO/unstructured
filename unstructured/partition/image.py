from typing import List, Optional

from unstructured.documents.elements import Element
from unstructured.partition.common import exactly_one
from unstructured.partition.pdf import partition_pdf_or_image


def partition_image(
    filename: str = "",
    file: Optional[bytes] = None,
    url: Optional[str] = None,
    template: Optional[str] = None,
    token: Optional[str] = None,
    include_page_breaks: bool = False,
    ocr_languages: str = "eng",
    strategy: str = "hi_res",
) -> List[Element]:
    """Parses an image into a list of interpreted elements.

    Parameters
    ----------
    filename
        A string defining the target filename path.
    file
        A file-like object as bytes --> open(filename, "rb").
    template
        A string defining the model to be used. Default None uses default model ("layout/image" url
        if using the API).
    url
        A string endpoint to self-host an inference API, if desired. If None, local inference will
        be used.
    token
        A string defining the authentication token for a self-host url, if applicable.
    ocr_languages
        The languages to use for the Tesseract agent. To use a language, you'll first need
        to install the appropriate Tesseract language pack.
    strategy
        The strategy to use for partitioning the PDF. Valid strategies are "hi_res" and
        "ocr_only". When using the "hi_res" strategy, the function uses a layout detection
        model if to identify document elements. When using the "ocr_only" strategy,
        partition_image simply extracts the text from the document using OCR and processes it.
    """
    exactly_one(filename=filename, file=file)

    if template is None:
        template = "layout/image"

    return partition_pdf_or_image(
        filename=filename,
        file=file,
        url=url,
        template=template,
        token=token,
        include_page_breaks=include_page_breaks,
        ocr_languages=ocr_languages,
        strategy=strategy,
    )
