from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional, TypeVar

from unstructured.documents.elements import DataSourceMetadata


class IndexDocType(str, Enum):
    BATCH = "batch"
    FILE = "file"


@dataclass
class SourceIdentifiers:
    filename: str
    fullpath: str
    rel_path: Optional[str] = None
    additional_metadata: Optional[dict[str, Any]] = None

    @property
    def filename_stem(self) -> str:
        return Path(self.filename).stem

    @property
    def relative_path(self) -> str:
        return self.rel_path or self.fullpath


source_id_type = TypeVar("source_id_type", bound=SourceIdentifiers)


@dataclass
class FileData:
    identifier: str
    connector_type: str
    source_identifiers: source_id_type
    doc_type: IndexDocType = field(default=IndexDocType.FILE)
    metadata: Optional[DataSourceMetadata] = None
