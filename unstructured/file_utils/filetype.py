from enum import Enum
import os
from typing import IO, Optional
import zipfile

import magic

from unstructured.logger import logger
from unstructured.nlp.patterns import EMAIL_HEAD_RE


DOCX_MIME_TYPES = [
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
]

DOC_MIME_TYPES = [
    "application/msword",
]

XLSX_MIME_TYPES = [
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
]

XLS_MIME_TYPES = [
    "application/vnd.ms-excel",
]

PPTX_MIME_TYPES = [
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
]

PPT_MIME_TYPES = [
    "application/vnd.ms-powerpoint",
]

# NOTE(robinson) - .docx.xlsx files are actually zip file with a .docx/.xslx extension.
# If the MIME type is application/octet-stream, we check if it's a .docx/.xlsx file by
# looking for expected filenames within the zip file.
EXPECTED_DOCX_FILES = [
    "docProps/core.xml",
    "word/document.xml",
]

EXPECTED_XLSX_FILES = [
    "docProps/core.xml",
    "xl/workbook.xml",
]

EXPECTED_PPTX_FILES = [
    "docProps/core.xml",
    "ppt/presentation.xml",
]


class FileType(Enum):
    UNK = 0

    # MS Office Types
    DOC = 10
    DOCX = 11
    XLS = 12
    XLSX = 13
    PPT = 14
    PPTX = 15

    # Adobe Types
    PDF = 20

    # Image Types
    JPG = 30
    PNG = 31

    # Plain Text Types
    EML = 40
    RTF = 41
    TXT = 42

    # Markup Types
    HTML = 50
    XML = 51

    # Compressed Types
    ZIP = 60

    # NOTE(robinson) - This is to support sorting for pandas groupby functions
    def __lt__(self, other):
        return self.name < other.name


EXT_TO_FILETYPE = {
    ".pdf": FileType.PDF,
    ".docx": FileType.DOCX,
    ".jpg": FileType.JPG,
    ".txt": FileType.TXT,
    ".eml": FileType.EML,
    ".xml": FileType.XML,
    ".html": FileType.HTML,
    ".xlsx": FileType.XLSX,
    ".pptx": FileType.PPTX,
    ".png": FileType.PNG,
    ".doc": FileType.DOC,
    ".zip": FileType.ZIP,
    ".xls": FileType.XLS,
    ".ppt": FileType.PPT,
    ".rtf": FileType.RTF,
}


def detect_filetype(
    filename: Optional[str] = None, file: Optional[IO] = None
) -> Optional[FileType]:
    """Use libmagic to determine a file's type. Helps determine which partition brick
    to use for a given file. A return value of None indicates a non-supported file type."""
    if filename and file:
        raise ValueError("Only one of filename or file should be specified.")

    if filename:
        _, extension = os.path.splitext(filename)
        extension = extension.lower()
        mime_type = magic.from_file(filename, mime=True)
    elif file is not None:
        extension = None
        # NOTE(robinson) - the python-magic docs recommend reading at least the first 2048 bytes
        # Increased to 4096 because otherwise .xlsx files get detected as a zip file
        # ref: https://github.com/ahupp/python-magic#usage
        mime_type = magic.from_buffer(file.read(4096), mime=True)
    else:
        raise ValueError("No filename nor file were specified.")

    if mime_type == "application/pdf":
        return FileType.PDF

    elif mime_type in DOCX_MIME_TYPES:
        return FileType.DOCX

    elif mime_type in DOC_MIME_TYPES:
        return FileType.DOC

    elif mime_type == "image/jpeg":
        return FileType.JPG

    elif mime_type == "image/png":
        return FileType.PNG

    elif mime_type == "text/plain":
        if extension and extension == ".eml":
            return FileType.EML
        if file and not extension:
            if _check_eml_from_buffer(file=file) is True:
                return FileType.EML
            else:
                return FileType.TXT
        else:
            return FileType.TXT

    elif mime_type.endswith("xml"):
        if extension and extension == ".html":
            return FileType.HTML
        else:
            return FileType.XML

    elif mime_type == "text/html":
        return FileType.HTML

    elif mime_type.startswith("text"):
        return FileType.TXT

    elif mime_type in XLSX_MIME_TYPES:
        return FileType.XLSX

    elif mime_type in XLS_MIME_TYPES:
        return FileType.XLS

    elif mime_type in PPTX_MIME_TYPES:
        return FileType.PPTX

    elif mime_type in PPT_MIME_TYPES:
        return FileType.PPT

    elif mime_type == "application/octet-stream":
        if file and not extension:
            return _detect_filetype_from_octet_stream(file=file)
        else:
            return EXT_TO_FILETYPE.get(extension, FileType.UNK)

    elif mime_type == "application/zip":
        filetype = FileType.UNK
        if file and not extension:
            filetype = _detect_filetype_from_octet_stream(file=file)
        elif filename is not None:
            with open(filename, "rb") as f:
                filetype = _detect_filetype_from_octet_stream(file=f)

        if filetype == FileType.UNK:
            return FileType.ZIP
        else:
            return filetype

    logger.warn(
        f"MIME type was {mime_type}. This file type is not currently supported in unstructured."
    )
    return FileType.UNK


def _detect_filetype_from_octet_stream(file: IO) -> FileType:
    """Detects the filetype, given a file with an application/octet-stream MIME type."""
    file.seek(0)
    if zipfile.is_zipfile(file):
        file.seek(0)
        archive = zipfile.ZipFile(file)

        archive_filenames = [f.filename for f in archive.filelist]
        if all([f in archive_filenames for f in EXPECTED_DOCX_FILES]):
            return FileType.DOCX
        elif all([f in archive_filenames for f in EXPECTED_XLSX_FILES]):
            return FileType.XLSX
        elif all([f in archive_filenames for f in EXPECTED_PPTX_FILES]):
            return FileType.PPTX

    logger.warning("Could not detect the filetype from application/octet-strem MIME type.")
    return FileType.UNK


def _check_eml_from_buffer(file: IO) -> bool:
    """Checks if a text/plain file is actually a .eml file. Uses a regex pattern to see if the
    start of the file matches the typical pattern for a .eml file."""
    file.seek(0)
    file_content = file.read(4096)
    if isinstance(file_content, bytes):
        file_head = file_content.decode("utf-8")
    else:
        file_head = file_content

    return EMAIL_HEAD_RE.match(file_head) is not None
