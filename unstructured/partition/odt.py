from typing import IO, List, Optional

from unstructured.documents.elements import Element, process_metadata
from unstructured.file_utils.filetype import FileType, add_metadata_with_filetype
from unstructured.partition.docx import convert_and_partition_docx


@process_metadata()
@add_metadata_with_filetype(FileType.ODT)
def partition_odt(
    filename: Optional[str] = None,
    file: Optional[IO[bytes]] = None,
    include_metadata: bool = True,
    metadata_filename: Optional[str] = None,
    include_element_types: Optional[List[Element]] = None,
    exclude_element_types: Optional[List[Element]] = None,
    **kwargs,
) -> List[Element]:
    """Partitions Open Office Documents in .odt format into its document elements.

    Parameters
    ----------
    filename
        A string defining the target filename path.
    file
        A file-like object using "rb" mode --> open(filename, "rb").
    include_element_types
        Determines which Elements included in the output.
    exclude_element_types
        Determines which Elements excluded in the output.
    """
    return convert_and_partition_docx(
        source_format="odt",
        filename=filename,
        file=file,
        metadata_filename=metadata_filename,
        include_element_types=include_element_types,
        exclude_element_types=exclude_element_types,
    )
