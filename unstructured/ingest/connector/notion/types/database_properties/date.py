# https://developers.notion.com/reference/property-object#date
from dataclasses import dataclass, field
from typing import Optional

from htmlBuilder.tags import HtmlTag

from unstructured.ingest.connector.notion.interfaces import DBCellBase, DBPropertyBase
from unstructured.ingest.connector.notion.types.date import Date as DateType


@dataclass
class Date(DBPropertyBase):
    id: str
    name: str
    type: str = "date"
    date: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)


@dataclass
class DateCell(DBCellBase):
    id: str
    date: Optional[DateType] = None
    name: Optional[str] = None
    type: str = "date"

    @classmethod
    def from_dict(cls, data: dict):
        date = None
        date_data = data.pop("date")
        if date_data:
            date = DateType.from_dict(date_data)
        return cls(date=date, **data)

    def get_html(self) -> Optional[HtmlTag]:
        if date := self.date:
            return date.get_html()
        return None
