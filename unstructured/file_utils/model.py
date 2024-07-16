"""Domain-model for file-types."""

from __future__ import annotations

import enum


class FileType(enum.Enum):
    UNK = 0
    EMPTY = 1

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
    TIFF = 32
    BMP = 33
    HEIC = 34

    # Plain Text Types
    EML = 40
    RTF = 41
    TXT = 42
    JSON = 43
    CSV = 44
    TSV = 45

    # Markup Types
    HTML = 50
    XML = 51
    MD = 52
    EPUB = 53
    RST = 54
    ORG = 55

    # Compressed Types
    ZIP = 60

    # Open Office Types
    ODT = 70

    # Audio Files
    WAV = 80

    def __lt__(self, other: FileType) -> bool:
        """Makes `FileType` members comparable with relational operators, at least with `<`.

        This makes them sortable, in particular it supports sorting for pandas groupby functions.
        """
        return self.name < other.name


STR_TO_FILETYPE = {
    # -- BMP --
    "image/bmp": FileType.BMP,
    # -- CSV --
    "application/csv": FileType.CSV,
    "application/x-csv": FileType.CSV,
    "text/comma-separated-values": FileType.CSV,
    "text/csv": FileType.CSV,
    "text/x-comma-separated-values": FileType.CSV,
    "text/x-csv": FileType.CSV,
    # -- DOC --
    "application/msword": FileType.DOC,
    # -- DOCX --
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": FileType.DOCX,
    # -- EML --
    "message/rfc822": FileType.EML,
    # -- EPUB --
    "application/epub": FileType.EPUB,
    "application/epub+zip": FileType.EPUB,
    # -- HEIF --
    "image/heic": FileType.HEIC,
    # -- HTML --
    "text/html": FileType.HTML,
    # -- JPG --
    "image/jpeg": FileType.JPG,
    # -- JSON --
    "application/json": FileType.JSON,
    # -- MD --
    "text/markdown": FileType.MD,
    "text/x-markdown": FileType.MD,
    # -- MSG --
    "application/vnd.ms-outlook": FileType.MSG,
    "application/x-ole-storage": FileType.MSG,
    # -- ODT --
    "application/vnd.oasis.opendocument.text": FileType.ODT,
    # -- ORG --
    "text/org": FileType.ORG,
    # -- PDF --
    "application/pdf": FileType.PDF,
    # -- PNG --
    "image/png": FileType.PNG,
    # -- PPT --
    "application/vnd.ms-powerpoint": FileType.PPT,
    # -- PPTX --
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": FileType.PPTX,
    # -- RST --
    "text/x-rst": FileType.RST,
    # -- RTF --
    "application/rtf": FileType.RTF,
    "text/rtf": FileType.RTF,
    # -- TIFF --
    "image/tiff": FileType.TIFF,
    # -- TSV --
    "text/tsv": FileType.TSV,
    # -- TXT --
    "text/plain": FileType.TXT,
    # NOTE(robinson) - https://mimetype.io/application/yaml
    # In the future, we may have special processing for YAML
    # files instead of treating them as plaintext
    "application/x-yaml": FileType.TXT,
    "application/yaml": FileType.TXT,
    "text/x-yaml": FileType.TXT,
    "text/yaml": FileType.TXT,
    # -- WAV --
    # NOTE(robinson) - https://mimetype.io/audio/wav
    "audio/vnd.wav": FileType.WAV,
    "audio/vnd.wave": FileType.WAV,
    "audio/wave": FileType.WAV,
    "audio/x-pn-wav": FileType.WAV,
    "audio/x-wav": FileType.WAV,
    # -- XLS --
    "application/vnd.ms-excel": FileType.XLS,
    # -- XLSX --
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": FileType.XLSX,
    # -- XML --
    "application/xml": FileType.XML,
    # -- EMPTY --
    "inode/x-empty": FileType.EMPTY,
}

MIMETYPES_TO_EXCLUDE = [
    "application/csv",
    "application/epub+zip",
    "application/x-csv",
    "application/x-ole-storage",
    "text/comma-separated-values",
    "text/x-comma-separated-values",
    "text/x-csv",
    "text/x-markdown",
]

FILETYPE_TO_MIMETYPE = {v: k for k, v in STR_TO_FILETYPE.items() if k not in MIMETYPES_TO_EXCLUDE}

EXT_TO_FILETYPE = {
    # -- BMP --
    ".bmp": FileType.BMP,
    # -- CSV --
    ".csv": FileType.CSV,
    # -- DOC --
    ".doc": FileType.DOC,
    # -- DOCX --
    ".docx": FileType.DOCX,
    # -- EML --
    ".eml": FileType.EML,
    ".p7s": FileType.EML,
    # -- EPUB --
    ".epub": FileType.EPUB,
    # -- HEIC --
    ".heic": FileType.HEIC,
    # -- HTML --
    ".htm": FileType.HTML,
    ".html": FileType.HTML,
    # -- JPG --
    ".jpeg": FileType.JPG,
    ".jpg": FileType.JPG,
    # -- JSON --
    ".json": FileType.JSON,
    # -- MD --
    ".md": FileType.MD,
    # -- MSG --
    ".msg": FileType.MSG,
    # -- ODT --
    ".odt": FileType.ODT,
    # -- ORG --
    ".org": FileType.ORG,
    # -- PDF --
    ".pdf": FileType.PDF,
    # -- PNG --
    ".png": FileType.PNG,
    # -- PPT --
    ".ppt": FileType.PPT,
    # -- PPTX --
    ".pptx": FileType.PPTX,
    # -- RST --
    ".rst": FileType.RST,
    # -- RTF --
    ".rtf": FileType.RTF,
    # -- TIFF --
    ".tiff": FileType.TIFF,
    # -- TSV --
    ".tab": FileType.TSV,
    ".tsv": FileType.TSV,
    # -- TXT --
    ".text": FileType.TXT,
    ".txt": FileType.TXT,
    # NOTE(robinson) - for now we are treating code files as plain text
    ".c": FileType.TXT,
    ".cc": FileType.TXT,
    ".cpp": FileType.TXT,
    ".cs": FileType.TXT,
    ".cxx": FileType.TXT,
    ".go": FileType.TXT,
    ".java": FileType.TXT,
    ".js": FileType.TXT,
    ".log": FileType.TXT,
    ".php": FileType.TXT,
    ".py": FileType.TXT,
    ".rb": FileType.TXT,
    ".swift": FileType.TXT,
    ".ts": FileType.TXT,
    ".yaml": FileType.TXT,
    ".yml": FileType.TXT,
    # -- WAV --
    ".wav": FileType.WAV,
    # -- XLS --
    ".xls": FileType.XLS,
    # -- XLSX --
    ".xlsx": FileType.XLSX,
    # -- XML --
    ".xml": FileType.XML,
    # -- ZIP --
    ".zip": FileType.ZIP,
    # -- UNK --
    None: FileType.UNK,
}

PLAIN_TEXT_EXTENSIONS = ".csv .eml .html .json .md .org .p7s .rst .rtf .tab .text .tsv .txt".split()
