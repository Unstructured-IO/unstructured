import json
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
    source_identifiers: Optional[SourceIdentifiers] = None
    doc_type: IndexDocType = field(default=IndexDocType.FILE)
    metadata: DataSourceMetadata = field(default_factory=DataSourceMetadata)
    additional_metadata: dict[str, Any] = field(default_factory=dict)
    reprocess: bool = False

    @classmethod
    def from_file(cls, path: str) -> "FileData":
        path = Path(path).resolve()
        if not path.exists() or not path.is_file():
            raise ValueError(f"file path not valid: {path}")
        with open(str(path.resolve()), "rb") as f:
            file_data_dict = json.load(f)
        file_data = FileData.from_dict(file_data_dict)
        return file_data

    def to_file(self, path: str) -> None:
        path = Path(path).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(str(path.resolve()), "w") as f:
            json.dump(self.to_dict(), f, indent=2)
