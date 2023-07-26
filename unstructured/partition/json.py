import json
from typing import IO, List, Optional

from unstructured.documents.elements import Element, process_metadata
from unstructured.file_utils.filetype import (
    FileType,
    add_metadata_with_filetype,
    is_json_processable,
)
from unstructured.partition.common import (
    exactly_one,
    get_last_modified_date,
    get_last_modified_date_from_file,
)
from unstructured.staging.base import dict_to_elements


@process_metadata()
@add_metadata_with_filetype(FileType.JSON)
def partition_json(
    filename: Optional[str] = None,
    file: Optional[IO[bytes]] = None,
    text: Optional[str] = None,
    include_metadata: bool = True,
    metadata_filename: Optional[str] = None,
    metadata_date: Optional[str] = None,
    **kwargs,
) -> List[Element]:
    """Partitions an .json document into its constituent elements.

    Parameters
    ----------
    filename
        A string defining the target filename path.
    file
        A file-like object as bytes --> open(filename, "rb").
    text
        The string representation of the .json document.
    metadata_date
        The last modified date for the document.
    """
    if text is not None and text.strip() == "" and not file and not filename:
        return []

    exactly_one(filename=filename, file=file, text=text)

    last_modification_date = None
    if filename is not None:
        last_modification_date = get_last_modified_date(filename)
        with open(filename, encoding="utf8") as f:
            file_text = f.read()

    elif file is not None:
        last_modification_date = get_last_modified_date_from_file(file)

        file_content = file.read()
        if isinstance(file_content, str):
            file_text = file_content
        else:
            file_text = file_content.decode()
        file.seek(0)

    elif text is not None:
        file_text = str(text)

    if not is_json_processable(file_text=file_text):
        raise ValueError(
            "JSON cannot be partitioned. Schema does not match the Unstructured schema.",
        )

    try:
        dict = json.loads(file_text)
        elements = dict_to_elements(dict)
    except json.JSONDecodeError:
        raise ValueError("Not a valid json")

    for element in elements:
        element.metadata.date = metadata_date or last_modification_date
    # NOTE(Nathan): in future PR, try extracting items that look like text
    #               if file_text is a valid json but not an unstructured json

    return elements
