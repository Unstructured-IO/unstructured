from typing import IO, List, Optional

from unstructured.documents.elements import Element
from unstructured.file_utils.filetype import FileType, add_metadata_with_filetype
from unstructured.partition.html import convert_and_partition_html


@add_metadata_with_filetype(FileType.ORG)
def partition_org(
    filename: Optional[str] = None,
    file: Optional[IO[bytes]] = None,
    include_page_breaks: bool = False,
    include_metadata: bool = True,
    metadata_filename: Optional[str] = None,
    include_element_types: Optional[List[Element]] = None,
    exclude_element_types: Optional[List[Element]] = None,
) -> List[Element]:
    """Partitions an org document. The document is first converted to HTML and then
    partitioned using partition_html.

    Parameters
    ----------
    filename
        A string defining the target filename path.
    file
        A file-like object using "rb" mode --> open(filename, "rb").
    include_page_breaks
        If True, the output will include page breaks if the filetype supports it
    include_element_types
        Determines which Elements included in the output.
    exclude_element_types
        Determines which Elements excluded in the output.
    """
    return convert_and_partition_html(
        source_format="org",
        filename=filename,
        file=file,
        include_page_breaks=include_page_breaks,
        metadata_filename=metadata_filename,
        include_element_types=include_element_types,
        exclude_element_types=exclude_element_types,
    )
