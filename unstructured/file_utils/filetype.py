import os
import zipfile
from enum import Enum
from typing import IO, Optional

try:
    import magic

    LIBMAGIC_AVAILABLE = True
except ImportError:  # pragma: nocover
    LIBMAGIC_AVAILABLE = False  # pragma: nocover

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

TXT_MIME_TYPES = [
    "text/plain",
    "message/rfc822",  # ref: https://www.rfc-editor.org/rfc/rfc822
]

MD_MIME_TYPES = [
    "text/markdown",
    "text/x-markdown",
]

EPUB_MIME_TYPES = [
    "application/epub",
    "application/epub+zip",
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
    JSON = 43

    # Markup Types
    HTML = 50
    XML = 51
    MD = 52
    EPUB = 53

    # Compressed Types
    ZIP = 60

    # NOTE(robinson) - This is to support sorting for pandas groupby functions
    def __lt__(self, other):
        return self.name < other.name


EXT_TO_FILETYPE = {
    ".pdf": FileType.PDF,
    ".docx": FileType.DOCX,
    ".jpg": FileType.JPG,
    ".jpeg": FileType.JPG,
    ".txt": FileType.TXT,
    ".text": FileType.TXT,
    ".eml": FileType.EML,
    ".xml": FileType.XML,
    ".html": FileType.HTML,
    ".md": FileType.MD,
    ".xlsx": FileType.XLSX,
    ".pptx": FileType.PPTX,
    ".png": FileType.PNG,
    ".doc": FileType.DOC,
    ".zip": FileType.ZIP,
    ".xls": FileType.XLS,
    ".ppt": FileType.PPT,
    ".rtf": FileType.RTF,
    ".json": FileType.JSON,
    ".epub": FileType.EPUB,
}


def detect_filetype(
    filename: Optional[str] = None,
    file: Optional[IO] = None,
) -> Optional[FileType]:
    """Use libmagic to determine a file's type. Helps determine which partition brick
    to use for a given file. A return value of None indicates a non-supported file type."""
    if filename and file:
        raise ValueError("Only one of filename or file should be specified.")

    if filename:
        _, extension = os.path.splitext(filename)
        extension = extension.lower()
        if LIBMAGIC_AVAILABLE:
            mime_type = magic.from_file(filename, mime=True)
        else:
            return EXT_TO_FILETYPE.get(extension.lower(), FileType.UNK)
    elif file is not None:
        extension = None
        # NOTE(robinson) - the python-magic docs recommend reading at least the first 2048 bytes
        # Increased to 4096 because otherwise .xlsx files get detected as a zip file
        # ref: https://github.com/ahupp/python-magic#usage
        if LIBMAGIC_AVAILABLE:
            mime_type = magic.from_buffer(file.read(4096), mime=True)
        else:
            raise ImportError(
                "libmagic is unavailable. "
                "Filetype detection on file-like objects requires libmagic. "
                "Please install libmagic and try again.",
            )
    else:
        raise ValueError("No filename nor file were specified.")

    if mime_type == "application/pdf":
        return FileType.PDF

    elif mime_type == "application/json":
        return FileType.JSON

    elif mime_type in DOCX_MIME_TYPES:
        return FileType.DOCX

    elif mime_type in DOC_MIME_TYPES:
        return FileType.DOC

    elif mime_type == "image/jpeg":
        return FileType.JPG

    elif mime_type == "image/png":
        return FileType.PNG

    elif mime_type in MD_MIME_TYPES:
        # NOTE - I am not sure whether libmagic ever returns these mimetypes.
        return FileType.MD

    elif mime_type in EPUB_MIME_TYPES:
        return FileType.EPUB

    elif mime_type in TXT_MIME_TYPES:
        if extension and extension == ".eml":
            return FileType.EML
        if extension and extension == ".md":
            return FileType.MD
        if file and not extension and _check_eml_from_buffer(file=file) is True:
            return FileType.EML
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

        extension = extension if extension else ""
        if filetype == FileType.UNK:
            return EXT_TO_FILETYPE.get(extension.lower(), FileType.ZIP)
        else:
            return EXT_TO_FILETYPE.get(extension.lower(), filetype)

    logger.warning(
        f"The MIME type{f' of {filename!r}' if filename else ''} is {mime_type!r}. "
        "This file type is not currently supported in unstructured.",
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

    logger.warning("Could not detect the filetype from application/octet-stream MIME type.")
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
