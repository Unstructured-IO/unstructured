import os
import re
import warnings
from tempfile import SpooledTemporaryFile
from typing import BinaryIO, List, Optional, Union, cast

import pdf2image
import PIL
from pdfminer.high_level import extract_pages
from pdfminer.layout import LTContainer, LTImage, LTItem, LTTextBox
from pdfminer.utils import open_filename

from unstructured.cleaners.core import clean_extra_whitespace
from unstructured.documents.coordinates import PixelSpace
from unstructured.documents.elements import (
    Element,
    ElementMetadata,
    Image,
    PageBreak,
    Text,
    process_metadata,
)
from unstructured.file_utils.filetype import (
    FileType,
    add_metadata_with_filetype,
    document_to_element_list,
)
from unstructured.nlp.patterns import PARAGRAPH_PATTERN
from unstructured.partition.common import (
    exactly_one,
    spooled_to_bytes_io_if_needed,
)
from unstructured.partition.strategies import determine_pdf_or_image_strategy
from unstructured.partition.text import element_from_text, partition_text
from unstructured.utils import requires_dependencies

RE_MULTISPACE_INCLUDING_NEWLINES = re.compile(pattern=r"\s+", flags=re.DOTALL)


@process_metadata()
@add_metadata_with_filetype(FileType.PDF)
def partition_pdf(
    filename: str = "",
    file: Optional[Union[BinaryIO, SpooledTemporaryFile]] = None,
    include_page_breaks: bool = False,
    strategy: str = "auto",
    infer_table_structure: bool = False,
    ocr_languages: str = "eng",
    max_partition: Optional[int] = 1500,
    include_metadata: bool = True,
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
    ocr_languages
        The languages to use for the Tesseract agent. To use a language, you'll first need
        to isntall the appropriate Tesseract language pack.
    max_partition
        The maximum number of characters to include in a partition. If None is passed,
        no maximum is applied. Only applies to the "ocr_only" strategy.
    """
    exactly_one(filename=filename, file=file)
    return partition_pdf_or_image(
        filename=filename,
        file=file,
        include_page_breaks=include_page_breaks,
        strategy=strategy,
        infer_table_structure=infer_table_structure,
        ocr_languages=ocr_languages,
        max_partition=max_partition,
    )


def partition_pdf_or_image(
    filename: str = "",
    file: Optional[Union[bytes, BinaryIO, SpooledTemporaryFile]] = None,
    is_image: bool = False,
    include_page_breaks: bool = False,
    strategy: str = "auto",
    infer_table_structure: bool = False,
    ocr_languages: str = "eng",
    max_partition: Optional[int] = 1500,
) -> List[Element]:
    """Parses a pdf or image document into a list of interpreted elements."""
    # TODO(alan): Extract information about the filetype to be processed from the template
    # route. Decoding the routing should probably be handled by a single function designed for
    # that task so as routing design changes, those changes are implemented in a single
    # function.

    strategy = determine_pdf_or_image_strategy(
        strategy,
        filename=filename,
        file=file,
        is_image=is_image,
        infer_table_structure=infer_table_structure,
    )

    if strategy == "hi_res":
        # NOTE(robinson): Catches a UserWarning that occurs when detectron is called
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            layout_elements = _partition_pdf_or_image_local(
                filename=filename,
                file=spooled_to_bytes_io_if_needed(file),
                is_image=is_image,
                infer_table_structure=infer_table_structure,
                include_page_breaks=include_page_breaks,
                ocr_languages=ocr_languages,
            )

    elif strategy == "fast":
        return _partition_pdf_with_pdfminer(
            filename=filename,
            file=spooled_to_bytes_io_if_needed(file),
            include_page_breaks=include_page_breaks,
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
                max_partition=max_partition,
            )

    return layout_elements


@requires_dependencies("unstructured_inference")
def _partition_pdf_or_image_local(
    filename: str = "",
    file: Optional[Union[bytes, BinaryIO]] = None,
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

    model_name = os.environ.get("UNSTRUCTURED_HI_RES_MODEL_NAME")
    if file is None:
        layout = process_file_with_model(
            filename,
            is_image=is_image,
            ocr_languages=ocr_languages,
            extract_tables=infer_table_structure,
            model_name=model_name,
        )
    else:
        layout = process_data_with_model(
            file,
            is_image=is_image,
            ocr_languages=ocr_languages,
            extract_tables=infer_table_structure,
            model_name=model_name,
        )
    elements = document_to_element_list(layout, include_page_breaks=include_page_breaks, sort=False)
    out_elements = []

    for el in elements:
        if (isinstance(el, PageBreak) and not include_page_breaks) or (
            # NOTE(crag): small chunks of text from Image elements tend to be garbage
            isinstance(el, Image)
            and (el.text is None or len(el.text) < 24 or el.text.find(" ") == -1)
        ):
            continue
        # NOTE(crag): this is probably always a Text object, but check for the sake of typing
        if isinstance(el, Text):
            el.text = re.sub(RE_MULTISPACE_INCLUDING_NEWLINES, " ", el.text or "").strip()
            if el.text or isinstance(el, PageBreak):
                out_elements.append(cast(Element, el))

    return out_elements


@requires_dependencies("pdfminer", "local-inference")
def _partition_pdf_with_pdfminer(
    filename: str = "",
    file: Optional[BinaryIO] = None,
    include_page_breaks: bool = False,
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
                include_page_breaks=include_page_breaks,
            )

    elif file:
        fp = cast(BinaryIO, file)
        elements = _process_pdfminer_pages(
            fp=fp,
            filename=filename,
            include_page_breaks=include_page_breaks,
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


def _process_pdfminer_pages(
    fp: BinaryIO,
    filename: str = "",
    include_page_breaks: bool = False,
):
    """Uses PDF miner to split a document into pages and process them."""
    elements: List[Element] = []

    for i, page in enumerate(extract_pages(fp)):  # type: ignore
        metadata = ElementMetadata(filename=filename, page_number=i + 1)
        width, height = page.width, page.height

        text_segments = []
        page_elements = []
        for obj in page:
            x1, y2, x2, y1 = obj.bbox
            y1 = height - y1
            y2 = height - y2

            if hasattr(obj, "get_text"):
                _text_snippets = [obj.get_text()]
            else:
                _text = _extract_text(obj)
                _text_snippets = re.split(PARAGRAPH_PATTERN, _text)

            for _text in _text_snippets:
                _text = clean_extra_whitespace(_text)
                if _text.strip():
                    text_segments.append(_text)
                    element = element_from_text(_text)
                    element._coordinate_system = PixelSpace(
                        width=width,
                        height=height,
                    )
                    element.coordinates = ((x1, y1), (x1, y2), (x2, y2), (x2, y1))
                    element.metadata = metadata
                    page_elements.append(element)

        sorted_page_elements = sorted(
            page_elements,
            key=lambda el: (
                el.coordinates[0][1] if el.coordinates else float("inf"),
                el.coordinates[0][0] if el.coordinates else float("inf"),
                el.id,
            ),
        )
        elements += sorted_page_elements

        if include_page_breaks:
            elements.append(PageBreak(text=""))

    return elements


@requires_dependencies("pytesseract")
def _partition_pdf_or_image_with_ocr(
    filename: str = "",
    file: Optional[Union[bytes, BinaryIO, SpooledTemporaryFile]] = None,
    include_page_breaks: bool = False,
    ocr_languages: str = "eng",
    is_image: bool = False,
    max_partition: Optional[int] = 1500,
):
    """Partitions and image or PDF using Tesseract OCR. For PDFs, each page is converted
    to an image prior to processing."""
    import pytesseract

    if is_image:
        if file is not None:
            image = PIL.Image.open(file)
            text = pytesseract.image_to_string(image, config=f"-l '{ocr_languages}'")
        else:
            text = pytesseract.image_to_string(filename, config=f"-l '{ocr_languages}'")
        elements = partition_text(text=text, max_partition=max_partition)
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

            _elements = partition_text(text=text, max_partition=max_partition)
            for element in _elements:
                element.metadata = metadata
                elements.append(element)

            if include_page_breaks:
                elements.append(PageBreak(text=""))
    return elements
