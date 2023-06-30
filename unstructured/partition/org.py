from typing import IO, List, Optional

from unstructured.documents.elements import Element
from unstructured.file_utils.filetype import FileType, add_metadata_with_filetype
from unstructured.partition.html import convert_and_partition_html


@add_metadata_with_filetype(FileType.ORG)
def partition_org(
    filename: Optional[str] = None,
    file: Optional[IO] = None,
    include_page_breaks: bool = False,
    include_metadata: bool = True,
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
    """
    return convert_and_partition_html(
        source_format="org",
        filename=filename,
        file=file,
        include_page_breaks=include_page_breaks,
    )
