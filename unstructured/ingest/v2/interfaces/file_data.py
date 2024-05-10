from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from dataclasses_json import DataClassJsonMixin

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


@dataclass
class FileData(DataClassJsonMixin):
    identifier: str
    connector_type: str
    source_identifiers: SourceIdentifiers
    doc_type: IndexDocType = field(default=IndexDocType.FILE)
    metadata: Optional[DataSourceMetadata] = None
