import os
import re
import zipfile
from enum import Enum
from typing import IO, Optional

from unstructured.nlp.patterns import LIST_OF_DICTS_PATTERN
from unstructured.partition.common import exactly_one

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

ODT_MIME_TYPES = [
    "application/vnd.oasis.opendocument.text",
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

MSG_MIME_TYPES = [
    "application/vnd.ms-outlook",
    "application/x-ole-storage",
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
    MSG = 16

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

    # Open Office Types
    ODT = 70

    # NOTE(robinson) - This is to support sorting for pandas groupby functions
    def __lt__(self, other):
        return self.name < other.name


STR_TO_FILETYPE = {
    "application/pdf": FileType.PDF,
    "application/msword": FileType.DOC,
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": FileType.DOCX,
    "image/jpeg": FileType.JPG,
    "image/png": FileType.PNG,
    "text/markdown": FileType.MD,
    "text/x-markdown": FileType.MD,
    "application/epub": FileType.EPUB,
    "application/epub+zip": FileType.EPUB,
    "text/html": FileType.HTML,
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": FileType.XLSX,
    "application/vnd.ms-excel": FileType.XLS,
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": FileType.PPTX,
    "application/vnd.ms-powerpoint": FileType.PPT,
    "application/xml": FileType.XML,
    "application/vnd.oasis.opendocument.text": FileType.ODT,
}


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
    ".msg": FileType.MSG,
    ".odt": FileType.ODT,
    None: FileType.UNK,
}


def detect_filetype(
    filename: Optional[str] = None,
    content_type: Optional[str] = None,
    file: Optional[IO] = None,
    file_filename: Optional[str] = None,
) -> Optional[FileType]:
    """Use libmagic to determine a file's type. Helps determine which partition brick
    to use for a given file. A return value of None indicates a non-supported file type.
    """
    exactly_one(filename=filename, file=file)

    if content_type:
        filetype = STR_TO_FILETYPE.get(content_type)
        if filetype:
            return filetype

    if filename or file_filename:
        _filename = filename or file_filename or ""
        _, extension = os.path.splitext(_filename)
        extension = extension.lower()
        if os.path.isfile(_filename) and LIBMAGIC_AVAILABLE:
            mime_type = magic.from_file(filename or file_filename, mime=True)  # type: ignore
            # NOTE(crag): for older versions of the OS libmagic package, such as is currently
            # installed on the Unstructured docker image, .json files resolve to "text/plain"
            # rather than "application/json". this corrects for that case.
            if mime_type == "text/plain" and extension == ".json":
                return FileType.JSON
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
        raise ValueError("No filename, file, nor file_filename were specified.")

    if mime_type == "application/pdf":
        return FileType.PDF

    elif mime_type == "application/json":
        return FileType.JSON

    elif mime_type in DOCX_MIME_TYPES:
        return FileType.DOCX

    elif mime_type in DOC_MIME_TYPES:
        return FileType.DOC

    elif mime_type in ODT_MIME_TYPES:
        return FileType.ODT

    elif mime_type in MSG_MIME_TYPES:
        return FileType.MSG

    elif mime_type == "image/jpeg":
        return FileType.JPG

    elif mime_type == "image/png":
        return FileType.PNG

    elif mime_type in MD_MIME_TYPES:
        # NOTE - I am not sure whether libmagic ever returns these mimetypes.
        return FileType.MD

    elif mime_type in EPUB_MIME_TYPES:
        return FileType.EPUB

    # NOTE(robinson) - examples are application/rtf or text/rtf.
    # magic often returns text/plain for RTF files
    elif mime_type.endswith("rtf"):
        return FileType.RTF

    elif mime_type.endswith("xml"):
        if extension and extension == ".html":
            return FileType.HTML
        else:
            return FileType.XML

    elif mime_type == "text/html":
        return FileType.HTML

    elif mime_type in TXT_MIME_TYPES or mime_type.startswith("text"):
        if extension and extension == ".eml":
            return FileType.EML
        elif extension and extension == ".md":
            return FileType.MD
        elif extension and extension == ".rtf":
            return FileType.RTF

        if _is_text_file_a_json(file=file, filename=filename):
            return FileType.JSON

        if file and not extension and _check_eml_from_buffer(file=file) is True:
            return FileType.EML
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
    return EXT_TO_FILETYPE.get(extension, FileType.UNK)


def _detect_filetype_from_octet_stream(file: IO) -> FileType:
    """Detects the filetype, given a file with an application/octet-stream MIME type."""
    file.seek(0)
    if zipfile.is_zipfile(file):
        file.seek(0)
        archive = zipfile.ZipFile(file)

        archive_filenames = [f.filename for f in archive.filelist]
        if all(f in archive_filenames for f in EXPECTED_DOCX_FILES):
            return FileType.DOCX
        elif all(f in archive_filenames for f in EXPECTED_XLSX_FILES):
            return FileType.XLSX
        elif all(f in archive_filenames for f in EXPECTED_PPTX_FILES):
            return FileType.PPTX

    logger.warning(
        "Could not detect the filetype from application/octet-stream MIME type.",
    )
    return FileType.UNK


def _is_text_file_a_json(
    filename: Optional[str] = None,
    content_type: Optional[str] = None,
    file: Optional[IO] = None,
):
    """Detects if a file that has a text/plain MIME type is a JSON file."""
    exactly_one(filename=filename, file=file)

    if file is not None:
        file.seek(0)
        file_content = file.read(4096)
        if isinstance(file_content, str):
            file_text = file_content
        else:
            file_text = file_content.decode()
        file.seek(0)
    elif filename is not None:
        with open(filename) as f:
            file_text = f.read()

    return re.match(LIST_OF_DICTS_PATTERN, file_text) is not None


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
