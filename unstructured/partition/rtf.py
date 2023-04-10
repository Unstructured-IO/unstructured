from typing import IO, List, Optional

from unstructured.documents.elements import Element
from unstructured.partition.html import convert_and_partition_html


def partition_rtf(
    filename: Optional[str] = None,
    file: Optional[IO] = None,
    include_page_breaks: bool = False,
) -> List[Element]:
    """Partitions an RTF document. The document is first converted to HTML and then
    partitioned using partiton_html.

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
        source_format="rtf",
        filename=filename,
        file=file,
        include_page_breaks=include_page_breaks,
    )
