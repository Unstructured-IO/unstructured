from typing import IO, List, Optional

from unstructured.documents.elements import Element
from unstructured.documents.html import HTMLDocument


def partition_html(filename: str = "", file: Optional[IO] = None, text: str = "") -> List[Element]:
    """Partitions an HTML document into its constituent elements.

    Parameters
    ----------
     filename
        A string defining the target filename path.
    file
        A file-like object using "r" mode --> open(filename, "r").
        text
                The string representation of the HTML document.
    """
    if not any([filename, file, text]):
        raise ValueError("One of filename, file, or text must be specified.")

    if filename and not file and not text:
        document = HTMLDocument.from_file(filename)
        elements = document.elements

    elif file and not filename and not text:
        text = file.read()
        document = HTMLDocument.from_string(text)
        elements = document.elements

    elif text and not filename and not file:
        document = HTMLDocument.from_string(text)
        elements = document.elements

    else:
        raise ValueError("Only one of filename, file, or text can be specified.")

    return elements
