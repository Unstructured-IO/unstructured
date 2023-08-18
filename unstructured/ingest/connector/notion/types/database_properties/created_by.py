# https://developers.notion.com/reference/property-object#created-by
from dataclasses import dataclass, field
from typing import Optional

from htmlBuilder.tags import HtmlTag

from unstructured.ingest.connector.notion.interfaces import DBCellBase, DBPropertyBase
from unstructured.ingest.connector.notion.types.user import People


@dataclass
class CreatedBy(DBPropertyBase):
    id: str
    name: str
    type: str = "created_by"
    created_by: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)


@dataclass
class CreatedByCell(DBCellBase):
    id: str
    created_by: People
    type: str = "created_by"
    name: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict):
        return cls(created_by=People.from_dict(data.pop("created_by")), **data)

    def get_html(self) -> Optional[HtmlTag]:
        return self.created_by.get_html()
