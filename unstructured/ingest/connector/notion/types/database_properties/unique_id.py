# https://developers.notion.com/reference/property-object#title
from dataclasses import dataclass, field
from typing import Optional

from htmlBuilder.tags import Div, HtmlTag

from unstructured.ingest.connector.notion.interfaces import (
    DBCellBase,
    DBPropertyBase,
    FromJSONMixin,
)


@dataclass
class UniqueID(DBPropertyBase):
    id: str
    name: str
    type: str = "unique_id"
    unique_id: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)


@dataclass
class UniqueIDCellData(FromJSONMixin):
    prefix: str
    number: int

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)


@dataclass
class UniqueIDCell(DBCellBase):
    id: str
    unique_id: Optional[UniqueIDCellData]
    type: str = "title"
    name: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict):
        return cls(unique_id=UniqueIDCellData.from_dict(data.pop("unique_id")), **data)

    def get_html(self) -> Optional[HtmlTag]:
        if unique_id := self.unique_id:
            return Div([], f"{unique_id.prefix}-{unique_id.number}")
        return None
