import io
from typing import IO, Callable, Dict, List, Optional, Tuple

import requests

from unstructured.documents.elements import DataSourceMetadata
from unstructured.file_utils.filetype import (
    FILETYPE_TO_MIMETYPE,
    STR_TO_FILETYPE,
    FileType,
    detect_filetype,
    is_json_processable,
)
from unstructured.logger import logger
from unstructured.partition.common import exactly_one
from unstructured.partition.email import partition_email
from unstructured.partition.html import partition_html
from unstructured.partition.json import partition_json
from unstructured.partition.lang import (
    convert_old_ocr_languages_to_languages,
)
from unstructured.partition.text import partition_text
from unstructured.partition.xml import partition_xml
from unstructured.utils import dependency_exists

PARTITION_WITH_EXTRAS_MAP: Dict[str, Callable] = {}

if dependency_exists("pandas"):
    from unstructured.partition.csv import partition_csv
    from unstructured.partition.tsv import partition_tsv

    PARTITION_WITH_EXTRAS_MAP["csv"] = partition_csv
    PARTITION_WITH_EXTRAS_MAP["tsv"] = partition_tsv


if dependency_exists("docx"):
    from unstructured.partition.doc import partition_doc
    from unstructured.partition.docx import partition_docx

    PARTITION_WITH_EXTRAS_MAP["doc"] = partition_doc
    PARTITION_WITH_EXTRAS_MAP["docx"] = partition_docx


if dependency_exists("docx") and dependency_exists("pypandoc"):
    from unstructured.partition.odt import partition_odt

    PARTITION_WITH_EXTRAS_MAP["odt"] = partition_odt


if dependency_exists("ebooklib"):
    from unstructured.partition.epub import partition_epub

    PARTITION_WITH_EXTRAS_MAP["epub"] = partition_epub


if dependency_exists("pypandoc"):
    from unstructured.partition.org import partition_org
    from unstructured.partition.rst import partition_rst
    from unstructured.partition.rtf import partition_rtf

    PARTITION_WITH_EXTRAS_MAP["org"] = partition_org
    PARTITION_WITH_EXTRAS_MAP["rst"] = partition_rst
    PARTITION_WITH_EXTRAS_MAP["rtf"] = partition_rtf


if dependency_exists("markdown"):
    from unstructured.partition.md import partition_md

    PARTITION_WITH_EXTRAS_MAP["md"] = partition_md


if dependency_exists("msg_parser"):
    from unstructured.partition.msg import partition_msg

    PARTITION_WITH_EXTRAS_MAP["msg"] = partition_msg


pdf_imports = ["pdf2image", "pdfminer", "PIL"]
if all(dependency_exists(dep) for dep in pdf_imports):
    from unstructured.partition.pdf import partition_pdf

    PARTITION_WITH_EXTRAS_MAP["pdf"] = partition_pdf


if dependency_exists("unstructured_inference"):
    from unstructured.partition.image import partition_image

    PARTITION_WITH_EXTRAS_MAP["image"] = partition_image


if dependency_exists("pptx"):
    from unstructured.partition.ppt import partition_ppt
    from unstructured.partition.pptx import partition_pptx

    PARTITION_WITH_EXTRAS_MAP["ppt"] = partition_ppt
    PARTITION_WITH_EXTRAS_MAP["pptx"] = partition_pptx


if dependency_exists("pandas") and dependency_exists("openpyxl"):
    from unstructured.partition.xlsx import partition_xlsx

    PARTITION_WITH_EXTRAS_MAP["xlsx"] = partition_xlsx


def _get_partition_with_extras(
    doc_type: str,
    partition_with_extras_map: Optional[Dict[str, Callable]] = None,
):
    if partition_with_extras_map is None:
        partition_with_extras_map = PARTITION_WITH_EXTRAS_MAP
    _partition_func = partition_with_extras_map.get(doc_type)
    if _partition_func is None:
        raise ImportError(
            f"partition_{doc_type} is not available. "
            f"Install the {doc_type} dependencies with "
            f'pip install "unstructured[{doc_type}]"',
        )
    return _partition_func


