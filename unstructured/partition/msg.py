import tempfile
from typing import IO, List, Optional

import msg_parser

from unstructured.documents.elements import Element
from unstructured.partition.common import exactly_one
from unstructured.partition.html import partition_html
from unstructured.partition.text import partition_text


def partition_msg(
    filename: Optional[str] = None,
    file: Optional[IO] = None,
) -> List[Element]:
    """Partitions a MSFT Outlook .msg file

    Parameters
    ----------
    filename
        A string defining the target filename path.
    file
        A file-like object using "rb" mode --> open(filename, "rb").
    """
    exactly_one(filename=filename, file=file)

    if filename is not None:
        msg_obj = msg_parser.MsOxMessage(filename)
    elif file is not None:
        tmp = tempfile.NamedTemporaryFile(delete=False)
        tmp.write(file.read())
        tmp.close()
        msg_obj = msg_parser.MsOxMessage(tmp.name)

    text = msg_obj.body
    if "<html>" in text or "</div>" in text:
        elements = partition_html(text=text)
    else:
        elements = partition_text(text=text)

    return elements
