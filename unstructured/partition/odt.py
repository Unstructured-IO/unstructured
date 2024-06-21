from __future__ import annotations

import os
import tempfile
from typing import IO, Any, Optional, cast

from unstructured.chunking import add_chunking_strategy
from unstructured.documents.elements import Element, process_metadata
from unstructured.file_utils.filetype import FileType, add_metadata_with_filetype
from unstructured.partition.common import exactly_one, get_last_modified
from unstructured.partition.docx import partition_docx
from unstructured.utils import requires_dependencies


@process_metadata()
@add_metadata_with_filetype(FileType.ODT)
@add_chunking_strategy
def partition_odt(
    filename: Optional[str] = None,
    *,
    date_from_file_object: bool = False,
    detect_language_per_element: bool = False,
    file: Optional[IO[bytes]] = None,
    infer_table_structure: bool = True,
    languages: Optional[list[str]] = ["auto"],
    metadata_filename: Optional[str] = None,
    metadata_last_modified: Optional[str] = None,
    starting_page_number: int = 1,
    strategy: Optional[str] = None,
    **kwargs: Any,
) -> list[Element]:
    """Partitions Open Office Documents in .odt format into its document elements.

    Parameters
    ----------
    filename
        A string defining the target filename path.
    file
        A file-like object using "rb" mode --> open(filename, "rb").
    infer_table_structure
        If True, any Table elements that are extracted will also have a metadata field
        named "text_as_html" where the table's text content is rendered into an html string.
        I.e., rows and cells are preserved.
        Whether True or False, the "text" field is always present in any Table element
        and is the text content of the table (no structure).
    metadata_last_modified
        The last modified date for the document.
    languages
        User defined value for `metadata.languages` if provided. Otherwise language is detected
        using naive Bayesian filter via `langdetect`. Multiple languages indicates text could be
        in either language.
        Additional Parameters:
            detect_language_per_element
                Detect language per element instead of at the document level.
    date_from_file_object
        Applies only when providing file via `file` parameter. If this option is True, attempt
        infer last_modified metadata from the file-like object, otherwise set it to None.
    """

    with tempfile.TemporaryDirectory() as target_dir:
        docx_path = _convert_odt_to_docx(target_dir, filename, file)
        elements = partition_docx(
            filename=docx_path,
            detect_language_per_element=detect_language_per_element,
            infer_table_structure=infer_table_structure,
            languages=languages,
            metadata_filename=metadata_filename,
            metadata_last_modified=(
                metadata_last_modified or get_last_modified(filename, file, date_from_file_object)
            ),
            starting_page_number=starting_page_number,
            strategy=strategy,
        )

    return elements


@requires_dependencies("pypandoc")
def _convert_odt_to_docx(
    target_dir: str, filename: Optional[str], file: Optional[IO[bytes]]
) -> str:
    """Convert ODT document to DOCX returning the new .docx file's path.

    Parameters
    ----------
    target_dir
        The str directory-path to use for conversion purposes. The new DOCX file is written to this
        directory. When passed as a file-like object, a copy of the source file is written here as
        well. It is the caller's responsibility to remove this directory and its contents when
        they are no longer needed.
    filename
        A str file-path specifying the location of the source ODT file on the local filesystem.
    file
        A file-like object open for reading in binary mode ("rb" mode).
    """
    exactly_one(filename=filename, file=file)

    # -- validate file-path when provided so we can provide a more meaningful error than whatever
    # -- would come from pandoc.
    if filename is not None and not os.path.exists(filename):
        raise ValueError(f"The file {filename} does not exist.")

    # -- Pandoc is a command-line program running in its own memory-space. It can therefore only
    # -- operate on files on the filesystem. If the source document was passed as `file`, write
    # -- it to `target_dir/document.odt` and use that path as the source-path.
    source_file_path = f"{target_dir}/document.odt" if file is not None else cast(str, filename)
    if file is not None:
        with open(source_file_path, "wb") as f:
            f.write(file.read())

    # -- Compute the path of the resulting .docx document. We want its file-name to be preserved
    # -- if the source-document was provided as `filename`.
    # -- a/b/foo.odt -> foo.odt --
    file_name = os.path.basename(source_file_path)
    # -- foo.odt -> foo --
    base_name, _ = os.path.splitext(file_name)
    # -- foo -> foo.docx --
    target_docx_path = os.path.join(target_dir, f"{base_name}.docx")

    import pypandoc

    pypandoc.convert_file(
        source_file_path,
        "docx",
        format="odt",
        outputfile=target_docx_path,
    )

    return target_docx_path
