# https://developers.notion.com/reference/property-object#select
from dataclasses import dataclass, field
from typing import List, Optional

from unstructured.ingest.connector.notion.interfaces import (
    DBCellBase,
    DBPropertyBase,
    FromJSONMixin,
)


@dataclass
class SelectOption(FromJSONMixin):
    color: str
    id: str
    name: str

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)


@dataclass
class SelectProp(FromJSONMixin):
    options: List[SelectOption] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict):
        return cls(options=[SelectOption.from_dict(o) for o in data.get("options", [])])


@dataclass
class Select(DBPropertyBase):
    id: str
    name: str
    select: SelectProp
    type: str = "select"

    @classmethod
    def from_dict(cls, data: dict):
        return cls(select=SelectProp.from_dict(data.pop("select", {})), **data)


@dataclass
class SelectCell(DBCellBase):
    id: str
    select: Optional[SelectOption]
    type: str = "select"
    name: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict):
        select_data = data.pop("select")
        select = None
        if select_data:
            select = SelectOption.from_dict(select_data)
        return cls(select=select, **data)

    def get_text(self) -> Optional[str]:
        if self.select:
            return self.select.id
        return None
