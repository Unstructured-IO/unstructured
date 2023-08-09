# https://developers.notion.com/reference/property-object#created-time
from dataclasses import dataclass, field
from typing import Optional

from unstructured.ingest.connector.notion.interfaces import DBCellBase, DBPropertyBase


@dataclass
class CreatedTime(DBPropertyBase):
    id: str
    name: str
    type: str = "created_time"
    created_time: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)


@dataclass
class CreatedTimeCell(DBCellBase):
    id: str
    created_time: str
    type: str = "created_time"
    name: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)

    def get_text(self) -> Optional[str]:
        return self.created_time
