from __future__ import annotations

import io
from abc import abstractmethod
from tempfile import SpooledTemporaryFile
from typing import (
    Any,
    BinaryIO,
    Iterator,
    Optional,
    Union,
)

from unstructured.documents.elements import Element
from unstructured.partition.common import (
    get_last_modified_date,
    get_last_modified_date_from_file,
)
from unstructured.utils import lazyproperty


class _Partitioner:
    """Provides `.partition()` for files."""

    # TODO: I think we can do better on metadata.filename. Should that only be populated when a
    #       `metadata_filename` argument was provided to `partition_docx()`? What about when not but
    #       we do get a `filename` arg or a `file` arg that has a `.name` attribute?

    def __init__(
        self,
        filename: Optional[str],
        file: Optional[Union[BinaryIO, SpooledTemporaryFile[bytes]]],
        metadata_filename: Optional[str],
        metadata_last_modified: Optional[str],
    ) -> None:
        self._filename = filename
        self._file = file
        self._metadata_filename = metadata_filename
        self._metadata_last_modified = metadata_last_modified

    @classmethod
    def iter_document_elements(
        cls,
        filename: Optional[str] = None,
        file: Optional[Union[BinaryIO, SpooledTemporaryFile[bytes]]] = None,
        metadata_filename: Optional[str] = None,
        metadata_last_modified: Optional[str] = None,
    ) -> Iterator[Element]:
        """Partition document into its document elements."""
        return cls(
            filename,
            file,
            metadata_filename,
            metadata_last_modified,
        )._iter_document_elements()

    @abstractmethod
    def _iter_document_elements(self) -> Iterator[Element]:
        """Generate each document-element in document order."""
        pass

    @abstractmethod
    def _load_document_from_filename(self, filename: str) -> Any:
        """Load document from filesystem as identified by a filename."""
        pass

    @abstractmethod
    def _load_document_from_file_object(
        self,
        file: Union[BinaryIO, SpooledTemporaryFile[bytes]],
    ) -> Any:
        """Load document from open file object."""
        pass

    @lazyproperty
    def _document(self) -> Any:
        """The object loaded from file or filename."""
        filename, file = self._filename, self._file

        if filename is not None:
            return self._load_document_from_filename(filename)

        assert file is not None
        if isinstance(file, SpooledTemporaryFile):
            file.seek(0)
            file = io.BytesIO(file.read())
        return self._load_document_from_file_object(file)

    @lazyproperty
    def _last_modified(self) -> Optional[str]:
        """Last-modified date suitable for use in element metadata."""
        # -- if this file was converted from another format, any last-modified date for the file
        # -- will be today, so we get it from the conversion step in `._metadata_last_modified`.
        if self._metadata_last_modified:
            return self._metadata_last_modified

        file_path, file = self._filename, self._file

        # -- if the file is on the filesystem, get its date from there --
        if file_path is not None:
            return None if file_path.startswith("/tmp") else get_last_modified_date(file_path)

        # -- otherwise try getting it from the file-like object (unlikely since BytesIO and its
        # -- brethren have no such metadata).
        assert file is not None
        return get_last_modified_date_from_file(file)
