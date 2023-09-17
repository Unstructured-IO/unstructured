from typing import Optional, IO, Dict, List, Callable, Iterable, Any, Union, Tuple, Type, BinaryIO
from tempfile import SpooledTemporaryFile
from types import TracebackType
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from abc import ABC, abstractmethod
from email.utils import parsedate_to_datetime
import io
import magic
import requests
import os
import json
from datetime import datetime

# TODO: Deprecate
from unstructured.documents.elements import Element
from unstructured.partition.docx import _DocxPartitioner

# ---------------
# Enums & File type mappings
# ---------------


class FileType(Enum):
    UNK = "unkown"
    EMPTY = "empty"

    # MS Office Types
    DOC = "doc"
    DOCX = "docx"
    XLS = "xls"
    XLSX = "xlsx"
    PPT = "ppt"
    PPTX = "pptx"
    MSG = "msg"

    # Adobe Types
    PDF = "pdf"

    # Image Types
    JPG = "jpg"
    PNG = "png"
    TIFF = "tiff"

    # Plain Text Types
    RTF = "rtf"
    TXT = "txt"

    # Structured Data Types
    JSON = "json"
    CSV = "csv"
    TSV = "tsv"

    # Markup Types
    HTML = "html"
    EML = "eml"
    XML = "xml"
    MD = "md"
    EPUB = "epub"
    RST = "rst"
    ORG = "org"

    # Compressed Types
    ZIP = "zip"

    # Open Office Types
    ODT = "odt"


CONTENT_TYPE_MAPPING = {
    "application/pdf": FileType.PDF,
    "application/msword": FileType.DOC,
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": FileType.DOCX,
    "image/jpeg": FileType.JPG,
    "image/png": FileType.PNG,
    "image/tiff": FileType.TIFF,
    "text/plain": FileType.TXT,
    "text/x-csv": FileType.CSV,
    "application/csv": FileType.CSV,
    "application/x-csv": FileType.CSV,
    "text/comma-separated-values": FileType.CSV,
    "text/x-comma-separated-values": FileType.CSV,
    "text/csv": FileType.CSV,
    "text/tsv": FileType.TSV,
    "text/markdown": FileType.MD,
    "text/x-markdown": FileType.MD,
    "text/org": FileType.ORG,
    "text/x-rst": FileType.RST,
    "application/epub": FileType.EPUB,
    "application/epub+zip": FileType.EPUB,
    "application/json": FileType.JSON,
    "application/rtf": FileType.RTF,
    "text/rtf": FileType.RTF,
    "text/html": FileType.HTML,
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": FileType.XLSX,
    "application/vnd.ms-excel": FileType.XLS,
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": FileType.PPTX,
    "application/vnd.ms-powerpoint": FileType.PPT,
    "application/xml": FileType.XML,
    "application/vnd.oasis.opendocument.text": FileType.ODT,
    "message/rfc822": FileType.EML,
    "application/x-ole-storage": FileType.MSG,
    "application/vnd.ms-outlook": FileType.MSG,
    "inode/x-empty": FileType.EMPTY,
}


CONVERTABLE_TYPES = {
    "docx": FileType.DOCX,
    "doc": FileType.DOCX,
    "odt": FileType.DOCX,
    "pdf": FileType.PDF,
    "pptx": FileType.PPTX,
    "ppt": FileType.PPTX,
    "xlsx": FileType.XLSX,
    "xls": FileType.XLSX,
    "html": FileType.HTML,
    "eml": FileType.HTML,
    "md": FileType.HTML,
    "org": FileType.HTML,
    "rst": FileType.HTML,
    "epub": FileType.HTML,
    "xml": FileType.XML,
    "txt": FileType.TXT,
    "rtf": FileType.TXT,
    "json": FileType.JSON,
    "csv": FileType.CSV,
    "tsv": FileType.CSV,
    "jpg": FileType.JPG,
    "png": FileType.JPG,
    "tiff": FileType.JPG,
    "zip": FileType.ZIP,
}


class Strategy(Enum):
    FAST = "fast"
    HI_RES = "hi_res"
    OCR_ONLY = "ocr_only"
    AUTO = "auto"


# ---------------
# Exceptions
# ---------------


class DocumentError(Exception):
    def __init__(self, message, context=None):
        super().__init__(message)
        self.context = context


class DocumentConversionError(DocumentError):
    pass


class DocumentFetchError(DocumentError):
    pass


class NetworkError(DocumentError):
    pass


class FileError(DocumentError):
    pass


# ---------------
# Utilities
# ---------------

