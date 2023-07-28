import os
import tempfile
from typing import IO, List, Optional

from unstructured.documents.elements import Element, process_metadata
from unstructured.file_utils.filetype import FileType, add_metadata_with_filetype
from unstructured.partition.common import (
    convert_office_doc,
    exactly_one,
    get_last_modified_date,
    get_last_modified_date_from_file,
)
from unstructured.partition.docx import partition_docx


@process_metadata()
@add_metadata_with_filetype(FileType.DOC)
def partition_doc(
    filename: Optional[str] = None,
    file: Optional[IO[bytes]] = None,
    include_page_breaks: bool = True,
    include_metadata: bool = True,
    metadata_filename: Optional[str] = None,
    metadata_date: Optional[str] = None,
    libre_office_filter: Optional[str] = "MS Word 2007 XML",
    **kwargs,
) -> List[Element]:
    """Partitions Microsoft Word Documents in .doc format into its document elements.

    Parameters
    ----------
    filename
        A string defining the target filename path.
    file
        A file-like object using "rb" mode --> open(filename, "rb").
    metadata_date
        The last modified date for the document.
    libre_office_filter
        The filter to use when coverting to .doc. The default is the
        filter that is required when using LibreOffice7. Pass in None
        if you do not want to apply any filter.
    """
    # Verify that only one of the arguments was provided
    if filename is None:
        filename = ""
    exactly_one(filename=filename, file=file)

    if len(filename) > 0:
        _, filename_no_path = os.path.split(os.path.abspath(filename))
        base_filename, _ = os.path.splitext(filename_no_path)
        if not os.path.exists(filename):
            raise ValueError(f"The file {filename} does not exist.")

        last_modification_date = get_last_modified_date(filename)

    elif file is not None:
        tmp = tempfile.NamedTemporaryFile(delete=False)
        tmp.write(file.read())
        tmp.close()
        filename = tmp.name
        _, filename_no_path = os.path.split(os.path.abspath(tmp.name))
        base_filename, _ = os.path.splitext(filename_no_path)

        last_modification_date = get_last_modified_date_from_file(file)

    with tempfile.TemporaryDirectory() as tmpdir:
        convert_office_doc(
            filename,
            tmpdir,
            target_format="docx",
            target_filter=libre_office_filter,
        )
        docx_filename = os.path.join(tmpdir, f"{base_filename}.docx")
        elements = partition_docx(
            filename=docx_filename,
            metadata_filename=metadata_filename,
            include_page_breaks=include_page_breaks,
            include_metadata=include_metadata,
            metadata_date=metadata_date or last_modification_date,
        )
        # remove tmp.name from filename if parsing file
        if file:
            for element in elements:
                element.metadata.filename = metadata_filename

    return elements
