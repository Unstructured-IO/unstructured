import re
import warnings
from tempfile import SpooledTemporaryFile
from typing import BinaryIO, List, Optional, Union, cast

import pdf2image
import pytesseract
from pdfminer.high_level import extract_pages
from pdfminer.utils import open_filename
from PIL import Image

from unstructured.cleaners.core import clean_extra_whitespace
from unstructured.documents.elements import Element, ElementMetadata, PageBreak
from unstructured.nlp.patterns import PARAGRAPH_PATTERN
from unstructured.partition import _partition_via_api
from unstructured.partition.common import (
    add_element_metadata,
    document_to_element_list,
    exactly_one,
    spooled_to_bytes_io_if_needed,
)
from unstructured.partition.strategies import determine_pdf_or_image_strategy
from unstructured.partition.text import partition_text
from unstructured.utils import requires_dependencies


def partition_pdf(
    filename: str = "",
    file: Optional[Union[BinaryIO, SpooledTemporaryFile]] = None,
    url: Optional[str] = None,
    template: str = "layout/pdf",
    token: Optional[str] = None,
    include_page_breaks: bool = False,
    strategy: str = "hi_res",
    infer_table_structure: bool = False,
    encoding: str = "utf-8",
    ocr_languages: str = "eng",
) -> List[Element]:
    """Parses a pdf document into a list of interpreted elements.
    Parameters
    ----------
    filename
        A string defining the target filename path.
    file
        A file-like object as bytes --> open(filename, "rb").
    template
        A string defining the model to be used. Default None uses default model ("layout/pdf" url
        if using the API).
    url
        A string endpoint to self-host an inference API, if desired. If None, local inference will
        be used.
    token
        A string defining the authentication token for a self-host url, if applicable.
    strategy
        The strategy to use for partitioning the PDF. Valid strategies are "hi_res",
        "ocr_only", and "fast". When using the "hi_res" strategy, the function uses
        a layout detection model to identify document elements. When using the
        "ocr_only" strategy, partition_image simply extracts the text from the
        document using OCR and processes it. If the "fast" strategy is used, the text
        is extracted directly from the PDF.
    infer_table_structure
        Only applicable if `strategy=hi_res`.
        If True, any Table elements that are extracted will also have a metadata field
        named "text_as_html" where the table's text content is rendered into an html string.
        I.e., rows and cells are preserved.
        Whether True or False, the "text" field is always present in any Table element
        and is the text content of the table (no structure).
    encoding
        The encoding method used to decode the text input. If None, utf-8 will be used.
    ocr_languages
        The languages to use for the Tesseract agent. To use a language, you'll first need
        to isntall the appropriate Tesseract language pack.
    """
    exactly_one(filename=filename, file=file)
    return partition_pdf_or_image(
        filename=filename,
        file=file,
        url=url,
        template=template,
        token=token,
        include_page_breaks=include_page_breaks,
        strategy=strategy,
        infer_table_structure=infer_table_structure,
        encoding=encoding,
        ocr_languages=ocr_languages,
    )


def partition_pdf_or_image(
    filename: str = "",
    file: Optional[Union[bytes, BinaryIO, SpooledTemporaryFile]] = None,
    url: Optional[str] = "https://ml.unstructured.io/",
    template: str = "layout/pdf",
    token: Optional[str] = None,
    is_image: bool = False,
    include_page_breaks: bool = False,
    strategy: str = "hi_res",
    infer_table_structure: bool = False,
    encoding: str = "utf-8",
    ocr_languages: str = "eng",
) -> List[Element]:
    """Parses a pdf or image document into a list of interpreted elements."""
    if url is None:
        # TODO(alan): Extract information about the filetype to be processed from the template
        # route. Decoding the routing should probably be handled by a single function designed for
        # that task so as routing design changes, those changes are implemented in a single
        # function.
        route_args = template.strip("/").split("/")
        is_image = route_args[-1] == "image"
        out_template: Optional[str] = template
        if route_args[0] == "layout":
            out_template = None

        strategy = determine_pdf_or_image_strategy(
            strategy,
            filename=filename,
            file=file,
            is_image=is_image,
        )

        if strategy == "hi_res":
            # NOTE(robinson): Catches a UserWarning that occurs when detectron is called
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                layout_elements = _partition_pdf_or_image_local(
                    filename=filename,
                    file=spooled_to_bytes_io_if_needed(file),
                    template=out_template,
                    is_image=is_image,
                    infer_table_structure=infer_table_structure,
                    include_page_breaks=True,
                    ocr_languages=ocr_languages,
                )

        elif strategy == "fast":
            return _partition_pdf_with_pdfminer(
                filename=filename,
                file=spooled_to_bytes_io_if_needed(file),
                include_page_breaks=include_page_breaks,
                encoding=encoding,
            )

        elif strategy == "ocr_only":
            # NOTE(robinson): Catches file conversion warnings when running with PDFs
            with warnings.catch_warnings():
                return _partition_pdf_or_image_with_ocr(
                    filename=filename,
                    file=file,
                    include_page_breaks=include_page_breaks,
                    ocr_languages=ocr_languages,
                    is_image=is_image,
                )

    else:
        # NOTE(alan): Remove these lines after different models are handled by routing
        if template == "checkbox":
            template = "layout/pdf"
        # NOTE(alan): Remove after different models are handled by routing
        data = {"model": "checkbox"} if (template == "checkbox") else None
        url = f"{url.rstrip('/')}/{template.lstrip('/')}"
        # NOTE(alan): Remove "data=data" after different models are handled by routing
        layout_elements = _partition_via_api(
            filename=filename,
            file=cast(BinaryIO, file),
            url=url,
            token=token,
            data=data,
            include_page_breaks=True,
        )

    return add_element_metadata(
        layout_elements,
        include_page_breaks=include_page_breaks,
        filename=filename,
    )


