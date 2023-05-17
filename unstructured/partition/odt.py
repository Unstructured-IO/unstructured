from typing import IO, List, Optional

from unstructured.documents.elements import Element
from unstructured.file_utils.filetype import FileType, add_metadata_with_filetype
from unstructured.partition.docx import convert_and_partition_docx


@add_metadata_with_filetype(FileType.ODT)
def partition_odt(filename: Optional[str] = None, file: Optional[IO] = None) -> List[Element]:
    """Partitions Open Office Documents in .odt format into its document elements.

    Parameters
    ----------
    filename
        A string defining the target filename path.
    file
        A file-like object using "rb" mode --> open(filename, "rb").
    """
    return convert_and_partition_docx(source_format="odt", filename=filename, file=file)
