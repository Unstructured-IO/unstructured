# https://developers.notion.com/reference/property-object#title
from dataclasses import dataclass, field
from typing import List, Optional

from htmlBuilder.tags import Div, HtmlTag

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

    def get_html(self) -> Optional[HtmlTag]:
        if not self.title:
            return None
        return Div([], [rt.get_html() for rt in self.title])