# TODO: Determine if we'll need to keep this abstraction
# Alternative network clients such as boto3 or a local mock client?


class NetworkClient(ABC):
    @abstractmethod
    def get(self, url: str, headers: Dict[str, str], verify: bool) -> requests.Response:
        pass


class RequestsNetworkClient(NetworkClient):
    def get(self, url: str, headers: Dict[str, str], verify: bool) -> requests.Response:
        try:
            return requests.get(url, headers=headers, verify=verify)
        except requests.RequestException as e:
            raise NetworkError(f"Failed to fetch from {url}", context=e)


# ---------------
# Documents
# ---------------


class DocumentMetadata:
    BUFFER_SIZE = 1024
    SEEK_SET = 0

    # TODO: Enforce Enums for content_type and encoding
    def __init__(self, content_type: str, encoding: str, last_modified: Optional[datetime]):
        self._content_type = content_type
        self._file_type = CONTENT_TYPE_MAPPING.get(content_type, FileType.UNK)
        self._convertable_type = CONVERTABLE_TYPES.get(self._file_type.value, FileType.UNK)
        self._encoding = encoding
        self._last_modified = last_modified

    @property
    def content_type(self) -> str:
        return self._content_type

    @property
    def encoding(self) -> str:
        return self._encoding

    @property
    def last_modified(self) -> Optional[datetime]:
        return self._last_modified

    @property
    def file_type(self) -> FileType:
        return self._file_type

    @property
    def convertable_type(self) -> FileType:
        return self._convertable_type

    @classmethod
    def from_file(cls, filename: str) -> "DocumentMetadata":
        last_modified = datetime.fromtimestamp(os.path.getmtime(filename))

        # Mime checker should be instantiated per thread. It is not thread safe.
        mime_checker = magic.Magic(mime=True, uncompress=True, mime_encoding=True, keep_going=True)
        mime = mime_checker.from_file(filename)
        content_type, encoding = cls._parse_mime_response(mime)
        return cls(content_type, encoding, last_modified)

    @classmethod
    def from_buffer(
        cls, buffer: IO, last_modified: datetime, buffer_size: int = 1024
    ) -> "DocumentMetadata":
        mime_checker = magic.Magic(mime=True, uncompress=True, mime_encoding=True, keep_going=True)
        first_bytes = buffer.read(buffer_size)
        buffer.seek(0)  # Reset the buffer to the beginning

        mime = mime_checker.from_buffer(first_bytes)
        content_type, encoding = cls._parse_mime_response(mime)
        return cls(content_type, encoding, last_modified)

    @staticmethod
    def _parse_mime_response(response: str) -> Tuple[str, str]:
        # TODO: Check if older libmagic versions can differencing between xls and doc
        # TODO: Check if libmagic can distinguish between html and xml
        # TODO: Check if libmagic can detect .json files as json (not text/plain)
        # TODO: Check if a file is a csv
        # TODO: Add additional encoding checks
        # TODO: Add types for content_type and encoding

        parts = response.split("; ")
        content_type = parts[0]
        extra_info = {k: v for k, v in (part.split("=") for part in parts[1:])}
        encoding = extra_info.get("charset", "utf-8")

        return content_type, encoding


@dataclass
class UnstructuredDocument:
    content: IO  # TODO: Determine more specific type
    metadata: DocumentMetadata


class DocumentSource(ABC):
    @abstractmethod
    def __enter__(self) -> UnstructuredDocument:
        raise NotImplementedError("Method __enter__ must be implemented in derived classes.")

    @abstractmethod
    def __exit__(
        self, exc_type: Type[BaseException], exc_value: BaseException, traceback: TracebackType
    ) -> None:
        pass

    @abstractmethod
    def fetch_document(self) -> UnstructuredDocument:
        raise NotImplementedError("Method fetch_document must be implemented in derived classes.")


class FileDocumentSource(DocumentSource):
    def __init__(self, filename: str):
        self.filename = filename
        self.file = None

    def __enter__(self):
        try:
            self.file = open(self.filename, "rb")
        except FileNotFoundError as e:
            raise FileError(f"File '{self.filename}' not found.", context=e)
        except PermissionError as e:
            raise FileError(f"Permission denied for '{self.filename}'.", context=e)
        metadata = DocumentMetadata.from_file(self.filename)
        return UnstructuredDocument(content=self.file, metadata=metadata)

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        if self.file:
            self.file.close()


