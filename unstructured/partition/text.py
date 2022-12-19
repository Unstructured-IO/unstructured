import email
import re
from typing import Dict, IO, List, Optional

from unstructured.cleaners.core import replace_mime_encodings
from unstructured.documents.elements import Element, Text
from unstructured.partition.text_type import (is_possible_narrative_text
                                              ,is_possible_title
                                              ,is_bulleted_text
                                             )
                                            


def partition_text(
    filename: Optional[str] = None, file: Optional[IO] = None, text: Optional[str] = None
) -> List[Element]:
    """Partitions an .eml documents into its constituent elements.
    Parameters
    ----------
     filename
        A string defining the target filename path.
    file
        A file-like object using "r" mode --> open(filename, "r").
    text
        The string representation of the .eml document.
    """
    if not any([filename, file, text]):
        raise ValueError("One of filename, file, or text must be specified.")

    if filename is not None and not file and not text:
        with open(filename, "r") as f:
            msg = email.message_from_file(f)

    elif file is not None and not filename and not text:
        file_text = file.read()
        msg = email.message_from_string(file_text)

    elif text is not None and not filename and not file:
        _text: str = str(text)
        msg = email.message_from_string(_text)

    else:
        raise ValueError("Only one of filename, file, or text can be specified.")

    content_map: Dict[str, str] = {
        part.get_content_type(): part.get_payload() for part in msg.walk()
    }
    content = content_map.get("text/plain", "")
    if not content:
        raise ValueError("text/plain content not found in email")

    content = re.split(r"\n\n\n|\n\n|\n", content)

    elements: List[Text] = list()
    for ctext in content:
        if ctext == "":
            break
        if is_possible_narrative_text(ctext):
            elements.append(NarrativeText(text=ctext))
        elif is_possible_title(ctext):
            elements.append(Title(text=ctext))
        elif is_bulleted_text(ctext):
            elements.append(ListItem(text=ctext)) 

    return elements