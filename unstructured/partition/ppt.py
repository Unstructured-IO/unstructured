import os
import tempfile
from typing import IO, List, Optional

from unstructured.documents.elements import Element, process_metadata
from unstructured.file_utils.filetype import FileType, add_metadata_with_filetype
from unstructured.partition.common import convert_office_doc, exactly_one
from unstructured.partition.pptx import partition_pptx


@process_metadata()
@add_metadata_with_filetype(FileType.PPT)
def partition_ppt(
    filename: Optional[str] = None,
    file: Optional[IO] = None,
    include_page_breaks: bool = False,
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
        convert_office_doc(filename, tmpdir, target_format="pptx")
        pptx_filename = os.path.join(tmpdir, f"{base_filename}.pptx")
        elements = partition_pptx(filename=pptx_filename, metadata_filename=filename)

    return elements
