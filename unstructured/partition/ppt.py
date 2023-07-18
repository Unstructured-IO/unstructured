import os
import tempfile
from typing import IO, List, Optional

from unstructured.documents.elements import Element, process_metadata
from unstructured.file_utils.filetype import FileType, add_metadata_with_filetype
from unstructured.partition.common import (
    convert_office_doc,
    exactly_one,
    filter_element_types,
)
from unstructured.partition.pptx import partition_pptx


@process_metadata()
@add_metadata_with_filetype(FileType.PPT)
def partition_ppt(
    filename: Optional[str] = None,
    file: Optional[IO[bytes]] = None,
    include_page_breaks: bool = False,
    include_metadata: bool = True,
    metadata_filename: Optional[str] = None,
    include_element_types: Optional[List[Element]] = None,
    exclude_element_types: Optional[List[Element]] = None,
    **kwargs,
) -> List[Element]:
    """Partitions Microsoft PowerPoint Documents in .ppt format into their document elements.

    Parameters
    ----------
    filename
        A string defining the target filename path.
    file
        A file-like object using "rb" mode --> open(filename, "rb").
    include_page_breaks
        If True, includes a PageBreak element between slides
    include_element_types
        Determines which Elements included in the output.
    exclude_element_types
        Determines which Elements excluded in the output.
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
    elif file is not None:
        tmp = tempfile.NamedTemporaryFile(delete=False)
        tmp.write(file.read())
        tmp.close()
        filename = tmp.name
        _, filename_no_path = os.path.split(os.path.abspath(tmp.name))

    base_filename, _ = os.path.splitext(filename_no_path)

    with tempfile.TemporaryDirectory() as tmpdir:
        convert_office_doc(
            filename,
            tmpdir,
            target_format="pptx",
            target_filter="Impress MS PowerPoint 2007 XML",
        )
        pptx_filename = os.path.join(tmpdir, f"{base_filename}.pptx")
        elements = partition_pptx(
            filename=pptx_filename,
            metadata_filename=metadata_filename,
        )

    # remove tmp.name from filename if parsing file
    if file:
        for element in elements:
            element.metadata.filename = metadata_filename

    if include_element_types or exclude_element_types:
        elements = filter_element_types(
            elements=elements,
            include_element_types=include_element_types,
            exclude_element_types=exclude_element_types,
        )
    return elements
