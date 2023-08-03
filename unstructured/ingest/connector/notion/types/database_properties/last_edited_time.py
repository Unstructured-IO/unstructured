# https://developers.notion.com/reference/property-object#last-edited-time
from dataclasses import dataclass, field
from typing import Optional

from unstructured.ingest.connector.notion.interfaces import DBCellBase, DBPropertyBase


@dataclass
class LastEditedTime(DBPropertyBase):
    id: str
    name: str
    type: str = "last_edited_time"
    last_edited_time: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)


@dataclass
class LastEditedTimeCell(DBCellBase):
    id: str
    last_edited_time: str
    type: str = "last_edited_time"
    name: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)

    def get_text(self) -> Optional[str]:
        return self.last_edited_time