class URLDocumentSource(DocumentSource):
    def __init__(
        self,
        url: str,
        headers: Optional[Dict[str, str]],
        filename: Optional[str] = None,
        ssl_verify: bool = True,
    ):
        self.url = url
        self.headers = headers if headers else {}
        self.ssl_verify = ssl_verify
        self.network_client = RequestsNetworkClient()
        self.filename = filename

    def __enter__(self):
        response = self.network_client.get(self.url, self.headers, self.ssl_verify)
        last_modified_str = response.headers.get("Last-Modified")
        last_modified = parsedate_to_datetime(last_modified_str) if last_modified_str else None

        return UnstructuredDocument(
            content=io.BytesIO(response.content),
            metadata=DocumentMetadata(
                content_type=response.headers["Content-Type"],
                encoding=response.headers.get("Content-Encoding", "utf-8"),
                last_modified=last_modified,
            ),
        )

    def __exit__(self, exc_type, exc_value, traceback):
        pass


# ---------------
# Partitioning
# ---------------


@dataclass
class PartitionerConfig:
    pass


class Partitioner(ABC):
    @abstractmethod
    def partition(
        self,
        document: UnstructuredDocument,
        config: PartitionerConfig,
        strategy: Strategy = Strategy.AUTO,
    ) -> Iterable[Element]:
        pass


class PartitionerFactory:
    partitioner_registry = {}

    @classmethod
    def register_partitioner(cls, core_file_type: FileType, partitioner: Type[Partitioner]):
        cls.partitioner_registry[core_file_type] = partitioner

    @classmethod
    def get_partitioner(
        cls, document: UnstructuredDocument, config: Optional[PartitionerConfig]
    ) -> Partitioner:
        core_file_type = document.metadata.convertable_type
        partitioner_class = cls.partitioner_registry.get(core_file_type)

        if partitioner_class is None:
            raise DocumentConversionError(
                f"No partitioner registered for core file type {core_file_type}"
            )

        return partitioner_class(document=document, config=config)


@dataclass
class DocxPartitionConfig(PartitionerConfig):
    page_breaks: bool = False


@dataclass
class PDFPartitionConfig(PartitionerConfig):
    infer_table_structure: bool = False
    infer_table_type: bool = False


@dataclass
class XMLPartitionConfig(PartitionerConfig):
    keep_tags: bool = False


class DocxPartitioner(Partitioner):
    def __init__(
        self,
        document: UnstructuredDocument,
        config: Optional[DocxPartitionConfig],
    ):
        self.document = document
        self.config = config or DocxPartitionConfig()

    def partition(self) -> Iterable[Element]:
        if (
            self.document.metadata.file_type != FileType.DOCX
            and self.document.metadata.convertable_type == FileType.DOCX
        ):
            converted_document = self.convert(self.document.content)
            return self._partition(converted_document)

        elif self.document.metadata.file_type == FileType.DOCX:
            return self._partition(self.document)

        else:
            raise DocumentConversionError(
                f"Cannot convert {self.document.metadata.file_type} to {FileType.DOCX}."
            )

    @staticmethod
    def convert(content: IO) -> UnstructuredDocument:
        """Converts document stream to a docx file."""
        # TODO: Implement
        return UnstructuredDocument(
            content=io.BytesIO(),
            metadata=DocumentMetadata(
                content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                encoding="utf-8",
                last_modified=None,
            ),
        )

    def _partition(self, document: UnstructuredDocument) -> Iterable[Element]:
        yield from _DocxPartitioner.iter_document_elements(document=document, config=self.config)


PartitionerFactory.register_partitioner(FileType.DOCX, DocxPartitioner)
# TODO: Implement HTML partitioner
# TODO: Implement XML partitioner
# TODO: Implement PDF partitioner
# TODO: Implement TXT partitioner
# TODO: Implement CSV partitioner
# TODO: Implement JSON partitioner
# TODO: Implement JPG partitioner


def partition(
    source: DocumentSource,
    config: PartitionerConfig = PartitionerConfig(),
    strategy: Strategy = Strategy.AUTO,
    **kwargs,
) -> Iterable[Element]:
    # TODO: Fold data_source_metadata into source
    # TODO: Infer languages as part of the partitioner
    # TODO: Post Processor -- reads the stream of elements and metadata and returns a compiled list of element
    # TODO: Partition code files
    # TODO: Write an interface to wrap this with the auto partitioner to maintain backwards compatibility

    with source as document:
        document: UnstructuredDocument = document

        partitioner = PartitionerFactory.get_partitioner(document, config)
        elements = partitioner.partition(document, config, strategy)

    # TODO: Implement post processor

    return elements
