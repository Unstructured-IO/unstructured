from __future__ import annotations

import os
import tempfile
from typing import IO, Any, Optional, cast

from unstructured.documents.elements import Element
from unstructured.file_utils.model import FileType
from unstructured.partition.common.common import exactly_one
from unstructured.partition.common.metadata import get_last_modified_date
from unstructured.partition.docx import partition_docx
from unstructured.utils import requires_dependencies


def partition_odt(
    filename: Optional[str] = None,
    *,
    file: Optional[IO[bytes]] = None,
    metadata_filename: Optional[str] = None,
    metadata_last_modified: Optional[str] = None,
    **kwargs: Any,
) -> list[Element]:
    """Partitions Open Office Documents in .odt format into its document elements.

    All parameters that are available on `partition_docx()` are also available here.

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
    """

    last_modified = get_last_modified_date(filename) if filename else None

    with tempfile.TemporaryDirectory() as target_dir:
        docx_path = _convert_odt_to_docx(target_dir, filename, file)
        elements = partition_docx(
            filename=docx_path,
            metadata_filename=metadata_filename or filename,
            metadata_file_type=FileType.ODT,
            metadata_last_modified=metadata_last_modified or last_modified,
            **kwargs,
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