def partition(
    filename: Optional[str] = None,
    content_type: Optional[str] = None,
    file: Optional[IO[bytes]] = None,
    file_filename: Optional[str] = None,
    url: Optional[str] = None,
    include_page_breaks: bool = False,
    strategy: str = "auto",
    encoding: Optional[str] = None,
    paragraph_grouper: Optional[Callable[[str], str]] = None,
    headers: Dict[str, str] = {},
    skip_infer_table_types: List[str] = ["pdf", "jpg", "png", "xls", "xlsx"],
    ssl_verify: bool = True,
    ocr_languages: Optional[str] = None,  # changing to optional for deprecation
    languages: Optional[List[str]] = None,
    detect_language_per_element: bool = False,
    pdf_infer_table_structure: bool = False,
    xml_keep_tags: bool = False,
    data_source_metadata: Optional[DataSourceMetadata] = None,
    metadata_filename: Optional[str] = None,
    **kwargs,
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
    metadata_filename
        When file is not None, the filename (string) to store in element metadata. E.g. "foo.txt"
    url
        The url for a remote document. Pass in content_type if you want partition to treat
        the document as a specific content_type.
    include_page_breaks
        If True, the output will include page breaks if the filetype supports it
    strategy
        The strategy to use for partitioning PDF/image. Uses a layout detection model if set
        to 'hi_res', otherwise partition simply extracts the text from the document
        and processes it.
    encoding
        The encoding method used to decode the text input. If None, utf-8 will be used.
    headers
        The headers to be used in conjunction with the HTTP request if URL is set.
    skip_infer_table_types
        The document types that you want to skip table extraction with.
    ssl_verify
        If the URL parameter is set, determines whether or not partition uses SSL verification
        in the HTTP request.
    languages
        The languages present in the document, for use in partitioning and/or OCR. For partitioning
        image or pdf documents with Tesseract, you'll first need to install the appropriate
        Tesseract language pack. For other partitions, language is detected using naive Bayesian
        filter via `langdetect`. Multiple languages indicates text could be in either language.
        Additional Parameters:
            detect_language_per_element
                Detect language per element instead of at the document level.
    pdf_infer_table_structure
        If True and strategy=hi_res, any Table Elements extracted from a PDF will include an
        additional metadata field, "text_as_html," where the value (string) is a just a
        transformation of the data into an HTML <table>.
        The "text" field for a partitioned Table Element is always present, whether True or False.
    xml_keep_tags
        If True, will retain the XML tags in the output. Otherwise it will simply extract
        the text from within the tags. Only applies to partition_xml.
    """
    exactly_one(file=file, filename=filename, url=url)

    if metadata_filename and file_filename:
        raise ValueError(
            "Only one of metadata_filename and file_filename is specified. "
            "metadata_filename is preferred. file_filename is marked for deprecation.",
        )

    if file_filename is not None:
        metadata_filename = file_filename
        logger.warn(
            "The file_filename kwarg will be deprecated in a future version of unstructured. "
            "Please use metadata_filename instead.",
        )
    kwargs.setdefault("metadata_filename", metadata_filename)

    if ocr_languages is not None:
        # check if languages was set to anything not the default value
        # languages and ocr_languages were therefore both provided - raise error
        if languages is not None:
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
            file_filename=metadata_filename,
            content_type=content_type,
            encoding=encoding,
        )

    if file is not None:
        file.seek(0)

    infer_table_structure = decide_table_extraction(
        filetype,
        skip_infer_table_types,
        pdf_infer_table_structure,
    )

    if filetype == FileType.DOC:
        _partition_doc = _get_partition_with_extras("doc")
        elements = _partition_doc(
            filename=filename,
            file=file,
            languages=languages,
            detect_language_per_element=detect_language_per_element,
            **kwargs,
        )
    elif filetype == FileType.DOCX:
        _partition_docx = _get_partition_with_extras("docx")
        elements = _partition_docx(
            filename=filename,
            file=file,
            languages=languages,
            detect_language_per_element=detect_language_per_element,
            **kwargs,
        )
    elif filetype == FileType.ODT:
        _partition_odt = _get_partition_with_extras("odt")
        elements = _partition_odt(
            filename=filename,
            file=file,
            languages=languages,
            detect_language_per_element=detect_language_per_element,
            **kwargs,
        )
    elif filetype == FileType.EML:
        elements = partition_email(
            filename=filename,
            file=file,
            encoding=encoding,
            languages=languages,
            detect_language_per_element=detect_language_per_element,
            **kwargs,
        )
    elif filetype == FileType.MSG:
        _partition_msg = _get_partition_with_extras("msg")
        elements = _partition_msg(
            filename=filename,
            file=file,
            languages=languages,
            detect_language_per_element=detect_language_per_element,
            **kwargs,
        )
    elif filetype == FileType.HTML:
        elements = partition_html(
            filename=filename,
            file=file,
            include_page_breaks=include_page_breaks,
            encoding=encoding,
            languages=languages,
            detect_language_per_element=detect_language_per_element,
            **kwargs,
        )
    elif filetype == FileType.XML:
        elements = partition_xml(
            filename=filename,
            file=file,
            encoding=encoding,
            xml_keep_tags=xml_keep_tags,
            languages=languages,
            detect_language_per_element=detect_language_per_element,
            **kwargs,
        )
    elif filetype == FileType.EPUB:
        _partition_epub = _get_partition_with_extras("epub")
        elements = _partition_epub(
            filename=filename,
            file=file,
            include_page_breaks=include_page_breaks,
            languages=languages,
            detect_language_per_element=detect_language_per_element,
            **kwargs,
        )
    elif filetype == FileType.ORG:
        _partition_org = _get_partition_with_extras("org")
        elements = _partition_org(
            filename=filename,
            file=file,
            include_page_breaks=include_page_breaks,
            languages=languages,
            detect_language_per_element=detect_language_per_element,
            **kwargs,
        )
    elif filetype == FileType.RST:
        _partition_rst = _get_partition_with_extras("rst")
        elements = _partition_rst(
            filename=filename,
            file=file,
            include_page_breaks=include_page_breaks,
            languages=languages,
            detect_language_per_element=detect_language_per_element,
            **kwargs,
        )
    elif filetype == FileType.MD:
        _partition_md = _get_partition_with_extras("md")
        elements = _partition_md(
            filename=filename,
            file=file,
            include_page_breaks=include_page_breaks,
            languages=languages,
            detect_language_per_element=detect_language_per_element,
            **kwargs,
        )
    elif filetype == FileType.PDF:
        _partition_pdf = _get_partition_with_extras("pdf")
        elements = _partition_pdf(
            filename=filename,  # type: ignore
            file=file,  # type: ignore
            url=None,
            include_page_breaks=include_page_breaks,
            infer_table_structure=infer_table_structure,
            strategy=strategy,
            languages=languages,
            **kwargs,
        )
    elif (filetype == FileType.PNG) or (filetype == FileType.JPG) or (filetype == FileType.TIFF):
        elements = partition_image(
            filename=filename,  # type: ignore
            file=file,  # type: ignore
            url=None,
            include_page_breaks=include_page_breaks,
            infer_table_structure=infer_table_structure,
            strategy=strategy,
            languages=languages,
            **kwargs,
        )
    elif filetype == FileType.TXT:
        elements = partition_text(
            filename=filename,
            file=file,
            encoding=encoding,
            paragraph_grouper=paragraph_grouper,
            languages=languages,
            detect_language_per_element=detect_language_per_element,
            **kwargs,
        )
    elif filetype == FileType.RTF:
        _partition_rtf = _get_partition_with_extras("rtf")
        elements = _partition_rtf(
            filename=filename,
            file=file,
            include_page_breaks=include_page_breaks,
            languages=languages,
            detect_language_per_element=detect_language_per_element,
            **kwargs,
        )
    elif filetype == FileType.PPT:
        _partition_ppt = _get_partition_with_extras("ppt")
        elements = _partition_ppt(
            filename=filename,
            file=file,
            include_page_breaks=include_page_breaks,
            languages=languages,
            detect_language_per_element=detect_language_per_element,
            **kwargs,
        )
    elif filetype == FileType.PPTX:
        _partition_pptx = _get_partition_with_extras("pptx")
        elements = _partition_pptx(
            filename=filename,
            file=file,
            include_page_breaks=include_page_breaks,
            languages=languages,
            detect_language_per_element=detect_language_per_element,
            **kwargs,
        )
    elif filetype == FileType.JSON:
        if not is_json_processable(filename=filename, file=file):
            raise ValueError(
                "Detected a JSON file that does not conform to the Unstructured schema. "
                "partition_json currently only processes serialized Unstructured output.",
            )
        elements = partition_json(filename=filename, file=file, **kwargs)
    elif (filetype == FileType.XLSX) or (filetype == FileType.XLS):
        _partition_xlsx = _get_partition_with_extras("xlsx")
        elements = _partition_xlsx(
            filename=filename,
            file=file,
            languages=languages,
            detect_language_per_element=detect_language_per_element,
            **kwargs,
        )
    elif filetype == FileType.CSV:
        _partition_csv = _get_partition_with_extras("csv")
        elements = _partition_csv(
            filename=filename,
            file=file,
            languages=languages,
            detect_language_per_element=detect_language_per_element,
            **kwargs,
        )
    elif filetype == FileType.TSV:
        _partition_tsv = _get_partition_with_extras("tsv")
        elements = _partition_tsv(
            filename=filename,
            file=file,
            languages=languages,
            detect_language_per_element=detect_language_per_element,
            **kwargs,
        )
    elif filetype == FileType.EMPTY:
        elements = []
    else:
        msg = "Invalid file" if not filename else f"Invalid file {filename}"
        raise ValueError(f"{msg}. The {filetype} file type is not supported in partition.")

    for element in elements:
        element.metadata.url = url
        element.metadata.data_source = data_source_metadata
        if content_type is not None:
            out_filetype = STR_TO_FILETYPE.get(content_type)
            element.metadata.filetype = (
                FILETYPE_TO_MIMETYPE[out_filetype] if out_filetype is not None else None
            )
        else:
            element.metadata.filetype = FILETYPE_TO_MIMETYPE[filetype]

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
    encoding = response.headers.get("Content-Encoding", "utf-8")

    filetype = detect_filetype(file=file, content_type=content_type, encoding=encoding)
    return file, filetype


def decide_table_extraction(
    filetype: Optional[FileType],
    skip_infer_table_types: List[str],
    pdf_infer_table_structure: bool,
) -> bool:
    doc_type = filetype.name.lower() if filetype else None

    if doc_type == "pdf":
        if doc_type in skip_infer_table_types and pdf_infer_table_structure:
            logger.warning(
                f"Conflict between variables skip_infer_table_types: {skip_infer_table_types} "
                f"and pdf_infer_table_structure: {pdf_infer_table_structure}, "
                "please reset skip_infer_table_types to turn on table extraction for PDFs.",
            )
        return not (doc_type in skip_infer_table_types) or pdf_infer_table_structure

    return not (doc_type in skip_infer_table_types)
