from typing import IO, List, Optional

from unstructured.documents.elements import Element
from unstructured.file_utils.file_conversion import convert_epub_to_html
from unstructured.partition.html import partition_html


def partition_epub(
    filename: Optional[str] = None,
    file: Optional[IO] = None,
    include_page_breaks: bool = False,
) -> List[Element]:
    """Partitions an EPUB document. The document is first converted to HTML and then
    partitoned using partiton_html.

    Parameters
    ----------
     filename
        A string defining the target filename path.
    file
        A file-like object using "rb" mode --> open(filename, "rb").
    include_page_breaks
        If True, the output will include page breaks if the filetype supports it
    """
    html_text = convert_epub_to_html(filename=filename, file=file)
    # NOTE(robinson) - pypandoc returns a text string with unicode encoding
    # ref: https://github.com/JessicaTegner/pypandoc#usage
    return partition_html(
        text=html_text,
        include_page_breaks=include_page_breaks,
        encoding="unicode",
    )
