import re
from typing import IO, List, Optional
from unstructured.staging.base import elements_from_json

LIST_OF_DICTS_PATTERN = r"\A\s*\[\s*{.*}\s*\]\s*\Z"

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

    # NOTE(Nathan): we expect file_text to be a list of dicts (optimization)
    if re.match(LIST_OF_DICTS_PATTERN, file_text):
        try:
            return elements_from_json(filename)
        except:
            raise ValueError("Not an unstructured json")
    else:
        raise ValueError("Not an unstructured json")
 