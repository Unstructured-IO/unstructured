from enum import Enum
import os
from typing import IO, Optional

import magic

from unstructured.logger import logger


DOCX_MIME_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
XLSX_MIME_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


class FileType(Enum):
    PDF = 1
    DOCX = 2
    JPG = 3
    TXT = 4
    EML = 5
    XML = 6
    HTML = 7
    XLSX = 8


def detect_filetype(filename: str = "", file: Optional[IO] = None) -> Optional[FileType]:
    """Use libmagic to determine a file's type. Helps determine which partition brick
    to use for a given file. A return value of None indicates a non-supported file type."""
    if filename and file:
        raise ValueError("Only one of filename or file should be specified.")

    if filename:
        _, extension = os.path.splitext(filename)
        mime_type = magic.from_file(filename, mime=True)
    elif file is not None:
        extension = None
        # NOTE(robinson) - the python-magic docs recommend reading at least the first 2048 bytes
        # Increased to 4096 because otherwise .xlsx files get detected as a zip fle
        # ref: https://github.com/ahupp/python-magic#usage
        mime_type = magic.from_buffer(file.read(4096), mime=True)
    else:
        raise ValueError("No filename nor file were specified.")

    if mime_type == "application/pdf":
        return FileType.PDF
    elif mime_type == DOCX_MIME_TYPE:
        return FileType.DOCX
    elif mime_type == "image/jpeg":
        return FileType.JPG
    elif mime_type == "text/plain":
        if extension and extension == ".eml":
            return FileType.EML
        else:
            return FileType.TXT
    elif mime_type == "text/xml":
        if extension and extension == ".html":
            return FileType.HTML
        else:
            return FileType.XML
    elif mime_type == "text/html":
        return FileType.HTML
    elif mime_type == XLSX_MIME_TYPE:
        return FileType.XLSX
    else:
        logger.warn(
            f"MIME type was {mime_type}. This file type is not currently supported in unstructured."
        )
        return None
