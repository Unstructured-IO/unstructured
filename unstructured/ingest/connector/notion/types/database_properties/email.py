# https://developers.notion.com/reference/property-object#email
from dataclasses import dataclass, field
from typing import Optional

from unstructured.ingest.connector.notion.interfaces import DBCellBase, DBPropertyBase


@dataclass
class Email(DBPropertyBase):
    id: str
    name: str
    type: str = "email"
    email: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)


@dataclass
class EmailCell(DBCellBase):
    id: str
    email: str
    name: Optional[str] = None
    type: str = "email"

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)

    def get_text(self) -> Optional[str]:
        return self.email
