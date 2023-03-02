import re
from typing import IO, List, Optional
from unstructured.staging.base import elements_from_json

def partition_json(
    filename: Optional[str] = None,
    file: Optional[IO] = None,
    text: Optional[str] = None,
) -> List[Element]:
    """Partitions an .json document into its constituent elements.                                                                          
    """
    if not any([filename, file, text]):
        raise ValueError("One of filename, file, or text must be specified.")

    if filename is not None and not file and not text:
        with open(filename, encoding="utf8") as f:
            file_text = f.read()

    elif file is not None and not filename and not text:
        file_text = file.read()

    elif text is not None and not filename and not file:
        file_text = str(text)

    else:
        raise ValueError("Only one of filename, file, or text can be specified.")


    file_text_whitespace_removed = file_text.replace(" ", "")
    try:
        # NOTE(Nathan): quick check to ensure that file_text is a list of dicts
        if file_text_whitespace_removed[0] == "[" and file_text_whitespace_removed[-1] == "]":
            if len(file_text_whitespace_removed) == 2 or \
                (file_text_whitespace_removed[1] == "{" and file_text_whitespace_removed[-2] == "}"):
                return elements_from_json(filename)
        raise ValueError("Not an unstructured json")
    except:
        raise ValueError("Not an unstructured json")
    