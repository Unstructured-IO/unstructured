from __future__ import annotations

import os
import tempfile
from typing import IO, Any, Optional

from unstructured.documents.elements import Element
from unstructured.file_utils.model import FileType
from unstructured.partition.common.common import convert_office_doc, exactly_one
from unstructured.partition.common.metadata import get_last_modified_date
from unstructured.partition.pptx import partition_pptx


def partition_ppt(
    filename: Optional[str] = None,
    file: Optional[IO[bytes]] = None,
    metadata_filename: Optional[str] = None,
    metadata_last_modified: Optional[str] = None,
    **kwargs: Any,
) -> list[Element]:
    """Partitions Microsoft PowerPoint Documents in .ppt format into their document elements.

    Parameters
    ----------
    filename
        A string defining the target filename path.
    file
        A file-like object using "rb" mode --> open(filename, "rb").
    metadata_last_modified
        The last modified date for the document.

    Note that all arguments valid on `partition_pptx()` are also valid here and will be passed
    along to the `partition_pptx()` function.
    """
    # -- Verify that only one of the arguments was provided
    exactly_one(filename=filename, file=file)

    last_modified = get_last_modified_date(filename) if filename else None

    with tempfile.TemporaryDirectory() as tmpdir:
        if filename:
            # -- Verify filename.
            if not os.path.exists(filename):
                raise ValueError(f"The file {filename} does not exist.")

        else:
            assert file
            # -- Create filename.
            tmp_file_path = os.path.join(tmpdir, "tmp_file")
            with open(tmp_file_path, "wb") as tmp_file:
                tmp_file.write(file.read())
            filename = tmp_file_path

        _, filename_no_path = os.path.split(os.path.abspath(filename))
        base_filename, _ = os.path.splitext(filename_no_path)

        convert_office_doc(
            filename,
            tmpdir,
            target_format="pptx",
            target_filter="Impress MS PowerPoint 2007 XML",
        )
        pptx_filename = os.path.join(tmpdir, f"{base_filename}.pptx")

        elements = partition_pptx(
            filename=pptx_filename,
            metadata_filename=metadata_filename or filename,
            metadata_file_type=FileType.PPT,
            metadata_last_modified=metadata_last_modified or last_modified,
            **kwargs,
        )

    # -- Remove tmp.name from filename if parsing file
    if file:
        for element in elements:
            element.metadata.filename = metadata_filename

    return elements
