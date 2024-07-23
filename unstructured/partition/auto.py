"""Provides partitioning with automatic file-type detection."""

from __future__ import annotations

import importlib
import io
from typing import IO, Any, Callable, Literal, Optional

import requests
from typing_extensions import TypeAlias

from unstructured.documents.elements import DataSourceMetadata, Element
from unstructured.file_utils.filetype import detect_filetype, is_json_processable
from unstructured.file_utils.model import FileType
from unstructured.logger import logger
from unstructured.partition.common import exactly_one
from unstructured.partition.lang import check_language_args
from unstructured.partition.utils.constants import PartitionStrategy
from unstructured.utils import dependency_exists

Partitioner: TypeAlias = Callable[..., list[Element]]


def partition(
    filename: Optional[str] = None,
    *,
    content_type: Optional[str] = None,
    file: Optional[IO[bytes]] = None,
    file_filename: Optional[str] = None,
    url: Optional[str] = None,
    include_page_breaks: bool = False,
    strategy: str = PartitionStrategy.AUTO,
    encoding: Optional[str] = None,
    paragraph_grouper: Optional[Callable[[str], str]] | Literal[False] = None,
    headers: dict[str, str] = {},
    skip_infer_table_types: list[str] = ["pdf", "jpg", "png", "heic"],
    ssl_verify: bool = True,
    ocr_languages: Optional[str] = None,  # changing to optional for deprecation
    languages: Optional[list[str]] = None,
    detect_language_per_element: bool = False,
    pdf_infer_table_structure: bool = False,
    extract_images_in_pdf: bool = False,
    extract_image_block_types: Optional[list[str]] = None,
    extract_image_block_output_dir: Optional[str] = None,
    extract_image_block_to_payload: bool = False,
    xml_keep_tags: bool = False,
    data_source_metadata: Optional[DataSourceMetadata] = None,
    metadata_filename: Optional[str] = None,
    request_timeout: Optional[int] = None,
    hi_res_model_name: Optional[str] = None,
    model_name: Optional[str] = None,  # to be deprecated
    date_from_file_object: bool = False,
    starting_page_number: int = 1,
    **kwargs: Any,
):
    """Partitions a document into its constituent elements.

    Uses libmagic to determine the file's type and route it to the appropriate partitioning
    function. Applies the default parameters for each partitioning function. Use the document-type
    specific partitioning functions if you need access to additional kwarg options.

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
        Deprecated! Use `skip_infer_table_types` to opt out of table extraction for any document
        type.
        If True and strategy=hi_res, any Table Elements extracted from a PDF will include an
        additional metadata field, "text_as_html," where the value (string) is a just a
        transformation of the data into an HTML <table>.
        The "text" field for a partitioned Table Element is always present, whether True or False.
    extract_images_in_pdf
        Only applicable if `strategy=hi_res`.
        If True, any detected images will be saved in the path specified by
        'extract_image_block_output_dir' or stored as base64 encoded data within metadata fields.
        Deprecation Note: This parameter is marked for deprecation. Future versions will use
        'extract_image_block_types' for broader extraction capabilities.
    extract_image_block_types
        Only applicable if `strategy=hi_res`.
        Images of the element type(s) specified in this list (e.g., ["Image", "Table"]) will be
        saved in the path specified by 'extract_image_block_output_dir' or stored as base64
        encoded data within metadata fields.
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
    xml_keep_tags
        If True, will retain the XML tags in the output. Otherwise it will simply extract
        the text from within the tags. Only applies to partition_xml.
    request_timeout
        The timeout for the HTTP request if URL is set. Defaults to None meaning no timeout and
        requests will block indefinitely.
    hi_res_model_name
        The layout detection model used when partitioning strategy is set to `hi_res`.
    model_name
        The layout detection model used when partitioning strategy is set to `hi_res`. To be
        deprecated in favor of `hi_res_model_name`.
    date_from_file_object
        Applies only when providing file via `file` parameter. If this option is True and inference
        from message header failed, attempt to infer last_modified metadata from bytes,
        otherwise set it to None.
    starting_page_number
        Indicates what page number should be assigned to the first page in the document.
        This information will be reflected in elements' metadata and can be be especially
        useful when partitioning a document that is part of a larger document.
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
    kwargs.setdefault("date_from_file_object", date_from_file_object)

    if pdf_infer_table_structure:
        logger.warning(
            "The pdf_infer_table_structure kwarg is deprecated. Please use skip_infer_table_types "
            "instead."
        )

    languages = check_language_args(languages or [], ocr_languages)

    if url is not None:
        file, file_type = file_and_type_from_url(
            url=url,
            content_type=content_type,
            headers=headers,
            ssl_verify=ssl_verify,
            request_timeout=request_timeout,
        )
    else:
        if headers != {}:
            logger.warning(
                "The headers kwarg is set but the url kwarg is not. "
                "The headers kwarg will be ignored.",
            )
        file_type = detect_filetype(
            file_path=filename,
            file=file,
            encoding=encoding,
            content_type=content_type,
            metadata_file_path=metadata_filename,
        )

    if file is not None:
        file.seek(0)

    infer_table_structure = decide_table_extraction(
        file_type,
        skip_infer_table_types,
        pdf_infer_table_structure,
    )

    partitioner_loader = _PartitionerLoader()

    if file_type == FileType.CSV:
        partition_csv = partitioner_loader.get(file_type)
        elements = partition_csv(
            filename=filename,
            file=file,
            infer_table_structure=infer_table_structure,
            languages=languages,
            detect_language_per_element=detect_language_per_element,
            **kwargs,
        )
    elif file_type == FileType.DOC:
        partition_doc = partitioner_loader.get(file_type)
        elements = partition_doc(
            filename=filename,
            file=file,
            infer_table_structure=infer_table_structure,
            languages=languages,
            detect_language_per_element=detect_language_per_element,
            starting_page_number=starting_page_number,
            strategy=strategy,
            **kwargs,
        )
    elif file_type == FileType.DOCX:
        partition_docx = partitioner_loader.get(file_type)
        elements = partition_docx(
            filename=filename,
            file=file,
            infer_table_structure=infer_table_structure,
            languages=languages,
            detect_language_per_element=detect_language_per_element,
            starting_page_number=starting_page_number,
            strategy=strategy,
            **kwargs,
        )
    elif file_type == FileType.EML:
        partition_email = partitioner_loader.get(file_type)
        elements = partition_email(
            filename=filename,
            file=file,
            encoding=encoding,
            languages=languages,
            detect_language_per_element=detect_language_per_element,
            **kwargs,
        )
    elif file_type == FileType.EPUB:
        partition_epub = partitioner_loader.get(file_type)
        elements = partition_epub(
            filename=filename,
            file=file,
            include_page_breaks=include_page_breaks,
            infer_table_structure=infer_table_structure,
            languages=languages,
            detect_language_per_element=detect_language_per_element,
            **kwargs,
        )
    elif file_type == FileType.HTML:
        partition_html = partitioner_loader.get(file_type)
        elements = partition_html(
            filename=filename,
            file=file,
            include_page_breaks=include_page_breaks,
            encoding=encoding,
            languages=languages,
            detect_language_per_element=detect_language_per_element,
            **kwargs,
        )
    elif file_type.partitioner_shortname == "image":
        partition_image = partitioner_loader.get(file_type)
        elements = partition_image(
            filename=filename,
            file=file,
            url=None,
            include_page_breaks=include_page_breaks,
            infer_table_structure=infer_table_structure,
            strategy=strategy,
            languages=languages,
            hi_res_model_name=hi_res_model_name or model_name,
            extract_images_in_pdf=extract_images_in_pdf,
            extract_image_block_types=extract_image_block_types,
            extract_image_block_output_dir=extract_image_block_output_dir,
            extract_image_block_to_payload=extract_image_block_to_payload,
            starting_page_number=starting_page_number,
            **kwargs,
        )
    elif file_type == FileType.JSON:
        if not is_json_processable(filename=filename, file=file):
            raise ValueError(
                "Detected a JSON file that does not conform to the Unstructured schema. "
                "partition_json currently only processes serialized Unstructured output.",
            )
        partition_json = partitioner_loader.get(file_type)
        elements = partition_json(filename=filename, file=file, **kwargs)
    elif file_type == FileType.MD:
        partition_md = partitioner_loader.get(file_type)
        elements = partition_md(
            filename=filename,
            file=file,
            include_page_breaks=include_page_breaks,
            infer_table_structure=infer_table_structure,
            languages=languages,
            detect_language_per_element=detect_language_per_element,
            **kwargs,
        )
    elif file_type == FileType.MSG:
        partition_msg = partitioner_loader.get(file_type)
        elements = partition_msg(
            filename=filename,
            file=file,
            languages=languages,
            detect_language_per_element=detect_language_per_element,
            **kwargs,
        )
    elif file_type == FileType.ODT:
        partition_odt = partitioner_loader.get(file_type)
        elements = partition_odt(
            filename=filename,
            file=file,
            infer_table_structure=infer_table_structure,
            languages=languages,
            detect_language_per_element=detect_language_per_element,
            starting_page_number=starting_page_number,
            strategy=strategy,
            **kwargs,
        )
    elif file_type == FileType.ORG:
        partition_org = partitioner_loader.get(file_type)
        elements = partition_org(
            filename=filename,
            file=file,
            include_page_breaks=include_page_breaks,
            languages=languages,
            detect_language_per_element=detect_language_per_element,
            **kwargs,
        )
    elif file_type == FileType.PDF:
        partition_pdf = partitioner_loader.get(file_type)
        elements = partition_pdf(
            filename=filename,
            file=file,
            url=None,
            include_page_breaks=include_page_breaks,
            infer_table_structure=infer_table_structure,
            strategy=strategy,
            languages=languages,
            hi_res_model_name=hi_res_model_name or model_name,
            extract_images_in_pdf=extract_images_in_pdf,
            extract_image_block_types=extract_image_block_types,
            extract_image_block_output_dir=extract_image_block_output_dir,
            extract_image_block_to_payload=extract_image_block_to_payload,
            starting_page_number=starting_page_number,
            **kwargs,
        )
    elif file_type == FileType.PPT:
        partition_ppt = partitioner_loader.get(file_type)
        elements = partition_ppt(
            filename=filename,
            file=file,
            include_page_breaks=include_page_breaks,
            infer_table_structure=infer_table_structure,
            languages=languages,
            detect_language_per_element=detect_language_per_element,
            strategy=strategy,
            **kwargs,
        )
    elif file_type == FileType.PPTX:
        partition_pptx = partitioner_loader.get(file_type)
        elements = partition_pptx(
            filename=filename,
            file=file,
            include_page_breaks=include_page_breaks,
            infer_table_structure=infer_table_structure,
            languages=languages,
            detect_language_per_element=detect_language_per_element,
            starting_page_number=starting_page_number,
            strategy=strategy,
            **kwargs,
        )
    elif file_type == FileType.RST:
        partition_rst = partitioner_loader.get(file_type)
        elements = partition_rst(
            filename=filename,
            file=file,
            include_page_breaks=include_page_breaks,
            infer_table_structure=infer_table_structure,
            languages=languages,
            detect_language_per_element=detect_language_per_element,
            **kwargs,
        )
    elif file_type == FileType.RTF:
        partition_rtf = partitioner_loader.get(file_type)
        elements = partition_rtf(
            filename=filename,
            file=file,
            include_page_breaks=include_page_breaks,
            infer_table_structure=infer_table_structure,
            languages=languages,
            detect_language_per_element=detect_language_per_element,
            **kwargs,
        )
    elif file_type == FileType.TSV:
        partition_tsv = partitioner_loader.get(file_type)
        elements = partition_tsv(
            filename=filename,
            file=file,
            languages=languages,
            detect_language_per_element=detect_language_per_element,
            **kwargs,
        )
    elif file_type == FileType.TXT:
        partition_text = partitioner_loader.get(file_type)
        elements = partition_text(
            filename=filename,
            file=file,
            encoding=encoding,
            paragraph_grouper=paragraph_grouper,
            languages=languages,
            detect_language_per_element=detect_language_per_element,
            **kwargs,
        )
    elif file_type in (FileType.XLS, FileType.XLSX):
        partition_xlsx = partitioner_loader.get(file_type)
        elements = partition_xlsx(
            filename=filename,
            file=file,
            infer_table_structure=infer_table_structure,
            languages=languages,
            detect_language_per_element=detect_language_per_element,
            starting_page_number=starting_page_number,
            **kwargs,
        )
    elif file_type == FileType.XML:
        partition_xml = partitioner_loader.get(file_type)
        elements = partition_xml(
            filename=filename,
            file=file,
            encoding=encoding,
            xml_keep_tags=xml_keep_tags,
            languages=languages,
            detect_language_per_element=detect_language_per_element,
            **kwargs,
        )
    elif file_type == FileType.EMPTY:
        elements = []
    else:
        msg = "Invalid file" if not filename else f"Invalid file {filename}"
        raise ValueError(f"{msg}. The {file_type} file type is not supported in partition.")

    for element in elements:
        element.metadata.url = url
        element.metadata.data_source = data_source_metadata
        if content_type is not None:
            out_filetype = FileType.from_mime_type(content_type)
            element.metadata.filetype = out_filetype.mime_type if out_filetype is not None else None
        else:
            element.metadata.filetype = file_type.mime_type

    return elements


def file_and_type_from_url(
    url: str,
    content_type: Optional[str] = None,
    headers: dict[str, str] = {},
    ssl_verify: bool = True,
    request_timeout: Optional[int] = None,
) -> tuple[io.BytesIO, FileType]:
    response = requests.get(url, headers=headers, verify=ssl_verify, timeout=request_timeout)
    file = io.BytesIO(response.content)

    if content_type := content_type or response.headers.get("Content-Type", None):
        content_type = content_type.split(";")[0].strip().lower()

    # -- non-None when response is textual --
    encoding = response.encoding

    filetype = detect_filetype(file=file, encoding=encoding, content_type=content_type)
    return file, filetype


def decide_table_extraction(
    filetype: Optional[FileType],
    skip_infer_table_types: list[str],
    pdf_infer_table_structure: bool,
) -> bool:
    doc_type = filetype.name.lower() if filetype else None

    if doc_type == "pdf":
        # For backwards compatibility. Ultimately we want to remove pdf_infer_table_structure
        # completely and rely exclusively on `skip_infer_table_types` for all file types.
        # Until then for pdf files we first check pdf_infer_table_structure and then update
        # based on skip_infer_tables.
        return pdf_infer_table_structure or doc_type not in skip_infer_table_types

    return doc_type not in skip_infer_table_types


class _PartitionerLoader:
    """Provides uniform helpful error when a partitioner dependency is not installed.

    Used by `partition()` to encapsulate coping with the possibility the Python
    environment it is executing in may not have all dependencies installed for a
    particular partitioner.

    Provides `.get()` to access partitioners by file-type, which raises when one or
    more dependencies for that partitioner are not installed.

    The error message indicates what extra needs to be installed to enable that
    partitioner. This avoids an inconsistent variety of possibly puzzling exceptions
    arising from much deeper in the partitioner when access to the missing dependency is
    first attempted.
    """

    # -- module-lifetime cache for partitioners once loaded --
    _partitioners: dict[FileType, Partitioner] = {}

    def get(self, file_type: FileType) -> Partitioner:
        """Return partitioner for `file_type`.

        Raises when one or more package dependencies for that file-type have not been
        installed.
        """
        if file_type not in self._partitioners:
            self._partitioners[file_type] = self._load_partitioner(file_type)

        return self._partitioners[file_type]

    def _load_partitioner(self, file_type: FileType) -> Partitioner:
        """Load the partitioner for `file_type` after verifying dependencies."""
        # -- verify all package dependencies are installed --
        for pkg_name in file_type.importable_package_dependencies:
            if not dependency_exists(pkg_name):
                raise ImportError(
                    f"{file_type.partitioner_function_name}() is not available because one or"
                    f" more dependencies are not installed. Use:"
                    f' pip install "unstructured[{file_type.extra_name}]" (including quotes)'
                    f" to install the required dependencies",
                )

        # -- load the partitioner and return it --
        assert file_type.is_partitionable  # -- would be a programming error if this failed --
        partitioner_module = importlib.import_module(file_type.partitioner_module_qname)
        return getattr(partitioner_module, file_type.partitioner_function_name)
