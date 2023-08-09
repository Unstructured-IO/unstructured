# https://developers.notion.com/reference/property-object#files
from dataclasses import dataclass, field
from typing import List, Optional

from unstructured.ingest.connector.notion.interfaces import DBCellBase, DBPropertyBase
from unstructured.ingest.connector.notion.types.file import FileObject


@dataclass
class Files(DBPropertyBase):
    id: str
    name: str
    type: str = "files"
    files: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)


@dataclass
class FilesCell(DBCellBase):
    id: str
    files: List[FileObject]
    type: str = "files"
    name: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict):
        return cls(files=[FileObject.from_dict(f) for f in data.pop("files", [])], **data)

    def get_text(self) -> Optional[str]:
        texts = [f.get_text() for f in self.files]
        return "\n".join([t for t in texts if t])
