# https://developers.notion.com/reference/property-object#title
from dataclasses import dataclass, field
from typing import List, Optional

from unstructured.ingest.connector.notion.interfaces import DBCellBase, DBPropertyBase
from unstructured.ingest.connector.notion.types.rich_text import RichText


@dataclass
class Title(DBPropertyBase):
    id: str
    name: str
    type: str = "title"
    title: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)


@dataclass
class TitleCell(DBCellBase):
    id: str
    title: List[RichText]
    type: str = "title"
    name: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict):
        return cls(title=[RichText.from_dict(rt) for rt in data.pop("title", [])], **data)

    def get_text(self) -> Optional[str]:
        rts = [rt.get_text() for rt in self.title]
        return ",".join([rt for rt in rts if rt])