def _partition_pdf_or_image_local(
    filename: str = "",
    file: Optional[Union[bytes, BinaryIO]] = None,
    template: Optional[str] = None,
    is_image: bool = False,
    infer_table_structure: bool = False,
    include_page_breaks: bool = False,
    ocr_languages: str = "eng",
) -> List[Element]:
    """Partition using package installed locally."""
    try:
        from unstructured_inference.inference.layout import (
            process_data_with_model,
            process_file_with_model,
        )
    except ModuleNotFoundError as e:
        raise Exception(
            "unstructured_inference module not found... try running pip install "
            "unstructured[local-inference] if you installed the unstructured library as a package. "
            "If you cloned the unstructured repository, try running make install-local-inference "
            "from the root directory of the repository.",
        ) from e
    except ImportError as e:
        raise Exception(
            "There was a problem importing unstructured_inference module - it may not be installed "
            "correctly... try running pip install unstructured[local-inference] if you installed "
            "the unstructured library as a package. If you cloned the unstructured repository, try "
            "running make install-local-inference from the root directory of the repository.",
        ) from e

    if file is None:
        layout = process_file_with_model(
            filename,
            template,
            is_image=is_image,
            ocr_languages=ocr_languages,
            extract_tables=infer_table_structure,
        )
    else:
        layout = process_data_with_model(
            file,
            template,
            is_image=is_image,
            ocr_languages=ocr_languages,
            extract_tables=infer_table_structure,
        )

    return document_to_element_list(layout, include_page_breaks=include_page_breaks)


@requires_dependencies("pdfminer", "local-inference")
def _partition_pdf_with_pdfminer(
    filename: str = "",
    file: Optional[BinaryIO] = None,
    include_page_breaks: bool = False,
    encoding: str = "utf-8",
) -> List[Element]:
    """Partitions a PDF using PDFMiner instead of using a layoutmodel. Used for faster
    processing or detectron2 is not available.

    Implementation is based on the `extract_text` implemenation in pdfminer.six, but
    modified to support tracking page numbers and working with file-like objects.

    ref: https://github.com/pdfminer/pdfminer.six/blob/master/pdfminer/high_level.py
    """
    exactly_one(filename=filename, file=file)
    if filename:
        with open_filename(filename, "rb") as fp:
            fp = cast(BinaryIO, fp)
            elements = _process_pdfminer_pages(
                fp=fp,
                filename=filename,
                encoding=encoding,
                include_page_breaks=include_page_breaks,
            )

    elif file:
        fp = cast(BinaryIO, file)
        elements = _process_pdfminer_pages(
            fp=fp,
            filename=filename,
            encoding=encoding,
            include_page_breaks=include_page_breaks,
        )

    return elements


def _process_pdfminer_pages(
    fp: BinaryIO,
    filename: str = "",
    encoding: str = "utf-8",
    include_page_breaks: bool = False,
):
    """Uses PDF miner to split a document into pages and process them."""
    elements: List[Element] = []

    for i, page in enumerate(extract_pages(fp)):  # type: ignore
        metadata = ElementMetadata(filename=filename, page_number=i + 1)

        text_segments = []
        for obj in page:
            # NOTE(robinson) - "Figure" is an example of an object type that does
            # not have a get_text method
            if not hasattr(obj, "get_text"):
                continue
            _text = obj.get_text()
            _text = re.sub(PARAGRAPH_PATTERN, " ", _text)
            _text = clean_extra_whitespace(_text)
            if _text.strip():
                text_segments.append(_text)

        text = "\n\n".join(text_segments)

        _elements = partition_text(text=text)
        for element in _elements:
            element.metadata = metadata
            elements.append(element)

        if include_page_breaks:
            elements.append(PageBreak())

    return elements


def _partition_pdf_or_image_with_ocr(
    filename: str = "",
    file: Optional[Union[bytes, BinaryIO, SpooledTemporaryFile]] = None,
    include_page_breaks: bool = False,
    ocr_languages: str = "eng",
    is_image: bool = False,
):
    """Partitions and image or PDF using Tesseract OCR. For PDFs, each page is converted
    to an image prior to processing."""
    if is_image:
        if file is not None:
            image = Image.open(file)
            text = pytesseract.image_to_string(image, config=f"-l '{ocr_languages}'")
        else:
            text = pytesseract.image_to_string(filename, config=f"-l '{ocr_languages}'")
        elements = partition_text(text=text)
    else:
        elements = []
        if file is not None:
            document = pdf2image.convert_from_bytes(file.read())  # type: ignore
            file.seek(0)  # type: ignore
        else:
            document = pdf2image.convert_from_path(filename)

        for i, image in enumerate(document):
            metadata = ElementMetadata(filename=filename, page_number=i + 1)
            text = pytesseract.image_to_string(image, config=f"-l '{ocr_languages}'")

            _elements = partition_text(text=text)
            for element in _elements:
                element.metadata = metadata
                elements.append(element)

            if include_page_breaks:
                elements.append(PageBreak())
    return elements
