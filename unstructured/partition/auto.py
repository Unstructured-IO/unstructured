import io
from typing import IO, Callable, Dict, Optional, Tuple

import requests

from unstructured.file_utils.filetype import FileType, detect_filetype
from unstructured.logger import logger
from unstructured.partition.common import exactly_one
from unstructured.partition.doc import partition_doc
from unstructured.partition.docx import partition_docx
from unstructured.partition.email import partition_email
from unstructured.partition.epub import partition_epub
from unstructured.partition.html import partition_html
from unstructured.partition.image import partition_image
from unstructured.partition.json import partition_json
from unstructured.partition.md import partition_md
from unstructured.partition.msg import partition_msg
from unstructured.partition.odt import partition_odt
from unstructured.partition.pdf import partition_pdf
from unstructured.partition.ppt import partition_ppt
from unstructured.partition.pptx import partition_pptx
from unstructured.partition.rtf import partition_rtf
from unstructured.partition.text import partition_text


def partition(
    filename: Optional[str] = None,
    content_type: Optional[str] = None,
    file: Optional[IO] = None,
    file_filename: Optional[str] = None,
    url: Optional[str] = None,
    include_page_breaks: bool = False,
    strategy: str = "hi_res",
    encoding: str = "utf-8",
    paragraph_grouper: Optional[Callable[[str], str]] = None,
    headers: Dict[str, str] = {},
    ssl_verify: bool = True,
    ocr_languages: str = "eng",
    pdf_infer_table_structure: bool = False,
):
    """Partitions a document into its constituent elements. Will use libmagic to determine
    the file's type and route it to the appropriate partitioning function. Applies the default
    parameters for each partitioning function. Use the document-type specific partitioning
    functions if you need access to additional kwarg options.

    Parameters
    ----------
    filename
        A string defining the target filename path.
    content_type
        A string defining the file content in MIME type
    file
        A file-like object using "rb" mode --> open(filename, "rb").
    file_filename
        When file is not None, the filename (string) to store in element metadata. E.g. "foo.txt"
    url
        The url for a remote document. Pass in content_type if you want partition to treat
        the document as a specific content_type.
    include_page_breaks
        If True, the output will include page breaks if the filetype supports it
    strategy
        The strategy to use for partitioning the PDF. Uses a layout detection model if set
        to 'hi_res', otherwise partition_pdf simply extracts the text from the document
        and processes it.
    encoding
        The encoding method used to decode the text input. If None, utf-8 will be used.
    headers
        The headers to be used in conjunction with the HTTP request if URL is set.
    ssl_verify
        If the URL parameter is set, determines whether or not partition uses SSL verification
        in the HTTP request.
    ocr_languages
        The languages to use for the Tesseract agent. To use a language, you'll first need
        to isntall the appropriate Tesseract language pack.
    pdf_infer_table_structure
        If True and strategy=hi_res, any Table Elements extracted from a PDF will include an
        additional metadata field, "text_as_html," where the value (string) is a just a
        transformation of the data into an HTML <table>.
        The "text" field for a partitioned Table Element is always present, whether True or False.
    """
    exactly_one(file=file, filename=filename, url=url)

    if url is not None:
        file, filetype = file_and_type_from_url(
            url=url,
            content_type=content_type,
            headers=headers,
            ssl_verify=ssl_verify,
        )
    else:
        if headers != {}:
            logger.warning(
                "The headers kwarg is set but the url kwarg is not. "
                "The headers kwarg will be ignored.",
            )
        filetype = detect_filetype(
            filename=filename,
            file=file,
            file_filename=file_filename,
            content_type=content_type,
        )

    if file is not None:
        file.seek(0)

    if filetype == FileType.DOC:
        elements = partition_doc(filename=filename, file=file)
    elif filetype == FileType.DOCX:
        elements = partition_docx(filename=filename, file=file)
    elif filetype == FileType.ODT:
        elements = partition_odt(filename=filename, file=file)
    elif filetype == FileType.EML:
        elements = partition_email(filename=filename, file=file, encoding=encoding)
    elif filetype == FileType.MSG:
        elements = partition_msg(filename=filename, file=file)
    elif filetype == FileType.HTML:
        elements = partition_html(
            filename=filename,
            file=file,
            include_page_breaks=include_page_breaks,
            encoding=encoding,
        )
    elif filetype == FileType.EPUB:
        elements = partition_epub(
            filename=filename,
            file=file,
            include_page_breaks=include_page_breaks,
        )
    elif filetype == FileType.MD:
        elements = partition_md(
            filename=filename,
            file=file,
            include_page_breaks=include_page_breaks,
        )
    elif filetype == FileType.PDF:
        elements = partition_pdf(
            filename=filename,  # type: ignore
            file=file,  # type: ignore
            url=None,
            include_page_breaks=include_page_breaks,
            encoding=encoding,
            infer_table_structure=pdf_infer_table_structure,
            strategy=strategy,
            ocr_languages=ocr_languages,
        )
    elif (filetype == FileType.PNG) or (filetype == FileType.JPG):
        elements = partition_image(
            filename=filename,  # type: ignore
            file=file,  # type: ignore
            url=None,
            include_page_breaks=include_page_breaks,
            ocr_languages=ocr_languages,
        )
    elif filetype == FileType.TXT:
        elements = partition_text(
            filename=filename,
            file=file,
            encoding=encoding,
            paragraph_grouper=paragraph_grouper,
        )
    elif filetype == FileType.RTF:
        elements = partition_rtf(
            filename=filename,
            file=file,
            include_page_breaks=include_page_breaks,
        )
    elif filetype == FileType.PPT:
        elements = partition_ppt(
            filename=filename,
            file=file,
            include_page_breaks=include_page_breaks,
        )
    elif filetype == FileType.PPTX:
        elements = partition_pptx(
            filename=filename,
            file=file,
            include_page_breaks=include_page_breaks,
        )
    elif filetype == FileType.JSON:
        elements = partition_json(filename=filename, file=file)
    else:
        msg = "Invalid file" if not filename else f"Invalid file {filename}"
        raise ValueError(f"{msg}. The {filetype} file type is not supported in partition.")

    for element in elements:
        element.metadata.url = url

    return elements


def file_and_type_from_url(
    url: str,
    content_type: Optional[str] = None,
    headers: Dict[str, str] = {},
    ssl_verify: bool = True,
) -> Tuple[io.BytesIO, Optional[FileType]]:
    response = requests.get(url, headers=headers, verify=ssl_verify)
    file = io.BytesIO(response.content)

    content_type = content_type or response.headers.get("Content-Type")
    filetype = detect_filetype(file=file, content_type=content_type)
    return file, filetype
