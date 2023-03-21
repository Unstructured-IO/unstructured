import warnings
from io import StringIO
from typing import BinaryIO, List, Optional, cast

from unstructured.documents.elements import Element, ElementMetadata, PageBreak
from unstructured.logger import logger
from unstructured.partition import _partition_via_api
from unstructured.partition.common import (
    add_element_metadata,
    document_to_element_list,
    exactly_one,
)
from unstructured.partition.text import partition_text
from unstructured.utils import dependency_exists, requires_dependencies


def partition_pdf(
    filename: str = "",
    file: Optional[bytes] = None,
    url: Optional[str] = None,
    template: Optional[str] = None,
    token: Optional[str] = None,
    include_page_breaks: bool = False,
    strategy: str = "hi_res",
    encoding: str = "utf-8",
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
        The strategy to use for partitioning the PDF. Uses a layout detection model if set
        to 'hi_res', otherwise partition_pdf simply extracts the text from the document
        and processes it.
    encoding
        The encoding method used to decode the text input. If None, utf-8 will be used.
    """
    if template is None:
        template = "layout/pdf"
    return partition_pdf_or_image(
        filename=filename,
        file=file,
        url=url,
        template=template,
        token=token,
        include_page_breaks=include_page_breaks,
        strategy=strategy,
        encoding=encoding,
    )


def partition_pdf_or_image(
    filename: str = "",
    file: Optional[bytes] = None,
    url: Optional[str] = "https://ml.unstructured.io/",
    template: str = "layout/pdf",
    token: Optional[str] = None,
    is_image: bool = False,
    include_page_breaks: bool = False,
    strategy: str = "hi_res",
    encoding: str = "utf-8",
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

        fallback_to_fast = False
        if not dependency_exists("detectron2"):
            if is_image:
                raise ValueError(
                    "detectron2 is not installed. detectron2 is required for " "partioning images.",
                )
            else:
                fallback_to_fast = True
                logger.warn(
                    "detectron2 is not installed. Cannot use the hi_res partitioning "
                    "strategy. Falling back to partitioning with the fast strategy.",
                )

        if strategy == "hi_res" and not fallback_to_fast:
            # NOTE(robinson): Catches a UserWarning that occurs when detectron is called
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                layout_elements = _partition_pdf_or_image_local(
                    filename=filename,
                    file=file,
                    template=out_template,
                    is_image=is_image,
                    include_page_breaks=True,
                )

        elif strategy == "fast" or fallback_to_fast:
            return _partition_pdf_with_pdfminer(
                filename=filename,
                file=file,
                include_page_breaks=include_page_breaks,
                encoding=encoding,
            )

        else:
            raise ValueError(f"{strategy} is an invalid parsing strategy for PDFs")

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
            file=file,
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
    file: Optional[bytes] = None,
    template: Optional[str] = None,
    is_image: bool = False,
    include_page_breaks: bool = False,
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

    layout = (
        process_file_with_model(filename, template, is_image=is_image)
        if file is None
        else process_data_with_model(file, template, is_image=is_image)
    )

    return document_to_element_list(layout, include_page_breaks=include_page_breaks)


@requires_dependencies("pdfminer", "local-inference")
def _partition_pdf_with_pdfminer(
    filename: str = "",
    file: Optional[bytes] = None,
    include_page_breaks: bool = False,
    encoding: str = "utf-8",
) -> List[Element]:
    """Partitions a PDF using PDFMiner instead of using a layoutmodel. Used for faster
    processing or detectron2 is not available.

    Implementation is based on the `extract_text` implemenation in pdfminer.six, but
    modified to support tracking page numbers and working with file-like objects.

    ref: https://github.com/pdfminer/pdfminer.six/blob/master/pdfminer/high_level.py
    """

    from pdfminer.utils import open_filename

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
    from pdfminer.converter import TextConverter
    from pdfminer.layout import LAParams
    from pdfminer.pdfinterp import PDFPageInterpreter, PDFResourceManager
    from pdfminer.pdfpage import PDFPage

    rsrcmgr = PDFResourceManager(caching=False)
    laparams = LAParams()

    elements: List[Element] = []

    for i, page in enumerate(PDFPage.get_pages(fp)):
        metadata = ElementMetadata(filename=filename, page_number=i + 1)
        with StringIO() as output_string:
            device = TextConverter(
                rsrcmgr,
                output_string,
                codec=encoding,
                laparams=laparams,
            )
            interpreter = PDFPageInterpreter(rsrcmgr, device)
            interpreter.process_page(page)
            text = output_string.getvalue()
            _elements = partition_text(text=text)
            for element in _elements:
                element.metadata = metadata
                elements.append(element)

        if include_page_breaks:
            elements.append(PageBreak())

    return elements
