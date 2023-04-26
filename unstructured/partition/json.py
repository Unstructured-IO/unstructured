import json
import re
from typing import IO, List, Optional

from unstructured.documents.elements import Element
from unstructured.nlp.patterns import LIST_OF_DICTS_PATTERN
from unstructured.partition.common import exactly_one
from unstructured.staging.base import dict_to_elements


def partition_json(
    filename: Optional[str] = None,
    file: Optional[IO] = None,
    text: Optional[str] = None,
) -> List[Element]:
    """Partitions an .json document into its constituent elements."""
    if text is not None and text.strip() == "" and not file and not filename:
        return []

    exactly_one(filename=filename, file=file, text=text)

    if filename is not None:
        with open(filename, encoding="utf8") as f:
            file_text = f.read()
    elif file is not None:
        file_content = file.read()
        if isinstance(file_content, str):
            file_text = file_content
        else:
            file_text = file_content.decode()
        file.seek(0)
    elif text is not None:
        file_text = str(text)

    # NOTE(Nathan): we expect file_text to be a list of dicts (optimization)
    if not re.match(LIST_OF_DICTS_PATTERN, file_text):
        raise ValueError("Json schema does not match the Unstructured schema")

    try:
        dict = json.loads(file_text)
        elements = dict_to_elements(dict)
    except json.JSONDecodeError:
        raise ValueError("Not a valid json")

    # NOTE(Nathan): in future PR, try extracting items that look like text
    #               if file_text is a valid json but not an unstructured json

    return elements
