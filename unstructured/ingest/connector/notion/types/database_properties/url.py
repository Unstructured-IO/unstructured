# https://developers.notion.com/reference/property-object#url
from dataclasses import dataclass, field
from typing import Optional

from unstructured.ingest.connector.notion.interfaces import DBCellBase, DBPropertyBase


@dataclass
class URL(DBPropertyBase):
    id: str
    name: str
    type: str = "url"
    url: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)


@dataclass
class URLCell(DBCellBase):
    id: str
    url: str
    name: Optional[str] = None
    type: str = "url"

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)

    def get_text(self) -> Optional[str]:
        return self.url
