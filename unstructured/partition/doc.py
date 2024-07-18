from __future__ import annotations

import os
import tempfile
from typing import IO, Any, Optional

from unstructured.chunking import add_chunking_strategy
from unstructured.documents.elements import Element, process_metadata
from unstructured.file_utils.filetype import add_metadata_with_filetype
from unstructured.file_utils.model import FileType
from unstructured.partition.common import (
    convert_office_doc,
    exactly_one,
    get_last_modified,
)
from unstructured.partition.docx import partition_docx


@process_metadata()
@add_metadata_with_filetype(FileType.DOC)
@add_chunking_strategy
def partition_doc(
    filename: Optional[str] = None,
    file: Optional[IO[bytes]] = None,
    include_page_breaks: bool = True,
    metadata_filename: Optional[str] = None,
    metadata_last_modified: Optional[str] = None,
    libre_office_filter: Optional[str] = "MS Word 2007 XML",
    languages: Optional[list[str]] = ["auto"],
    detect_language_per_element: bool = False,
    date_from_file_object: bool = False,
    starting_page_number: int = 1,
    strategy: Optional[str] = None,
    **kwargs: Any,
) -> list[Element]:
    """Partitions Microsoft Word Documents in .doc format into its document elements.

    Parameters
    ----------
    filename
        A string defining the target filename path.
    file
        A file-like object using "rb" mode --> open(filename, "rb").
    metadata_last_modified
        The last modified date for the document.
    libre_office_filter
        The filter to use when coverting to .doc. The default is the
        filter that is required when using LibreOffice7. Pass in None
        if you do not want to apply any filter.
    languages
        User defined value for `metadata.languages` if provided. Otherwise language is detected
        using naive Bayesian filter via `langdetect`. Multiple languages indicates text could be
        in either language.
        Additional Parameters:
            detect_language_per_element
                Detect language per element instead of at the document level.
    date_from_file_object
        Applies only when providing file via `file` parameter. If this option is True, attempt
        infer last_modified metadata from bytes, otherwise set it to None.
    starting_page_number
        Indicates what page number should be assigned to the first page in the document.
        This information will be reflected in elements' metadata and can be be especially
        useful when partitioning a document that is part of a larger document.
    """
    exactly_one(filename=filename, file=file)

    last_modified = get_last_modified(filename, file, date_from_file_object)

    # -- validate file-path when provided so we can provide a more meaningful error --
    if filename is not None and not os.path.exists(filename):
        raise ValueError(f"The file {filename} does not exist.")

    # -- `convert_office_doc` uses a command-line program that ships with LibreOffice to convert
    # -- from DOC -> DOCX. So both the source and the target need to be file-system files. Put
    # -- transient files in a temporary directory that is automatically removed so they don't
    # -- pile up.
    with tempfile.TemporaryDirectory() as target_dir:
        source_file_path = f"{target_dir}/document.doc" if file is not None else filename
        assert source_file_path is not None

        # -- when source is a file-like object, write it to the filesystem so the command-line
        # -- process can access it (CLI executes in different memory-space).
        if file is not None:
            with open(source_file_path, "wb") as f:
                f.write(file.read())

        # -- convert the .doc file to .docx. The resulting file takes the same base-name as the
        # -- source file and is written to `target_dir`.
        convert_office_doc(
            source_file_path,
            target_dir,
            target_format="docx",
            target_filter=libre_office_filter,
        )

        # -- compute the path of the resulting .docx document --
        _, filename_no_path = os.path.split(os.path.abspath(source_file_path))
        base_filename, _ = os.path.splitext(filename_no_path)
        target_file_path = os.path.join(target_dir, f"{base_filename}.docx")

        # -- and partition it. Note that `kwargs` is not passed which is a sketchy way to partially
        # -- disable post-partitioning processing (what the decorators do) so for example the
        # -- resulting elements are not double-chunked.
        elements = partition_docx(
            filename=target_file_path,
            detect_language_per_element=detect_language_per_element,
            include_page_breaks=include_page_breaks,
            languages=languages,
            metadata_filename=metadata_filename,
            metadata_last_modified=metadata_last_modified or last_modified,
            starting_page_number=starting_page_number,
            strategy=strategy,
        )

    # -- Remove temporary document.docx path from metadata when necessary. Note `metadata_filename`
    # -- defaults to `None` but that's better than a meaningless temporary filename.
    if file:
        for element in elements:
            element.metadata.filename = metadata_filename

    return elements
